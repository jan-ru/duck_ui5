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

import pandas as pd

from utils import pad_account_code, apply_schema, validate_schema, write_to_duckdb

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

    # Validate schema before writing
    if not validate_schema(df, TRANSACTIONS_SCHEMA):
        print("  Warning: Schema validation found issues, but continuing...")

    # Write to DuckDB using shared utility
    row_count = write_to_duckdb(df, output_path, "transactions", if_exists="replace")

    print(f"  ✓ Written to: {output_path}")
    print(f"  ✓ Verified: {row_count:,} rows in transactions table")


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
