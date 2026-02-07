# Data Type Handling Strategy

## Overview

This document explains how we handle data types in the Excel → Pandas → DuckDB pipeline.

## Strategy: Explicit Types in Pandas + Optional DuckDB Schema

We use a **hybrid approach**:
1. **Define explicit dtypes in Pandas** after reading Excel
2. **Optionally provide DuckDB schema** for validation
3. **Document expected schema** in code comments

## Why Pandas Type Handling?

### ✅ Advantages:
- **Early validation**: Catch type issues during transformation
- **Data cleaning**: Convert/coerce types before database insert
- **Explicit control**: Document expected types in code
- **Easier debugging**: See type issues with actual data
- **Flexibility**: Handle mixed types, nulls, edge cases

### ❌ Problem Without Explicit Types:
```python
# Excel has empty "Name" column
# Pandas infers: float64 (NaN is float)
# DuckDB infers: INTEGER (sees numeric NULLs)
# Result: VARCHAR column becomes INTEGER!
```

## Implementation Pattern

### 1. Define Schema as Constants

```python
# Define expected schema at top of script
TRIAL_BALANCES_SCHEMA = {
    'CodeGrootboekrekening': 'str',
    'NaamAdministratie': 'str',
    'CodeRelatiekostenplaats': 'Int64',  # Nullable integer
    'NaamRelatiekostenplaats': 'str',
    'Value': 'float64',
    'JaarPeriode': 'str',
    'LastDate': 'datetime64[ns]',
    'DisplayValue': 'float64'
}

TRANSACTIONS_SCHEMA = {
    'NaamAdministratie': 'str',
    'CodeGrootboekrekening': 'str',
    'NaamGrootboekrekening': 'str',
    'Code': 'str',
    'Boekingsnummer': 'Int64',  # Nullable integer
    'Boekdatum': 'datetime64[ns]',
    'Periode': 'str',
    'Code1': 'str',
    'Omschrijving': 'str',
    'Saldo': 'float64',
    'Factuurnummer': 'str'
}
```

### 2. Apply Schema After Transformations

```python
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
            if dtype == 'datetime64[ns]':
                # Handle dates specially
                df_typed[col] = pd.to_datetime(df_typed[col], errors='coerce')
            elif dtype in ['float64', 'Float64']:
                # Handle numeric with coercion
                df_typed[col] = pd.to_numeric(df_typed[col], errors='coerce')
            elif dtype in ['Int64', 'int64']:
                # Nullable integer for codes
                df_typed[col] = pd.to_numeric(df_typed[col], errors='coerce').astype('Int64')
            else:
                # String and other types
                df_typed[col] = df_typed[col].astype(dtype, errors='ignore')
        else:
            print(f"Warning: Column {col} not found in DataFrame")

    return df_typed
```

### 3. Use in Transformation Scripts

```python
# After all transformations, before writing to DuckDB
final_df = apply_schema(final_df, TRIAL_BALANCES_SCHEMA)

# Optionally validate
print("\nFinal schema:")
print(final_df.dtypes)
```

### 4. Optional: DuckDB Explicit Schema

For extra validation, create table with explicit schema:

```python
# Option A: Let DuckDB infer from properly-typed Pandas
con.execute("CREATE TABLE fct_TrialBalances AS SELECT * FROM final_df")

# Option B: Explicit DuckDB schema (stronger validation)
con.execute("""
    CREATE TABLE fct_TrialBalances (
        CodeGrootboekrekening VARCHAR,
        NaamAdministratie VARCHAR,
        CodeRelatiekostenplaats INTEGER,
        NaamRelatiekostenplaats VARCHAR,  -- Prevent INTEGER inference!
        Value DOUBLE,
        JaarPeriode VARCHAR,
        LastDate DATE,
        DisplayValue DOUBLE
    )
""")
con.execute("INSERT INTO fct_TrialBalances SELECT * FROM final_df")
```

## Common Gotchas

### 1. All-NULL Columns
```python
# Problem: Empty columns get inferred as float64
df['EmptyColumn']  # float64 (NaN)

# Solution: Explicitly type
df['EmptyColumn'] = df['EmptyColumn'].astype('str')
```

### 2. Mixed Numeric Strings
```python
# Problem: Column has "123", "ABC", causes issues
df['Code'] = pd.to_numeric(df['Code'], errors='coerce')  # ABC → NaN

# Solution: Keep as string
df['Code'] = df['Code'].astype('str')
```

### 3. Date Parsing
```python
# Problem: Different date formats
df['Date'] = df['Date']  # Might be string, datetime, or number

# Solution: Explicit conversion
df['Date'] = pd.to_datetime(df['Date'], errors='coerce', format='%Y-%m-%d')
```

### 4. Nullable Integers
```python
# Problem: Integer columns with NaN become float64
df['Code'] = df['Code']  # float64 if any NaN

# Solution: Use nullable Int64
df['Code'] = df['Code'].astype('Int64')  # Supports NaN
```

## Type Mapping Reference

| Use Case | Pandas Type | DuckDB Type | Notes |
|----------|-------------|-------------|-------|
| Account codes (with NULLs) | `str` | `VARCHAR` | Always string for codes |
| Names/Text | `str` | `VARCHAR` | Force string even if empty |
| Amounts/Values | `float64` | `DOUBLE` | Financial precision |
| Counts (no NULLs) | `int64` | `BIGINT` | Standard integer |
| Counts (with NULLs) | `Int64` | `BIGINT` | Nullable integer |
| Dates | `datetime64[ns]` | `DATE` or `TIMESTAMP` | Parse explicitly |
| Periods (2025-01) | `str` | `VARCHAR` | Keep as string for flexibility |
| Flags/Booleans | `bool` | `BOOLEAN` | True/False |

## Validation Strategy

```python
def validate_schema(df: pd.DataFrame, expected_schema: dict) -> None:
    """Validate DataFrame matches expected schema."""

    # Check for missing columns
    missing = set(expected_schema.keys()) - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    # Check for unexpected columns
    extra = set(df.columns) - set(expected_schema.keys())
    if extra:
        print(f"Warning: Unexpected columns: {extra}")

    # Check types match
    for col, expected_type in expected_schema.items():
        if col in df.columns:
            actual_type = str(df[col].dtype)
            if actual_type != expected_type:
                print(f"Warning: {col} type mismatch. Expected {expected_type}, got {actual_type}")
```

## Best Practices

1. ✅ **Define schema constants** at top of each script
2. ✅ **Apply types explicitly** after transformations
3. ✅ **Use nullable types** (Int64, Float64) for codes with possible NULLs
4. ✅ **Parse dates explicitly** with pd.to_datetime()
5. ✅ **Keep codes as strings** (account codes, period codes, etc.)
6. ✅ **Validate before writing** to database
7. ✅ **Document expected types** in code comments
8. ✅ **Use coercion wisely** (errors='coerce' for numeric, errors='ignore' for others)

## Example: Full Implementation

See updated `transform_trial_balances.py` for complete example.
