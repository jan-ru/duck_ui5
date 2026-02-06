"""
Transform Excel trial balance data to DuckDB database.
Replicates the Power Query logic from fac_TrialBalances.m
"""

import pandas as pd
import duckdb
from pathlib import Path
from datetime import date
import calendar


# Mapping Dutch month names to month numbers
MONTH_MAP = {
    "januari": 1, "februari": 2, "maart": 3, "april": 4,
    "mei": 5, "juni": 6, "juli": 7, "augustus": 8,
    "september": 9, "oktober": 10, "november": 11, "december": 12,
}


def parse_period_column(col_name: str) -> tuple[str, date] | None:
    """
    Parse column name like 'januari2025' or 'Openingsbalans2025' to (JaarPeriode, LastDate).
    Returns None for non-period columns.
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
    """Transform Excel trial balance data to DuckDB."""

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

    # Step 7: Set proper types
    final_df["Value"] = pd.to_numeric(final_df["Value"], errors="coerce")
    final_df["DisplayValue"] = pd.to_numeric(final_df["DisplayValue"], errors="coerce")

    print(f"Final dataset: {len(final_df)} rows")

    # Write to DuckDB
    print(f"Writing to DuckDB: {output_path}")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(output_path))
    con.execute("DROP TABLE IF EXISTS fct_TrialBalances")
    con.execute("CREATE TABLE fct_TrialBalances AS SELECT * FROM final_df")

    # Verify
    row_count = con.execute("SELECT COUNT(*) FROM fct_TrialBalances").fetchone()[0]
    print(f"Verified: {row_count} rows written to fct_TrialBalances table")

    # Show sample
    print("\nSample rows:")
    sample = con.execute("SELECT * FROM fct_TrialBalances LIMIT 5").fetchdf()
    print(sample)

    con.close()
    print("\nDone!")


if __name__ == "__main__":
    input_file = Path("import/2025_BalansenWinstverliesperperiode.xlsx")
    output_file = Path("export/trial_balances.duckdb")

    transform_trial_balances(input_file, output_file)
