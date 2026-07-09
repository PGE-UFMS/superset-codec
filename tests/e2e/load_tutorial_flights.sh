#!/usr/bin/env bash
# Runs inside the Superset container.
# Creates (or opens) the examples.db SQLite file and loads tutorial_flights.csv
# into the main.tutorial_flights table.

set -euo pipefail

CSV_URL="https://raw.githubusercontent.com/apache-superset/examples-data/d4d3a59b04835d2665bacfe264416662c44c9e7d/tutorial_flights.csv"
DB_PATH="${DB_PATH:-/app/superset_home/examples.db}"
TABLE="${TABLE:-tutorial_flights}"

python3 - "$CSV_URL" "$DB_PATH" "$TABLE" <<'PY'
import sqlite3
import sys
import pandas as pd

csv_url, db_path, table = sys.argv[1:]

df = pd.read_csv(csv_url, na_values=["#N/A", "N/A", "NA", "null", "NULL"])
df.columns = [c.lower().replace(" ", "_") for c in df.columns]
df["travel_date"] = pd.to_datetime(df["travel_date"]).dt.date.astype(str)

with sqlite3.connect(db_path) as conn:
    df.to_sql(table, conn, if_exists="replace", index=False)
    rows = conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

print(f"loaded {rows} rows into {db_path}::main.{table}")
PY
