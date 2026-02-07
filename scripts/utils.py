"""
Shared utility functions for data transformation scripts.
"""

import pandas as pd


def pad_account_code(code_series: pd.Series) -> pd.Series:
    """
    Pad CodeGrootboekrekening to 4 digits with leading zeros.

    Padding rules:
    - 2 characters → pad with 2 zeros (e.g., "10" → "0010")
    - 3 characters → pad with 1 zero (e.g., "100" → "0100")
    - 4 characters → no change (e.g., "1000" → "1000")

    Args:
        code_series: Pandas Series containing account codes

    Returns:
        Pandas Series with padded account codes
    """
    return code_series.astype(str).str.zfill(4)
