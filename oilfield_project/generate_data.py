"""
Generates realistic-looking daily well records and writes them to
production_data.csv (then run db_setup.py to load them into the DB).

    python generate_data.py

Unlike a per-day coin flip, each well follows a story: a healthy
baseline with day-to-day noise, and optional DEGRADATION EPISODES in
which vibration, motor current and temperature creep up while oil rate
and pressure fall over several days, until the pump is recorded as
failed (Pump_Status = 1). After a repair the well returns to baseline.

Because failures build up gradually, the ML model's risk score rises
over days (20% -> 55% -> 85%) instead of jumping 0% -> 100%.

Edit EPISODES to change the story for the demo.
"""

import random
import datetime

import pandas as pd

from config import CSV_PATH, WELL_IDS, NUM_DAYS


START_DATE = datetime.date(2026, 4, 1)

# Degradation episodes per well:
#   (start_day, ramp_days, failed_days, repaired)
#   start_day    day index (0-based) the problem begins
#   ramp_days    days for severity to climb from 0 to 1
#   failed_days  days the pump stays failed at full severity
#   repaired     True -> returns to baseline afterwards
#                False -> stays failed to the end of the data
#
# Story for the demo (30 days):
#   WELL-01  degrades over the last week and is failed right now  -> HIGH RISK
#   WELL-02  healthy throughout                                    -> NORMAL
#   WELL-03  a week into degradation, not failed yet               -> WARNING
#   WELL-04  failed mid-month, repaired, healthy now               -> NORMAL
#   WELL-05  brief fault in the first week, repaired; noisier gear -> NORMAL
EPISODES = {
    "WELL-01": [(21, 7, 3, False)],
    "WELL-02": [],
    "WELL-03": [(22, 10, 2, False)],
    "WELL-04": [(9, 5, 2, True)],
    "WELL-05": [(2, 5, 2, True)],
}


def _severity(day, episodes):
    """0 = healthy ... 1 = fully failed, for the given day."""
    worst = 0.0
    for start, ramp, failed_days, repaired in episodes:
        if day < start:
            continue
        end_of_failure = start + ramp + failed_days
        if day < start + ramp:
            level = (day - start + 1) / ramp
        elif day < end_of_failure or not repaired:
            level = 1.0
        else:
            level = 0.0                      # repaired
        worst = max(worst, level)
    return worst


def build_dataframe(seed=42):
    rng = random.Random(seed)
    rows = []

    for well in WELL_IDS:
        # Per-well healthy baseline
        base_oil = rng.uniform(260, 460)
        base_pressure = rng.uniform(1900, 2600)
        base_temp = rng.uniform(78, 95)
        base_vib = rng.uniform(1.0, 2.0)
        base_amps = rng.uniform(38, 50)
        base_water = rng.uniform(15, 40)
        base_gor = rng.uniform(900, 1300)
        base_choke = rng.uniform(45, 80)
        noise = 0.09 if well == "WELL-05" else 0.05

        episodes = EPISODES.get(well, [])

        for day in range(NUM_DAYS):
            s = _severity(day, episodes)
            jitter = lambda scale=noise: 1 + rng.uniform(-scale, scale)

            oil = base_oil * (1 - 0.72 * s) * jitter()
            pressure = base_pressure * (1 - 0.38 * s) * jitter(0.04)
            vibration = (base_vib + 6.5 * s ** 1.3) * jitter(0.12)
            amps = (base_amps + 75 * s ** 1.2) * jitter(0.06)
            temp = (base_temp + 22 * s) * jitter(0.03)
            water = min(95, base_water * (1 + 0.5 * s) * jitter())
            gor = base_gor * (1 + 0.25 * s) * jitter(0.06)
            gas = oil * gor / 1000
            choke = max(5, min(100, base_choke * (1 - 0.3 * s) * jitter(0.08)))

            # Failure label. Certain once severity reaches 85%; in the
            # grey zone above 55% the pump sometimes trips early, the
            # way real equipment does. This is what teaches the model
            # to give mid-range risk scores instead of 0% / 100%.
            if s >= 0.85:
                failed = 1
            elif s >= 0.55:
                failed = 1 if rng.random() < (s - 0.55) / 0.30 else 0
            else:
                failed = 0

            rows.append((
                well,
                (START_DATE + datetime.timedelta(days=day)).isoformat(),
                round(oil, 2), round(gas, 2), round(gor, 2), round(water, 2),
                round(pressure, 2), round(temp, 2), round(choke, 1),
                round(vibration, 2), round(amps, 2),
                failed,
            ))

    return pd.DataFrame(rows, columns=[
        'Well_ID', 'Date', 'Oil_Rate', 'Gas_Rate', 'GOR', 'Water_Cut',
        'Pressure', 'Temperature', 'Choke_Position', 'Vibration',
        'Motor_Current', 'Pump_Status'
    ])


if __name__ == "__main__":
    df = build_dataframe()
    df.to_csv(CSV_PATH, index=False)
    print(f"Wrote {len(df)} rows to {CSV_PATH}  "
          f"(failure days: {int(df['Pump_Status'].sum())})")