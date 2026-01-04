# inspect_sqlite.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "vectorstore/chroma" / "chroma.sqlite3"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

print("Database:", DB_PATH)

# List all tables
cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [t[0] for t in cur.fetchall()]
print("\nTables found:", tables)

# Inspect schema and show first few rows
for t in tables:
    print(f"\n--- Table: {t} ---")
    cur.execute(f"PRAGMA table_info({t})")
    schema = cur.fetchall()
    for col in schema:
        print(f"  {col}")
    cur.execute(f"SELECT * FROM {t} LIMIT 1;")
    rows = cur.fetchall()
    for r in rows:
        print("  Sample row:", r)

conn.close()
