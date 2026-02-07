"""
Validate that all account codes from transactions exist in trial balances.

This script checks data consistency between the two source files:
- DUMP_13jun25.xls (transactions)
- 2025_BalansenWinstverliesperperiode.xlsx (trial balances)

Ensures all CodeGrootboekrekening values in transactions have corresponding
entries in the trial balances, which is required for proper reporting.
"""

import sys
from pathlib import Path
from typing import Tuple

import pandas as pd

from utils import pad_account_code


def read_transaction_codes(file_path: Path) -> set[str]:
    """
    Read and extract unique account codes from transactions file.

    Args:
        file_path: Path to DUMP_13jun25.xls file.

    Returns:
        Set of unique padded account codes (4 digits).

    Raises:
        FileNotFoundError: If transactions file doesn't exist.
    """
    print(f"Reading transactions: {file_path}")
    df = pd.read_excel(file_path)

    # Apply same padding logic as in transformation scripts
    codes = pad_account_code(df["CodeGrootboekrekening"])
    unique_codes = set(codes.unique())

    print(f"  Found {len(df):,} transactions")
    print(f"  Found {len(unique_codes)} unique account codes")

    return unique_codes


def read_trial_balance_codes(file_path: Path) -> set[str]:
    """
    Read and extract unique account codes from trial balances file.

    Args:
        file_path: Path to trial balances Excel file.

    Returns:
        Set of unique padded account codes (4 digits).

    Raises:
        FileNotFoundError: If trial balances file doesn't exist.
    """
    print(f"\nReading trial balances: {file_path}")
    df = pd.read_excel(file_path)

    # Apply same padding logic as in transformation scripts
    codes = pad_account_code(df["CodeGrootboekrekening"])
    unique_codes = set(codes.unique())

    print(f"  Found {len(df):,} rows")
    print(f"  Found {len(unique_codes)} unique account codes")

    return unique_codes


def validate_codes(
    transaction_codes: set[str], trial_balance_codes: set[str]
) -> Tuple[set[str], set[str], set[str]]:
    """
    Validate account code consistency between transactions and trial balances.

    Args:
        transaction_codes: Set of account codes from transactions.
        trial_balance_codes: Set of account codes from trial balances.

    Returns:
        Tuple of (missing_codes, extra_codes, common_codes):
        - missing_codes: Codes in transactions but NOT in trial balances
        - extra_codes: Codes in trial balances but NOT in transactions
        - common_codes: Codes present in both
    """
    missing_codes = transaction_codes - trial_balance_codes
    extra_codes = trial_balance_codes - transaction_codes
    common_codes = transaction_codes & trial_balance_codes

    return missing_codes, extra_codes, common_codes


def print_validation_report(
    transaction_codes: set[str],
    trial_balance_codes: set[str],
    missing_codes: set[str],
    extra_codes: set[str],
    common_codes: set[str],
) -> bool:
    """
    Print comprehensive validation report.

    Args:
        transaction_codes: All codes from transactions.
        trial_balance_codes: All codes from trial balances.
        missing_codes: Codes missing from trial balances.
        extra_codes: Codes only in trial balances.
        common_codes: Codes present in both.

    Returns:
        True if validation passed (no missing codes), False otherwise.
    """
    print("\n" + "=" * 80)
    print("ACCOUNT CODE VALIDATION REPORT")
    print("=" * 80)

    print("\n📊 SUMMARY")
    print("-" * 80)
    print(f"Transaction codes:     {len(transaction_codes):>4} unique codes")
    print(f"Trial balance codes:   {len(trial_balance_codes):>4} unique codes")
    print(f"Codes in both:         {len(common_codes):>4} codes")
    print(f"Coverage:              {len(common_codes) / len(transaction_codes) * 100:>5.1f}%")

    print("\n🔍 VALIDATION RESULTS")
    print("-" * 80)

    # Check if all transaction codes exist in trial balances
    if not missing_codes:
        print("✅ VALIDATION PASSED: All transaction codes exist in trial balances")
        validation_passed = True
    else:
        print(f"❌ VALIDATION FAILED: {len(missing_codes)} transaction codes NOT found in trial balances")
        validation_passed = False

        print("\n❗ MISSING CODES (in transactions but NOT in trial balances):")
        print("-" * 80)
        for code in sorted(missing_codes):
            print(f"  - {code}")

    # Report extra codes (informational, not an error)
    if extra_codes:
        print(f"\nℹ️  INFO: {len(extra_codes)} codes exist only in trial balances (not used in transactions)")
        print("-" * 80)
        if len(extra_codes) <= 20:
            for code in sorted(extra_codes):
                print(f"  - {code}")
        else:
            # Show first 20 if too many
            print(f"  Showing first 20 of {len(extra_codes)} codes:")
            for code in sorted(extra_codes)[:20]:
                print(f"  - {code}")
            print(f"  ... and {len(extra_codes) - 20} more")

    # Sample of matching codes
    if common_codes:
        print(f"\n✓ SAMPLE OF MATCHING CODES (showing 10 of {len(common_codes)}):")
        print("-" * 80)
        for code in sorted(common_codes)[:10]:
            print(f"  - {code}")

    print("\n" + "=" * 80)

    return validation_passed


def validate_account_codes(
    transactions_path: str = "import/DUMP_13jun25.xls",
    trial_balances_path: str = "import/2025_BalansenWinstverliesperperiode.xlsx",
) -> bool:
    """
    Validate account code consistency between source files.

    Args:
        transactions_path: Path to transactions Excel file.
        trial_balances_path: Path to trial balances Excel file.

    Returns:
        True if validation passed (all codes exist), False otherwise.

    Example:
        >>> validate_account_codes()
        Reading transactions: import/DUMP_13jun25.xls
          Found 7,388 transactions
          Found 42 unique account codes
        ...
        ✅ VALIDATION PASSED: All transaction codes exist in trial balances
        True
    """
    try:
        # Read account codes from both files
        transaction_codes = read_transaction_codes(Path(transactions_path))
        trial_balance_codes = read_trial_balance_codes(Path(trial_balances_path))

        # Validate consistency
        missing_codes, extra_codes, common_codes = validate_codes(
            transaction_codes, trial_balance_codes
        )

        # Print report
        validation_passed = print_validation_report(
            transaction_codes,
            trial_balance_codes,
            missing_codes,
            extra_codes,
            common_codes,
        )

        return validation_passed

    except FileNotFoundError as e:
        print(f"\n❌ ERROR: File not found: {e}", file=sys.stderr)
        return False
    except KeyError as e:
        print(
            f"\n❌ ERROR: Required column not found: {e}",
            file=sys.stderr,
        )
        print("   Ensure both files contain 'CodeGrootboekrekening' column", file=sys.stderr)
        return False
    except Exception as e:
        print(f"\n❌ ERROR: Validation failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return False


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate account codes between transactions and trial balances"
    )
    parser.add_argument(
        "--transactions",
        default="import/DUMP_13jun25.xls",
        help="Path to transactions Excel file (default: import/DUMP_13jun25.xls)",
    )
    parser.add_argument(
        "--trial-balances",
        default="import/2025_BalansenWinstverliesperperiode.xlsx",
        help="Path to trial balances Excel file (default: import/2025_BalansenWinstverliesperperiode.xlsx)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code if validation fails",
    )

    args = parser.parse_args()

    # Run validation
    validation_passed = validate_account_codes(
        transactions_path=args.transactions,
        trial_balances_path=args.trial_balances,
    )

    # Return appropriate exit code
    if args.strict and not validation_passed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
