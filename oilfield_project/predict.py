import joblib
import pandas as pd
from data_loader import load_well_data
from config import MODEL_PATH, RISK_THRESHOLD

# Load model ONCE at module level
_model = joblib.load(MODEL_PATH)

FEATURES = ['Oil_Rate', 'Water_Cut', 'Pressure', 'Temperature']


def predict_failure_risk(well_id: str) -> float:
    """
    Return failure risk score 0.0–1.0
    for the most recent day of a well.
    """
    df = load_well_data(well_id)

    if df.empty:
        raise ValueError(f"No data for {well_id}")

    latest = df.iloc[[-1]]          # Last row = latest reading
    X = latest[FEATURES]

    risk_score = _model.predict_proba(X)[0, 1]
    return float(risk_score)


def get_risk_level(score: float) -> str:
    """Human-readable risk label."""
    if score >= RISK_THRESHOLD:
        return "🔴 CRITICAL"
    elif score >= 0.50:
        return "🟠 WARNING"
    else:
        return "🟢 NORMAL"


def check_all_wells() -> dict:
    """Score every well — used for auto-alerts."""
    from data_loader import get_well_ids
    results = {}
    for well in get_well_ids():
        score = predict_failure_risk(well)
        results[well] = {
            'score': score,
            'level': get_risk_level(score)
        }
    return results


# # ==============================
# # TERMINAL TEST
# # ==============================
# if __name__ == "__main__":
#     print("\n========================================")
#     print("   DIGITAL OILFIELD FAILURE PREDICTION")
#     print("========================================\n")

#     try:
#         results = check_all_wells()

#         for well, result in results.items():
#             print(f"Well: {well}")
#             print(f"Failure Risk: {result['score']:.2%}")
#             print(f"Risk Level: {result['level']}")
#             print("----------------------------------------")

#         print("\nPrediction completed successfully.")

#     except Exception as e:
#         print("\nERROR:")
#         print(e)

