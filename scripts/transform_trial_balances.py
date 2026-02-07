"""
Transform Excel trial balance data to DuckDB database.
Replicates the Power Query logic from fac_TrialBalances.m
"""

import pandas as pd
from pathlib import Path
from datetime import date
import calendar
from utils import pad_account_code, apply_schema, validate_schema, write_to_duckdb


# Mapping Dutch month names to month numbers
MONTH_MAP = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "augustus": 8,
    "september": 9, "oktober": 10, "november": 11, "december": 12,
}


# Expected schema for fct_TrialBalances table
TRIAL_BALANCES_SCHEMA = {
    "CodeGrootboekrekening": "str",
    "NaamAdministratie": "str",
    "CodeRelatiekostenplaats": "Int64",  # Nullable integer for codes
    "NaamRelatiekostenplaats": "str",  # Force string even if all NULL
    "Value": "float64",
    "JaarPeriode": "str",
    "LastDate": "datetime64[ns]",
    "DisplayValue": "float64",
}


def parse_period_column(col_name: str) -> tuple[str, date] | None:
    """
    Parse period column name to extract year-month and last date.

    Handles two types of period columns:
    - Opening balance: 'Openingsbalans2025' → ('2025-00', date(2025, 1, 1))
    - Monthly periods: 'januari2025' → ('2025-01', date(2025, 1, 31))

    Args:
        col_name: Excel column name (case-insensitive).

    Returns:
        Tuple of (JaarPeriode, LastDate) or None if not a period column.
        - JaarPeriode: String in format 'YYYY-MM' (or 'YYYY-00' for opening)
        - LastDate: Last day of the period as a date object

    Example:
        >>> parse_period_column('januari2025')
        ('2025-01', datetime.date(2025, 1, 31))
        >>> parse_period_column('Openingsbalans2025')
        ('2025-00', datetime.date(2025, 1, 1))
        >>> parse_period_column('SomeOtherColumn')
        None
    """
    col_lower = col_name.lower()

    # Handle opening balance
    if col_lower.startswith("openingsbalans"):
        year = int(col_name[-4:])
        return (f"{year}-00", date(year, 1, 1))

    # Handle regular months
    for month_name, month_num in MONTH_MAP.items():
        if col_lower.startswith(month_name):
            year = int(col_name[-4:])
            last_day = calendar.monthrange(year, month_num)[1]
            return (f"{year}-{month_num:02d}", date(year, month_num, last_day))

    return None


def get_category(code1: str) -> str | None:
    """Determine category based on Code1 value."""
    if code1 in {"000", "010", "020", "030", "040", "050"}:
        return "Activa"
    elif code1 in {"060", "065", "070", "080"}:
        return "Passiva"
    elif code1 in {"500", "510"}:
        return "Gross Margin"
    elif code1 in {"520", "530", "540", "550"}:
        return "Expenses"
    return None


def calculate_display_value(row: pd.Series) -> float | None:
    """Calculate DisplayValue with sign correction based on category."""
    category = get_category(str(row["Code1"]))
    if category == "Activa":
        return row["Value"]
    elif category in {"Passiva", "Expenses", "Gross Margin"}:
        return row["Value"] * -1
    return None


def transform_trial_balances(input_path: Path, output_path: Path) -> None:
    """
    Transform Excel trial balance data to DuckDB database.

    Replicates Power Query logic from fac_TrialBalances.m with the following steps:
    1. Load Excel with monthly period columns
    2. Unpivot period columns (Openingsbalans, januari-december) to rows
    3. Calculate JaarPeriode (YYYY-MM format) and LastDate (last day of month)
    4. Calculate DisplayValue with sign corrections per category (Activa/Passiva)
    5. Generate synthetic profit rows by aggregating Gross Margin and Expenses
    6. Pad account codes to 4 digits
    7. Apply explicit schema for type safety
    8. Write to DuckDB with validation

    Args:
        input_path: Path to Excel file containing trial balance data.
            Expected columns: account codes, names, monthly periods.
        output_path: Path to output DuckDB database file.
            Table 'fct_TrialBalances' will be created/replaced.

    Raises:
        FileNotFoundError: If input Excel file doesn't exist.
        KeyError: If required columns are missing from Excel.
        Exception: If database write fails.

    Example:
        >>> from pathlib import Path
        >>> input_file = Path("import/2025_BalansenWinstverliesperperiode.xlsx")
        >>> output_file = Path("export/trial_balances.duckdb")
        >>> transform_trial_balances(input_file, output_file)
        Loading Excel file: import/2025_BalansenWinstverliesperperiode.xlsx
        Loaded 427 rows with 33 columns
        ...
        ✓ Verified: 1,775 rows written to fct_TrialBalances table
    """

    # Step 1: Load Excel
    print(f"Loading Excel file: {input_path}")
    df = pd.read_excel(input_path)
    print(f"Loaded {len(df)} rows with {len(df.columns)} columns")

    # Identify period columns (months + opening balance)
    period_columns = []
    for col in df.columns:
        parsed = parse_period_column(col)
        if parsed:
            period_columns.append((col, parsed[0], parsed[1]))

    print(f"Found {len(period_columns)} period columns")

    # ID columns to keep
    id_columns = [
        "CodeGrootboekrekening",
        "NaamAdministratie",
        "CodeRelatiekostenplaats",
        "NaamRelatiekostenplaats",
        "CodeDimensietype",  # This becomes Code0
        "CodeRapportagestructuurgroep1",  # This becomes Code1
    ]

    # Verify ID columns exist
    missing_cols = [col for col in id_columns if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Step 2: Unpivot (melt) period columns to long format
    print("Unpivoting period columns...")
    value_cols = [pc[0] for pc in period_columns]

    melted = df.melt(
        id_vars=id_columns,
        value_vars=value_cols,
        var_name="Period",
        value_name="Value",
    )

    # Add JaarPeriode and LastDate based on Period column
    period_info = {pc[0]: (pc[1], pc[2]) for pc in period_columns}
    melted["JaarPeriode"] = melted["Period"].map(lambda x: period_info[x][0])
    melted["LastDate"] = melted["Period"].map(lambda x: period_info[x][1])

    # Rename columns to match M code expectations
    melted = melted.rename(columns={
        "CodeDimensietype": "Code0",
        "CodeRapportagestructuurgroep1": "Code1",
    })

    # Convert Code1 to 3-digit zero-padded string
    melted["Code1"] = melted["Code1"].apply(lambda x: f"{int(x):03d}" if pd.notna(x) else None)

    # Drop the Period helper column
    melted = melted.drop(columns=["Period"])

    # Drop rows with null values
    fact_df = melted.dropna(subset=["Value"]).copy()
    print(f"After unpivot: {len(fact_df)} rows")

    # Step 3: Add DisplayValue (sign-corrected for reporting)
    print("Calculating DisplayValue...")
    fact_df["DisplayValue"] = fact_df.apply(calculate_display_value, axis=1)

    # Step 4: Calculate Profit rows for "Winst lopend boekjaar"
    print("Calculating profit rows...")
    balance_df = fact_df[fact_df["Code0"] == "BAS"].copy()

    profit_per_period = (
        balance_df.groupby(["JaarPeriode", "LastDate", "NaamAdministratie"])["Value"]
        .sum()
        .reset_index()
        .rename(columns={"Value": "Profit"})
    )

    # Create synthetic profit rows
    profit_rows = pd.DataFrame({
        "CodeGrootboekrekening": "9999",
        "LastDate": profit_per_period["LastDate"],
        "JaarPeriode": profit_per_period["JaarPeriode"],
        "NaamAdministratie": profit_per_period["NaamAdministratie"],
        "CodeRelatiekostenplaats": None,
        "NaamRelatiekostenplaats": None,
        "Code0": "BAS",
        "Code1": "060",
        "Value": profit_per_period["Profit"] * -1,
        "DisplayValue": profit_per_period["Profit"],
    })

    print(f"Created {len(profit_rows)} profit rows")

    # Step 5: Combine base rows + profit rows
    combined_df = pd.concat([fact_df, profit_rows], ignore_index=True)

    # Step 6: Remove helper columns not needed downstream
    final_df = combined_df.drop(columns=["Code0", "Code1"])

    # Step 7: Pad CodeGrootboekrekening to 4 digits with leading zeros
    final_df["CodeGrootboekrekening"] = pad_account_code(final_df["CodeGrootboekrekening"])

    # Step 8: Apply explicit schema to ensure correct types
    print("Applying schema...")
    final_df = apply_schema(final_df, TRIAL_BALANCES_SCHEMA)

    print(f"Final dataset: {len(final_df)} rows")
    print("\nFinal schema:")
    print(final_df.dtypes)

    # Validate schema before writing
    if not validate_schema(final_df, TRIAL_BALANCES_SCHEMA):
        print("Warning: Schema validation found issues, but continuing...")

    # Write to DuckDB using shared utility
    print(f"\nWriting to DuckDB: {output_path}")
    row_count = write_to_duckdb(
        final_df,
        str(output_path),
        "fct_TrialBalances",
        if_exists="replace"
    )
    print(f"✓ Verified: {row_count:,} rows written to fct_TrialBalances table")

    # Show sample
    import duckdb
    con = duckdb.connect(str(output_path))
    print("\nSample rows:")
    sample = con.execute("SELECT * FROM fct_TrialBalances LIMIT 5").fetchdf()
    print(sample)
    con.close()

    print("\nDone!")


def main() -> int:
    """CLI entry point."""
    import sys

    try:
        input_file = Path("import/2025_BalansenWinstverliesperperiode.xlsx")
        output_file = Path("export/trial_balances.duckdb")
        transform_trial_balances(input_file, output_file)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
