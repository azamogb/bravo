"""
Live data feed: emits one new sensor row per well every minute and
writes it straight into the SQLite database, like a real telemetry
stream. Run it in its own terminal alongside app.py:

    python live_feed.py                 # 1 row/well/minute, forever
    python live_feed.py --interval 5    # demo mode: a new "minute" every 5s
    python live_feed.py --ticks 30      # stop after 30 ticks

Each well is a small state machine: healthy -> (random) degrading ->
failed -> repaired -> healthy. The starting state is taken from the
end of the history in generate_data.py, so a well that is failed in
history is still failed when the feed starts.

Timestamps continue from the last row in the DB, one minute per tick,
so nothing ever collides with history and re-running is safe.
"""

import argparse
import datetime
import random
import sqlite3
import time

from config import DB_PATH, WELL_IDS, NUM_DAYS, LIVE_INTERVAL_SECONDS
from simulator import COLUMNS, make_baseline, sample_row, well_rng
from generate_data import EPISODES, severity, history_end

# How often a healthy well starts degrading (per tick). 1/300 with
# 1-minute ticks = roughly one new episode per well every 5 hours.
EPISODE_START_PROB = 1 / 300
RAMP_TICKS = (40, 150)     # minutes for severity to climb 0 -> 1
FAILED_TICKS = (15, 40)    # minutes the pump stays failed before repair

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS production_data (
    Well_ID TEXT NOT NULL, Date TEXT NOT NULL,
    Oil_Rate REAL, Gas_Rate REAL, GOR REAL, Water_Cut REAL,
    Pressure REAL, Temperature REAL, Choke_Position REAL,
    Vibration REAL, Motor_Current REAL, Pump_Status INTEGER,
    PRIMARY KEY (Well_ID, Date)
)"""


class WellState:
    def __init__(self, well):
        self.well = well
        self.base = make_baseline(well)
        self.rng = well_rng(well, f"live-{time.time():.0f}")  # fresh each run
        s0 = severity(NUM_DAYS - 1e-6, EPISODES.get(well, []))
        if s0 >= 1.0:
            self.mode, self.severity = "failed", 1.0
            self.ticks_left = self.rng.randint(*FAILED_TICKS)
        elif s0 > 0:
            self.mode, self.severity = "degrading", s0
            self.ramp_step = 1 / self.rng.randint(*RAMP_TICKS)
        else:
            self.mode, self.severity = "healthy", 0.0

    def step(self):
        if self.mode == "healthy":
            if self.rng.random() < EPISODE_START_PROB:
                self.mode = "degrading"
                self.ramp_step = 1 / self.rng.randint(*RAMP_TICKS)
        elif self.mode == "degrading":
            self.severity = min(1.0, self.severity + self.ramp_step)
            if self.severity >= 1.0:
                self.mode = "failed"
                self.ticks_left = self.rng.randint(*FAILED_TICKS)
        elif self.mode == "failed":
            self.ticks_left -= 1
            if self.ticks_left <= 0:
                self.mode, self.severity = "healthy", 0.0   # repaired
        return self.severity


def next_timestamp(conn):
    """One minute after the newest row in the DB (or after history end)."""
    row = conn.execute("SELECT MAX(Date) FROM production_data").fetchone()
    last = datetime.datetime.fromisoformat(row[0]) if row and row[0] else history_end()
    return max(last, history_end()) + datetime.timedelta(minutes=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=float, default=LIVE_INTERVAL_SECONDS,
                        help="real seconds between ticks (each tick = 1 simulated minute)")
    parser.add_argument("--ticks", type=int, default=0, help="stop after N ticks (0 = forever)")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.execute(CREATE_SQL)
    conn.commit()

    wells = [WellState(w) for w in WELL_IDS]
    sim_time = next_timestamp(conn)
    placeholders = ",".join("?" * len(COLUMNS))
    tick = 0

    print(f"live_feed: streaming to {DB_PATH} from {sim_time} "
          f"(every {args.interval:g}s). Ctrl+C to stop.")
    try:
        while not args.ticks or tick < args.ticks:
            rows = [sample_row(w.well, sim_time, w.step(), w.base, w.rng) for w in wells]
            conn.executemany(
                f"INSERT OR REPLACE INTO production_data VALUES ({placeholders})", rows)
            conn.commit()

            status = "  ".join(f"{w.well[-2:]}:{w.mode[:4]}({w.severity:.0%})" for w in wells)
            print(f"{sim_time:%Y-%m-%d %H:%M}  {status}")

            sim_time += datetime.timedelta(minutes=1)
            tick += 1
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nlive_feed: stopped.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()