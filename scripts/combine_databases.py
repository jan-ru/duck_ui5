"""
Combine multiple DuckDB databases into a single file.

Merges transactions and trial balances databases for unified analysis.
"""

import sys
from pathlib import Path

import duckdb


def combine_databases(
    transactions_db: str = "export/2023_transactions.db",
    trial_balances_db: str = "export/trial_balances.duckdb",
    output_db: str = "export/combined.db",
) -> None:
    """
    Combine multiple DuckDB databases into a single file.

    Args:
        transactions_db: Path to transactions database
        trial_balances_db: Path to trial balances database
        output_db: Path to combined output database
    """
    print(f"Combining databases into {output_db}...")

    # Ensure output directory exists
    Path(output_db).parent.mkdir(parents=True, exist_ok=True)

    # Create a new combined database
    con = duckdb.connect(output_db)

    # Attach and copy from transactions database
    print("  Copying transactions table...")
    con.execute(f"ATTACH '{transactions_db}' AS source1")
    con.execute("CREATE TABLE transactions AS SELECT * FROM source1.transactions")
    con.execute("DETACH source1")
    transaction_count = con.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    print(f"    ✓ Copied {transaction_count:,} rows")

    # Attach and copy from trial balances database
    print("  Copying fct_TrialBalances table...")
    con.execute(f"ATTACH '{trial_balances_db}' AS source2")
    con.execute("CREATE TABLE fct_TrialBalances AS SELECT * FROM source2.fct_TrialBalances")
    con.execute("DETACH source2")
    trial_balance_count = con.execute("SELECT COUNT(*) FROM fct_TrialBalances").fetchone()[0]
    print(f"    ✓ Copied {trial_balance_count:,} rows")

    # Close connection
    con.close()

    total_rows = transaction_count + trial_balance_count
    print(f"\n✓ Combined database created: {output_db}")
    print(f"  Tables: 2")
    print(f"  Total rows: {total_rows:,}")


def main() -> int:
    """CLI entry point."""
    try:
        combine_databases()
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
