import os
import sqlite3
import pandas as pd

from config import DB_PATH, CSV_PATH


# --- 1. Connect (creates the .db file if missing) ---
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --- 2. Create the table if it doesn't exist yet ---
# (Well_ID, Date) is the primary key so re-running this script
# updates rows in place instead of appending duplicates every time.
cursor.execute("""
    CREATE TABLE IF NOT EXISTS production_data (
        Well_ID TEXT NOT NULL,
        Date TEXT NOT NULL,
        Oil_Rate REAL,
        Gas_Rate REAL,
        GOR REAL,
        Water_Cut REAL,
        Pressure REAL,
        Temperature REAL,
        Choke_Position REAL,
        Vibration REAL,
        Motor_Current REAL,
        Pump_Status INTEGER,
        PRIMARY KEY (Well_ID, Date)
    )
""")

# --- 3. Load the rows to insert from the existing CSV ---
df_csv = pd.read_csv(CSV_PATH)
rows_list = list(df_csv.itertuples(index=False, name=None))

# --- 4. Insert (or replace) many rows at once ---
cursor.executemany(
    "INSERT OR REPLACE INTO production_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
    rows_list
)
conn.commit()

print(f"Inserted/updated {len(rows_list)} rows in production_data.")

# --- 5. Read into DataFrame (example query) ---
df = pd.read_sql_query(
    "SELECT * FROM production_data WHERE Well_ID = ?",
    conn,
    params=('WELL-01',)
)
print(df.head())

conn.close()