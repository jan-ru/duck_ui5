import pandas as pd
import duckdb

# Read the Excel file
df = pd.read_excel('import/DUMP_13jun25.xls')

# Print dimensions
print(f"Number of rows: {len(df)}")
print(f"Number of columns: {len(df.columns)}")

# Delete specified columns
df = df.drop(columns=['Btwbedrag', 'Boekingsstatus', 'CodeAdministratie', 'Code2', 'Debet', 'Credit', 'Btwcode', 'Nummer'])

# Convert Boekdatum to proper datetime type (from timestamp milliseconds)
df['Boekdatum'] = pd.to_datetime(df['Boekdatum'], unit='ms')

# Pad CodeGrootboekrekening to 4 positions with leading zeros
df['CodeGrootboekrekening'] = df['CodeGrootboekrekening'].astype(str).str.zfill(4)

# Write to DuckDB
db_path = 'export/2023_transactions.db'
con = duckdb.connect(db_path)
con.execute("CREATE OR REPLACE TABLE transactions AS SELECT * FROM df")
con.close()

print(f"\nDatabase written successfully to {db_path}")
print(f"Final dimensions: {len(df)} rows, {len(df.columns)} columns")
