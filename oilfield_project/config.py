import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'oilfield.db')
CSV_PATH = os.path.join(BASE_DIR, 'production_data.csv')


# ----------------------------------------------------------------
# .env loader (no extra package needed)
#
# Put secrets in a file named ".env" next to this config.py:
#
#     EMAIL_USER=bravooilfleet@gmail.com
#     EMAIL_PASS=xxxx xxxx xxxx xxxx
#
# Values from .env take priority over anything set with setx, so a
# stale Windows variable can never override the team account.
# ----------------------------------------------------------------
def _load_dotenv(path):
    values = {}
    if not os.path.isfile(path):
        return values

    with open(path, encoding='utf-8') as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]          # strip surrounding quotes
            values[key] = value
            os.environ[key] = value           # make it visible everywhere

    return values


_ENV = _load_dotenv(os.path.join(BASE_DIR, '.env'))


def _setting(name, default=''):
    """.env first, then the environment, then the default."""
    return _ENV.get(name) or os.environ.get(name) or default


# Fleet name shown in the dashboard header and on reports.
FLEET_NAME = 'BRAVO FLEET'


# --- ML Model ---
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'pump_failure_model.pkl')

# Input features. These MUST match the production_data column names.
# Pump_Status is the failure LABEL the model predicts, so it is
# deliberately NOT a feature.
FEATURE_COLUMNS = [
    "Oil_Rate",
    "Gas_Rate",
    "GOR",
    "Water_Cut",
    "Pressure",
    "Temperature",
    "Choke_Position",
    "Vibration",
    "Motor_Current",
]
TARGET_COLUMN = "Pump_Status"


# --- Alerts ---
# Everyone who receives the automatic high-risk alert emails.
TECH_EMAIL = [
    'abdulmaleekarg01@gmail.com',
    'enomfonakpanudo@gmail.com',
    'aniekemeoton46@gmail.com',
    'ogbchiazam@gmail.com',
    'agbochigozieanthony@gmail.com',
    'imranabellowakili@gmail.com',
    # add more addresses here
]

# Risk threshold as a FRACTION (0-1). The dashboard slider works in
# percent and converts at the boundary (RISK_THRESHOLD * 100).
RISK_THRESHOLD = 0.75

# Minimum seconds between two automatic alert emails for the SAME well.
ALERT_COOLDOWN_SECONDS = 15 * 60

# How often (ms) Auto-Monitor re-checks every well while switched on.
AUTO_MONITOR_INTERVAL_MS = 30 * 1000

# The high-risk alarm sounds until dismissed. Set a number of seconds to
# make it cut off on its own (0 = keep sounding until dismissed).
ALARM_MAX_SECONDS = 0

# Equipment operating limits used by the dashboard panels.
MOTOR_CURRENT_OVERLOAD_A = 70.0     # amps
VIBRATION_ANOMALY_MM_S = 3.5        # mm/s


# --- Wells & data generation ---
WELL_IDS = [f'WELL-0{i}' for i in range(1, 6)]
NUM_DAYS = 30


# --- Email ---
SENDER_EMAIL = _setting('EMAIL_USER', 'bravooilfleet@gmail.com')
EMAIL_PASS = _setting('EMAIL_PASS')          # Gmail App Password, from .env
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024      # 25 MB, Gmail's per-message limit
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5