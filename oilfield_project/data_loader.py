"""
Single entry point for reading well records.

    load_data()                 -> full DataFrame, every well, sorted by date
    load_data(force_reload=True)-> re-read the DB (use this when live_feed.py is running)
    load_well(well, days=N)     -> one well's rows, optionally only the last N days
    latest(well)                -> the most recent row for a well (live view)
    list_wells()                -> the well IDs actually present in the data

Reads from the SQLite database created by db_setup.py. If the database
is missing or empty, falls back to an in-memory synthetic dataset
(same generator as generate_data.py) so the dashboard still runs.
"""

import os
import sqlite3

import pandas as pd

from config import DB_PATH
from simulator import COLUMNS

_cache = None


def _synthetic_data():
    from generate_data import build_dataframe
    return build_dataframe()


def load_data(force_reload=False):
    """Returns every well's records as a DataFrame.

    Cached after the first read. Pass force_reload=True to pick up rows
    that live_feed.py has written since the last call.
    """
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

    df = df[COLUMNS]
    df["Date"] = pd.to_datetime(df["Date"])
    df = (
        df.drop_duplicates(subset=["Well_ID", "Date"], keep="last")
          .sort_values(["Well_ID", "Date"])
          .reset_index(drop=True)
    )

    _cache = df
    return df.copy()


def load_well(well, days=None, force_reload=False):
    """Returns one well's records, newest last.

    days=N keeps only the rows from the last N days of that well's data
    (time-based, so it works whether rows are hourly or per-minute).
    """
    df = load_data(force_reload=force_reload)
    well_df = df[df["Well_ID"] == well]

    if days is not None and not well_df.empty:
        cutoff = well_df["Date"].max() - pd.Timedelta(days=days)
        well_df = well_df[well_df["Date"] >= cutoff]

    return well_df.reset_index(drop=True)


def latest(well, force_reload=True):
    """The most recent row for a well, as a Series (None if no data)."""
    well_df = load_well(well, force_reload=force_reload)
    return None if well_df.empty else well_df.iloc[-1]


def list_wells():
    return sorted(load_data()["Well_ID"].unique().tolist())