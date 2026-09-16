"""
Single entry point for reading well records.

    load_data()        -> full DataFrame, every well, sorted by date
    load_well(well)    -> one well's rows (optionally only the last N days)
    list_wells()       -> the well IDs actually present in the data

Reads from the SQLite database created by db_setup.py. If the database
is missing or empty, falls back to an in-memory synthetic dataset
(same generator as generate_data.py) so the dashboard still runs.
"""

import os
import random
import sqlite3
import datetime

import pandas as pd

from config import DB_PATH, WELL_IDS, NUM_DAYS


COLUMNS = [
    'Well_ID', 'Date', 'Oil_Rate', 'Gas_Rate', 'GOR', 'Water_Cut',
    'Pressure', 'Temperature', 'Choke_Position', 'Vibration',
    'Motor_Current', 'Pump_Status'
]

_cache = None


def _synthetic_data():
    rng = random.Random(42)
    start_date = datetime.date(2026, 4, 1)
    rows = []

    for well in WELL_IDS:
        for day in range(NUM_DAYS):
            is_failure = rng.random() < 0.15
            pressure = rng.uniform(1200, 2800)

            if is_failure:
                pressure *= 0.6
                oil_rate = rng.uniform(50, 120)
                vibration = rng.uniform(4.0, 9.0)
                motor_current = rng.uniform(80, 140)
            else:
                oil_rate = rng.uniform(200, 500)
                vibration = rng.uniform(0.5, 3.0)
                motor_current = rng.uniform(30, 60)

            gas_rate = oil_rate * rng.uniform(0.8, 1.5)
            gor = round((gas_rate * 1000) / oil_rate, 2) if oil_rate > 0 else 0

            rows.append((
                well,
                (start_date + datetime.timedelta(days=day)).isoformat(),
                round(oil_rate, 2), round(gas_rate, 2), gor,
                round(rng.uniform(5, 60), 2), round(pressure, 2),
                round(rng.uniform(60, 120), 2), round(rng.uniform(20, 100), 1),
                round(vibration, 2), round(motor_current, 2),
                1 if is_failure else 0,
            ))

    return pd.DataFrame(rows, columns=COLUMNS)


def load_data(force_reload=False):
    """Returns every well's records as a DataFrame (cached after first read)."""

    global _cache

    if _cache is not None and not force_reload:
        return _cache.copy()

    df = None

    if os.path.isfile(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            df = pd.read_sql_query("SELECT * FROM production_data", conn)
            conn.close()
        except Exception as error:
            print(f"data_loader: could not read {DB_PATH}: {error}")
            df = None

    if df is None or df.empty:
        print("data_loader: database missing or empty, using synthetic data.")
        df = _synthetic_data()

    df["Date"] = pd.to_datetime(df["Date"])
    df = (
        df.drop_duplicates(subset=["Well_ID", "Date"], keep="last")
          .sort_values(["Well_ID", "Date"])
          .reset_index(drop=True)
    )

    _cache = df
    return df.copy()


def load_well(well, days=None):
    """Returns one well's records, newest last. days=N keeps only the last N."""

    df = load_data()
    well_df = df[df["Well_ID"] == well]

    if days is not None:
        well_df = well_df.tail(days)

    return well_df.reset_index(drop=True)


def list_wells():
    return sorted(load_data()["Well_ID"].unique().tolist())