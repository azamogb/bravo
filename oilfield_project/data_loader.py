import sqlite3
import pandas as pd
from config import DB_PATH


def get_connection():
    """Return a sqlite3 connection."""
    return sqlite3.connect(DB_PATH)


def load_all_data() -> pd.DataFrame:
    """Load entire production_data table."""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM production_data", conn)
    conn.close()
    return df


def load_well_data(well_id: str) -> pd.DataFrame:
    """Filter to a single well, sorted by date."""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM production_data WHERE Well_ID = ? ORDER BY Date",
        conn, params=(well_id,)
    )
    conn.close()
    return df


def get_well_ids() -> list:
    """Return list of unique well IDs."""
    df = load_all_data()
    return sorted(df['Well_ID'].unique().tolist())