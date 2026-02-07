"""
Shared utility functions for data transformation scripts.

This module provides common utilities used across the ETL pipeline:
- Account code padding (standardization)
- Data type schema application (type safety)
- Schema validation (data quality)
- DuckDB write operations (consistency)

Example:
    >>> import pandas as pd
    >>> from utils import pad_account_code, apply_schema
    >>>
    >>> # Pad account codes
    >>> codes = pd.Series(['10', '100', '1000'])
    >>> padded = pad_account_code(codes)
    >>> # Result: ['0010', '0100', '1000']
    >>>
    >>> # Apply schema
    >>> df = pd.DataFrame({'code': ['123', '456'], 'value': [1.5, 2.5]})
    >>> schema = {'code': 'str', 'value': 'float64'}
    >>> typed_df = apply_schema(df, schema)
"""

from typing import Optional
import duckdb
import pandas as pd


def pad_account_code(code_series: pd.Series) -> pd.Series:
    """
    Pad account codes (CodeGrootboekrekening) to 4 digits with leading zeros.

    This ensures consistent formatting for account codes across all tables,
    making joins and comparisons reliable.

    Padding rules:
        - 2 characters → pad with 2 zeros (e.g., "10" → "0010")
        - 3 characters → pad with 1 zero (e.g., "100" → "0100")
        - 4 characters → no change (e.g., "1000" → "1000")
        - 5+ characters → no change (preserves longer codes)

    Args:
        code_series: Pandas Series containing account codes.
            Can be numeric or string type.

    Returns:
        Pandas Series with padded account codes as strings.

    Example:
        >>> import pandas as pd
        >>> codes = pd.Series([10, 100, 1000, 12345])
        >>> pad_account_code(codes)
        0    0010
        1    0100
        2    1000
        3    12345
        dtype: object

    Note:
        Always converts to string type, even if input is numeric.
    """
    return code_series.astype(str).str.zfill(4)


def apply_schema(df: pd.DataFrame, schema: dict[str, str]) -> pd.DataFrame:
    """
    Apply explicit data types to DataFrame columns.

    This prevents DuckDB type inference issues, especially for:
    - All-NULL columns (would infer as INTEGER instead of VARCHAR)
    - Mixed-type columns (inconsistent inference)
    - Nullable numeric codes (need Int64, not int64)

    Supported type strings:
        - 'str': String/VARCHAR type
        - 'datetime64[ns]': Datetime/timestamp type
        - 'float64', 'Float64': Floating point numbers
        - 'int64': Integer (no NULLs allowed)
        - 'Int64': Nullable integer (pandas nullable type)
        - 'bool': Boolean type

    Args:
        df: DataFrame to apply types to.
        schema: Dictionary mapping column names to pandas dtype strings.

    Returns:
        DataFrame with corrected types. Returns a copy, doesn't modify in place.

    Raises:
        None: All type conversions use error handling. Warnings are printed
            for columns that fail conversion.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({
        ...     'code': ['10', '20'],
        ...     'value': [1.5, 2.5],
        ...     'date': ['2025-01-01', '2025-01-02'],
        ...     'nullable_int': [1, None]
        ... })
        >>> schema = {
        ...     'code': 'str',
        ...     'value': 'float64',
        ...     'date': 'datetime64[ns]',
        ...     'nullable_int': 'Int64'
        ... }
        >>> typed_df = apply_schema(df, schema)
        >>> typed_df.dtypes
        code                       object
        value                     float64
        date              datetime64[ns]
        nullable_int               Int64
        dtype: object

    See Also:
        - docs/DATA_TYPE_STRATEGY.md for comprehensive type handling guide
        - validate_schema() for schema validation before writing to database
    """
    df_typed = df.copy()

    for col, dtype in schema.items():
        if col not in df_typed.columns:
            print(f"Warning: Column '{col}' in schema but not found in DataFrame")
            continue

        try:
            if dtype == "datetime64[ns]":
                # Handle dates with explicit conversion
                df_typed[col] = pd.to_datetime(df_typed[col], errors="coerce")

            elif dtype in ["float64", "Float64"]:
                # Handle numeric with coercion (invalid values → NaN)
                df_typed[col] = pd.to_numeric(df_typed[col], errors="coerce")

            elif dtype in ["Int64", "int64"]:
                # Nullable integer for codes (Int64 allows NaN)
                df_typed[col] = pd.to_numeric(df_typed[col], errors="coerce").astype("Int64")

            elif dtype == "str":
                # Force string type (important for all-NULL columns)
                df_typed[col] = df_typed[col].astype("str")

            else:
                # Other types (bool, category, etc.)
                df_typed[col] = df_typed[col].astype(dtype)

        except Exception as e:
            print(f"Warning: Could not convert column '{col}' to {dtype}: {e}")

    return df_typed


def validate_schema(
    df: pd.DataFrame,
    expected_schema: dict[str, str],
    strict: bool = False,
) -> bool:
    """
    Validate DataFrame schema matches expected types.

    Checks for:
    - Missing columns (expected but not present)
    - Extra columns (present but not expected)
    - Type mismatches (column exists but wrong type)

    Args:
        df: DataFrame to validate.
        expected_schema: Dictionary of expected column names and types.
        strict: If True, raises ValueError on any issue.
                If False, prints warnings and returns False.

    Returns:
        True if schema matches perfectly, False if there are any issues.

    Raises:
        ValueError: Only if strict=True and validation fails.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'code': ['10', '20'], 'value': [1.5, 2.5]})
        >>> schema = {'code': 'object', 'value': 'float64'}
        >>> validate_schema(df, schema)
        True
        >>> validate_schema(df, {'code': 'int64', 'value': 'float64'})
        Warning: Type mismatch for 'code': expected int64, got object
        False
    """
    is_valid = True

    # Check for missing columns
    missing = set(expected_schema.keys()) - set(df.columns)
    if missing:
        msg = f"Missing required columns: {sorted(missing)}"
        if strict:
            raise ValueError(msg)
        print(f"Warning: {msg}")
        is_valid = False

    # Check for unexpected columns
    extra = set(df.columns) - set(expected_schema.keys())
    if extra:
        msg = f"Unexpected columns found: {sorted(extra)}"
        print(f"Info: {msg}")
        # Don't mark as invalid - extra columns are often okay

    # Check types match
    for col, expected_type in expected_schema.items():
        if col in df.columns:
            actual_type = str(df[col].dtype)
            # Normalize type comparison (e.g., 'object' == 'str')
            if actual_type != expected_type and not (
                actual_type == "object" and expected_type == "str"
            ):
                msg = f"Type mismatch for '{col}': expected {expected_type}, got {actual_type}"
                if strict:
                    raise ValueError(msg)
                print(f"Warning: {msg}")
                is_valid = False

    return is_valid


def write_to_duckdb(
    df: pd.DataFrame,
    output_path: str,
    table_name: str,
    if_exists: str = "replace",
) -> int:
    """
    Write DataFrame to DuckDB database with consistent error handling.

    Provides a standard interface for writing DataFrames to DuckDB,
    with automatic directory creation and row count verification.

    Args:
        df: DataFrame to write.
        output_path: Path to DuckDB database file.
        table_name: Name of table to create.
        if_exists: What to do if table exists:
            - 'replace': Drop and recreate table (default)
            - 'append': Append rows to existing table
            - 'fail': Raise error if table exists

    Returns:
        Number of rows written to database.

    Raises:
        ValueError: If if_exists is not valid.
        Exception: If database write fails.

    Example:
        >>> import pandas as pd
        >>> df = pd.DataFrame({'a': [1, 2, 3], 'b': [4, 5, 6]})
        >>> rows = write_to_duckdb(df, 'export/test.db', 'my_table')
        >>> print(f"Wrote {rows} rows")
        Wrote 3 rows
    """
    from pathlib import Path

    if if_exists not in ["replace", "append", "fail"]:
        raise ValueError(f"if_exists must be 'replace', 'append', or 'fail', got: {if_exists}")

    # Ensure output directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Connect to database
    con = duckdb.connect(str(output_path))

    try:
        if if_exists == "replace":
            con.execute(f"DROP TABLE IF EXISTS {table_name}")
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
        elif if_exists == "append":
            # Check if table exists
            tables = con.execute("SHOW TABLES").fetchall()
            table_exists = any(t[0] == table_name for t in tables)
            if table_exists:
                con.execute(f"INSERT INTO {table_name} SELECT * FROM df")
            else:
                con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")
        elif if_exists == "fail":
            con.execute(f"CREATE TABLE {table_name} AS SELECT * FROM df")

        # Verify row count
        row_count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        return row_count

    finally:
        con.close()
