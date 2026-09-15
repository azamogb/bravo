
import os



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'oilfield.db')


# --- ML Model ---
MODEL_PATH = 'models/pump_failure_model.pkl'
FEATURE_COLUMNS = ["Oil_Rate",
    "Water_Cut",
    "Pressure",
    "Temperature",
    "Gas Rate",
    "GOR",
    "Choke_position",
    "Vibration",
    "Motor_Current",
    "Pump_Status"]

# --- Alerts ---
TECH_EMAIL = 'enomfonakpanudo@gmail.com'   
RISK_THRESHOLD = 0.75

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

