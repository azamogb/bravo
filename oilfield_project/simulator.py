"""
Shared "physics" for the fake wells.

One function turns (well baseline, severity 0..1, timestamp) into a
sensor row. generate_data.py uses it to build months of history and
live_feed.py uses it to emit new rows every minute, so the model
trained on history sees the same behaviour in the live stream.
"""

import random

COLUMNS = [
    'Well_ID', 'Date', 'Oil_Rate', 'Gas_Rate', 'GOR', 'Water_Cut',
    'Pressure', 'Temperature', 'Choke_Position', 'Vibration',
    'Motor_Current', 'Pump_Status'
]

SEED = 42


def well_rng(well, tag="baseline"):
    """Deterministic RNG per well, so history and live feed agree on a
    well's healthy baseline no matter which script asks for it."""
    return random.Random(f"{SEED}:{tag}:{well}")


def make_baseline(well):
    rng = well_rng(well)
    return {
        "oil":      rng.uniform(260, 460),
        "pressure": rng.uniform(1900, 2600),
        "temp":     rng.uniform(78, 95),
        "vib":      rng.uniform(1.0, 2.0),
        "amps":     rng.uniform(38, 50),
        "water":    rng.uniform(15, 40),
        "gor":      rng.uniform(900, 1300),
        "choke":    rng.uniform(45, 80),
        "noise":    0.09 if well == "WELL-05" else 0.05,
    }


def sample_row(well, timestamp, s, base, rng):
    """s = severity: 0 healthy ... 1 fully failed."""
    noise = base["noise"]
    jitter = lambda scale=noise: 1 + rng.uniform(-scale, scale)

    oil = base["oil"] * (1 - 0.72 * s) * jitter()
    pressure = base["pressure"] * (1 - 0.38 * s) * jitter(0.04)
    vibration = (base["vib"] + 6.5 * s ** 1.3) * jitter(0.12)
    amps = (base["amps"] + 75 * s ** 1.2) * jitter(0.06)
    temp = (base["temp"] + 22 * s) * jitter(0.03)
    water = min(95, base["water"] * (1 + 0.5 * s) * jitter())
    gor = base["gor"] * (1 + 0.25 * s) * jitter(0.06)
    gas = oil * gor / 1000
    choke = max(5, min(100, base["choke"] * (1 - 0.3 * s) * jitter(0.08)))

    # Certain failure at >= 85% severity; in the 55-85% grey zone the
    # pump sometimes trips early. This gives the model mid-range risk.
    if s >= 0.85:
        failed = 1
    elif s >= 0.55:
        failed = 1 if rng.random() < (s - 0.55) / 0.30 else 0
    else:
        failed = 0

    return (
        well,
        timestamp.isoformat(timespec="minutes"),
        round(oil, 2), round(gas, 2), round(gor, 2), round(water, 2),
        round(pressure, 2), round(temp, 2), round(choke, 1),
        round(vibration, 2), round(amps, 2),
        failed,
    )