"""
Generates NUM_DAYS of historical well records (one row per
HISTORY_STEP_MINUTES) and writes them to production_data.csv.
Then run db_setup.py to load them, and train_model.py to train.

    python generate_data.py

History ENDS at the current hour, so live_feed.py can pick up right
where it stops. Each well follows a story: a healthy baseline with
noise, plus DEGRADATION EPISODES where vibration, motor current and
temperature creep up while oil rate and pressure fall, until the pump
is recorded as failed (Pump_Status = 1). After a repair the well
returns to baseline.

Edit EPISODES to change the story.
"""

import datetime

import pandas as pd

from config import CSV_PATH, WELL_IDS, NUM_DAYS, HISTORY_STEP_MINUTES
from simulator import COLUMNS, make_baseline, sample_row, well_rng


# Episodes per well: (start_day, ramp_days, failed_days, repaired)
# Day indices count back from the END of history (day NUM_DAYS-1 = today).
# Several episodes per well is fine - more failures = better training data.
EPISODES = {
    "WELL-01": [(10, 4, 2, True), (35, 6, 3, True), (NUM_DAYS - 8, 7, 3, False)],
    "WELL-02": [(50, 5, 2, True)],
    "WELL-03": [(20, 8, 2, True), (NUM_DAYS - 7, 10, 2, False)],
    "WELL-04": [(5, 5, 2, True), (40, 4, 3, True), (70, 6, 2, True)],
    "WELL-05": [(2, 5, 2, True), (30, 3, 1, True), (60, 5, 2, True)],
}


def severity(day, episodes):
    """0 = healthy ... 1 = fully failed, for a (fractional) day index."""
    worst = 0.0
    for start, ramp, failed_days, repaired in episodes:
        if day < start:
            continue
        end_of_failure = start + ramp + failed_days
        if day < start + ramp:
            level = min(1.0, (day - start) / ramp + 1e-9)
        elif day < end_of_failure or not repaired:
            level = 1.0
        else:
            level = 0.0
        worst = max(worst, level)
    return worst


def history_end():
    """Last history timestamp: the current hour, floored."""
    return datetime.datetime.now().replace(minute=0, second=0, microsecond=0)


def build_dataframe():
    step = datetime.timedelta(minutes=HISTORY_STEP_MINUTES)
    steps_per_day = (24 * 60) // HISTORY_STEP_MINUTES
    total_steps = NUM_DAYS * steps_per_day
    start = history_end() - step * (total_steps - 1)

    rows = []
    for well in WELL_IDS:
        base = make_baseline(well)
        rng = well_rng(well, "history")
        episodes = EPISODES.get(well, [])
        for i in range(total_steps):
            t = start + step * i
            s = severity(i / steps_per_day, episodes)
            rows.append(sample_row(well, t, s, base, rng))

    return pd.DataFrame(rows, columns=COLUMNS)


if __name__ == "__main__":
    df = build_dataframe()
    df.to_csv(CSV_PATH, index=False)
    print(f"Wrote {len(df)} rows to {CSV_PATH}  "
          f"({df['Date'].min()} -> {df['Date'].max()}, "
          f"failure rows: {int(df['Pump_Status'].sum())})")