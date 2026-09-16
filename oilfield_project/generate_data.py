import os
import random
import datetime
import pandas as pd

from config import CSV_PATH, WELL_IDS, NUM_DAYS

random.seed(42)

start_date = datetime.date(2026, 1, 4)
rows = []

for well in WELL_IDS:
    for day in range(NUM_DAYS):
        is_failure = random.random() < 0.15
        pressure = random.uniform(1200, 2800)

        if is_failure:
            pressure *= 0.6
            oil_rate = random.uniform(50, 120)
            vibration = random.uniform(4.0, 9.0)
            motor_current = random.uniform(80, 140)
        else:
            oil_rate = random.uniform(200, 500)
            vibration = random.uniform(0.5, 3.0)
            motor_current = random.uniform(30, 60)

        gas_rate = oil_rate * random.uniform(0.8, 1.5)
        gor = round((gas_rate * 1000) / oil_rate, 2) if oil_rate > 0 else 0
        choke_position = round(random.uniform(20, 100), 1)

        rows.append((
            well,
            (start_date + datetime.timedelta(days=day)).isoformat(),
            round(oil_rate, 2),
            round(gas_rate, 2),
            gor,
            round(random.uniform(5, 60), 2),
            round(pressure, 2),
            round(random.uniform(60, 120), 2),
            choke_position,
            round(vibration, 2),
            round(motor_current, 2),
            1 if is_failure else 0
        ))

df = pd.DataFrame(rows, columns=[
    'Well_ID', 'Date', 'Oil_Rate', 'Gas_Rate', 'GOR', 'Water_Cut',
    'Pressure', 'Temperature', 'Choke_Position', 'Vibration',
    'Motor_Current', 'Pump_Status'
])

# Always written next to the project files, regardless of the
# directory the script is launched from (db_setup.py reads it from
# the same place).
df.to_csv(CSV_PATH, index=False)
print(f"Wrote {len(df)} rows to {CSV_PATH}")