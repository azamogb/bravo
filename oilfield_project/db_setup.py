import os
import sqlite3
import pandas as pd
from config import DB_PATH,BASE_DIR



# --- 1. Connect (creates the .db file if missing) ---
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# --- 2. Create the table if it doesn't exist yet ---
cursor.execute("""
    CREATE TABLE IF NOT EXISTS production_data (
        Well_ID TEXT,
        Date TEXT,
        Oil_Rate REAL,
        Gas_Rate REAL,
        GOR REAL,
        Water_Cut REAL,
        Pressure REAL,
        Temperature REAL,
        Choke_Position REAL,
        Vibration REAL,
        Motor_Current REAL,
        Pump_Status INTEGER
    )
""")

# --- 3. Load the rows to insert from the existing CSV ---
df_csv = pd.read_csv(os.path.join(BASE_DIR, 'production_data.csv'))
rows_list = list(df_csv.itertuples(index=False, name=None))

# --- 4. Insert many rows at once ---
cursor.executemany(
    "INSERT INTO production_data VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
    rows_list
)
conn.commit()

print(f"Inserted {len(rows_list)} rows into production_data.")

# --- 5. Read into DataFrame (example query) ---
df = pd.read_sql_query(
    "SELECT * FROM production_data WHERE Well_ID = ?",
    conn,
    params=('WELL-01',)
)
print(df.head())

conn.close()






# import sqlite3
# import pandas as pd

# # Connect (creates file if missing)
# conn = sqlite3.connect('data/oilfield.db')
# cursor = conn.cursor()

# # Insert many rows at once
# cursor.executemany(
#     "INSERT INTO production_data VALUES (?,?,?,?,?,?,?)",
#     rows_list                    # list of tuples
# )
# conn.commit()

# # Read into DataFrame (data_loader.py)
# df = pd.read_sql_query(
#     "SELECT * FROM production_data WHERE Well_ID = ?",
#     conn,
#     params=('WELL-01',)
# )
# conn.close()
