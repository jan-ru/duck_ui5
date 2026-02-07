"""
Process transaction dump from Excel to DuckDB.

Transforms Excel transaction data by:
- Removing unnecessary columns
- Converting date formats
- Padding account codes
- Writing to DuckDB database
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd

from utils import pad_account_code

# Column names to remove from the dump
COLUMNS_TO_DROP = [
    "Btwbedrag",
    "Boekingsstatus",
    "CodeAdministratie",
    "Code2",
    "Debet",
    "Credit",
    "Btwcode",
    "Nummer",
]

# Expected schema for transactions table
TRANSACTIONS_SCHEMA = {
    "NaamAdministratie": "str",
    "CodeGrootboekrekening": "str",  # String for padded codes
    "NaamGrootboekrekening": "str",
    "Code": "str",
    "Boekingsnummer": "Int64",  # Nullable integer
    "Boekdatum": "datetime64[ns]",
    "Periode": "str",
    "Code1": "str",
    "Omschrijving": "str",
    "Saldo": "float64",
    "Factuurnummer": "str",
}


def apply_schema(df: pd.DataFrame, schema: dict) -> pd.DataFrame:
    """
    Apply explicit data types to DataFrame.

    Args:
        df: DataFrame to type
        schema: Dict mapping column names to dtypes

    Returns:
        DataFrame with corrected types
    """
    df_typed = df.copy()

    for col, dtype in schema.items():
        if col in df_typed.columns:
            try:
                if dtype == "datetime64[ns]":
                    # Handle dates specially
                    df_typed[col] = pd.to_datetime(df_typed[col], errors="coerce")
                elif dtype in ["float64", "Float64"]:
                    # Handle numeric with coercion
                    df_typed[col] = pd.to_numeric(df_typed[col], errors="coerce")
                elif dtype in ["Int64", "int64"]:
                    # Nullable integer for codes
                    df_typed[col] = pd.to_numeric(df_typed[col], errors="coerce").astype("Int64")
                elif dtype == "str":
                    # Force string type
                    df_typed[col] = df_typed[col].astype("str")
                else:
                    # Other types
                    df_typed[col] = df_typed[col].astype(dtype)
            except Exception as e:
                print(f"Warning: Could not convert {col} to {dtype}: {e}")
        else:
            print(f"Warning: Column {col} not found in DataFrame")

    return df_typed


def process_dump(
    input_path: str = "import/DUMP_13jun25.xls",
    output_path: str = "export/2023_transactions.db",
) -> None:
    """
    Process transaction dump from Excel to DuckDB.

    Args:
        input_path: Path to input Excel file
        output_path: Path to output DuckDB database
    """
    print(f"Processing {input_path}...")

    # Read the Excel file
    df = pd.read_excel(input_path)

    print(f"  Loaded: {len(df):,} rows, {len(df.columns)} columns")

    # Delete specified columns
    df = df.drop(columns=COLUMNS_TO_DROP)

    # Convert Boekdatum to proper datetime type (from timestamp milliseconds)
    df["Boekdatum"] = pd.to_datetime(df["Boekdatum"], unit="ms")

    # Pad CodeGrootboekrekening to 4 positions with leading zeros
    df["CodeGrootboekrekening"] = pad_account_code(df["CodeGrootboekrekening"])

    # Apply explicit schema to ensure correct types
    print("  Applying schema...")
    df = apply_schema(df, TRANSACTIONS_SCHEMA)

    print(f"  Final schema:")
    print(df.dtypes)

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Write to DuckDB
    con = duckdb.connect(output_path)
    con.execute("CREATE OR REPLACE TABLE transactions AS SELECT * FROM df")
    con.close()

    print(f"  ✓ Written to: {output_path}")
    print(f"  ✓ Final: {len(df):,} rows, {len(df.columns)} columns")


def main() -> int:
    """CLI entry point."""
    try:
        process_dump()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
