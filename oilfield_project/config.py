import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'oilfield.db')
CSV_PATH = os.path.join(BASE_DIR, 'production_data.csv')

# Fleet name shown in the dashboard header.
FLEET_NAME = 'BRAVO FLEET'


# --- ML Model ---
# Built from BASE_DIR so the app works no matter which directory it is
# launched from (previously a relative path that broke outside the
# project folder).
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'pump_failure_model.pkl')

# Input features for the model. These MUST match the column names in
# the production_data table exactly (Gas_Rate, Choke_Position -- both
# were mis-spelled before). Pump_Status is the failure LABEL that the
# model predicts, so it is deliberately NOT in this list: including it
# would let the model read the answer it is supposed to predict.
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
TECH_EMAIL = 'enomfonakpanudo@gmail.com'

# Risk threshold as a FRACTION (0-1). The dashboard slider works in
# percent and converts at the boundary (RISK_THRESHOLD * 100).
RISK_THRESHOLD = 0.75

# Minimum time (seconds) between two automatic alert emails for the
# SAME well, so a well sitting above the threshold doesn't spam the
# inbox every time diagnostics run. 15 minutes by default.
ALERT_COOLDOWN_SECONDS = 15 * 60

# How often (milliseconds) the optional "Auto-Monitor" mode re-checks
# every well's risk while it's switched on.
AUTO_MONITOR_INTERVAL_MS = 30 * 1000

# The high-risk alarm sounds continuously until the banner is dismissed
# or the well clears. Set a number of seconds here to have it cut off
# on its own as a safety net (0 = never, keep sounding until dismissed).
ALARM_MAX_SECONDS = 0

# Equipment operating limits used by the dashboard panels.
MOTOR_CURRENT_OVERLOAD_A = 70.0     # amps -- above this the ESP is overloaded
VIBRATION_ANOMALY_MM_S = 3.5        # mm/s -- above this the FFT flags an anomaly


# --- Wells & data generation ---
WELL_IDS = [f'WELL-0{i}' for i in range(1, 6)]
NUM_DAYS = 30


# --- Email ---
SENDER_EMAIL = os.environ.get('EMAIL_USER', 'enomfonakpanudo@gmail.com')
EMAIL_PASS = os.environ.get('EMAIL_PASS')
SMTP_HOST = 'smtp.gmail.com'
SMTP_PORT = 587
MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024   # 25MB, Gmail's per-message limit
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5