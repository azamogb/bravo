"""
Failure-risk prediction for the dashboard.

    predict_risk(well_data)   -> float 0-1, failure probability for the
                                 given rows (a DataFrame containing the
                                 FEATURE_COLUMNS). If several rows are
                                 passed, the highest probability is
                                 returned, so scoring the last few days
                                 flags a well that tripped recently.
    predict_well(well_id, days=3) -> float 0-1, convenience wrapper
    predict_all_wells(days=3)     -> {well_id: risk}
    predict_failure(well)         -> dict: risk (0-100), mode, eta_days,
                                     confidence -- used by the dashboard's
                                     ML Failure Forecast panel
    get_well_risk(well)           -> risk 0-100 for a well (cached)

Command line:
    python predict.py             risk for every well
    python predict.py WELL-03     risk for one well

The model is loaded once from config.MODEL_PATH on first use. Run
train_model.py first to create it.
"""

import os
import sys
import pickle

import pandas as pd

from config import MODEL_PATH, FEATURE_COLUMNS
from data_loader import load_well, list_wells


_bundle = None


def _load_bundle():
    global _bundle

    if _bundle is None:
        if not os.path.isfile(MODEL_PATH):
            raise FileNotFoundError(
                f"No trained model at {MODEL_PATH}. Run train_model.py first."
            )
        with open(MODEL_PATH, "rb") as handle:
            _bundle = pickle.load(handle)

    return _bundle


def model_info():
    """Returns training metadata stored with the model (for status text)."""
    bundle = _load_bundle()
    return {k: v for k, v in bundle.items() if k != "model"}


def predict_risk(well_data):
    """
    well_data: DataFrame (one or more rows) with the FEATURE_COLUMNS,
    or a dict / Series for a single record.
    Returns the failure probability as a float in [0, 1].
    """
    bundle = _load_bundle()
    model = bundle["model"]
    columns = bundle["feature_columns"]

    if isinstance(well_data, dict):
        well_data = pd.DataFrame([well_data])
    elif isinstance(well_data, pd.Series):
        well_data = well_data.to_frame().T

    missing = [c for c in columns if c not in well_data.columns]
    if missing:
        raise ValueError(f"well_data is missing feature columns: {missing}")

    if well_data.empty:
        return 0.0

    X = well_data[columns].astype(float)
    proba = model.predict_proba(X)[:, 1]
    return float(proba.max())


def predict_well(well_id, days=3):
    return predict_risk(load_well(well_id, days))


def predict_all_wells(days=3):
    return {well: predict_well(well, days) for well in list_wells()}


# ----------------------------------------------------------------
# Dashboard failure forecast (extracted from app.py)
#
# ML_ACTIVE previously checked both that `from predict import
# predict_risk` succeeded AND that the model file existed. Now that
# predict_failure lives in this same file, predict_risk is always
# available locally -- so the only real-world condition left to check
# is whether a trained model file actually exists.
# ----------------------------------------------------------------
ML_ACTIVE = os.path.isfile(MODEL_PATH)

RISK_WINDOW_DAYS = 3

well_risk_cache = {}          # well -> last computed risk (0-100)


def _clip01(x):
    return float(max(0.0, min(1.0, x)))


def predict_failure(well):
    """
    Returns a dict describing the failure forecast for a well:
        risk        0-100
        mode        predicted failure mode text
        eta_days    estimated days to failure (None when NORMAL)
        confidence  0-100

    Uses predict_risk() when a trained model is available. The
    failure-mode / ETA logic is rule-based until the ML module
    provides those directly.
    """

    df = load_well(well)

    # Score the worst reading in the recent window so a well that
    # tripped two days ago is still flagged, not just one whose very
    # last record happens to look bad.
    recent_rows = df.tail(RISK_WINDOW_DAYS)
    vib = float(recent_rows["Vibration"].max())
    amps = float(recent_rows["Motor_Current"].max())
    pressure = float(recent_rows["Pressure"].min())
    temp = float(recent_rows["Temperature"].max())

    vib_score = _clip01((vib - 1.0) / 6.0)
    amps_score = _clip01((amps - 40.0) / 80.0)
    press_score = _clip01((2000.0 - pressure) / 1200.0)
    temp_score = _clip01((temp - 95.0) / 25.0)

    risk = None
    if ML_ACTIVE:
        try:
            # predict_risk returns the highest failure probability across
            # the rows given, so pass the same recent window scored above.
            raw = float(predict_risk(recent_rows[FEATURE_COLUMNS]))
            risk = raw * 100.0 if raw <= 1.0 else raw
        except Exception as error:
            print(f"predict.py failed for {well}, using rule-based risk: {error}")

    if risk is None:
        risk = 100.0 * (0.40 * vib_score + 0.35 * amps_score
                        + 0.20 * press_score + 0.05 * temp_score)

    risk = float(max(0.0, min(100.0, risk)))

    # Rule-based failure mode from the dominant driver
    if risk < 50:
        mode = "NO FAILURE PREDICTED"
    else:
        drivers = {
            "ESP MOTOR SEIZE": amps_score * 0.6 + vib_score * 0.4,
            "PUMP BEARING WEAR": vib_score,
            "GAS LOCK / PRESSURE DEPLETION": press_score,
            "MOTOR OVERHEAT": temp_score * 0.7 + amps_score * 0.3,
        }
        mode = max(drivers, key=drivers.get)

    eta_days = None if risk < 50 else max(1, int(round(60 * (1 - risk / 100))))

    # Recent trend agreement makes the estimate more "confident"
    recent = df["Vibration"].tail(5).values
    trend_agree = 1.0 if len(recent) < 2 or (recent[-1] >= recent[0]) == (risk >= 50) else 0.6
    confidence = round(70 + 25 * trend_agree * abs(risk - 50) / 50, 1)

    return {"risk": risk, "mode": mode, "eta_days": eta_days,
            "confidence": confidence}


def get_well_risk(well):
    """Risk 0-100 for the asset list / auto-monitor (cached)."""
    if well not in well_risk_cache:
        well_risk_cache[well] = predict_failure(well)["risk"]
    return well_risk_cache[well]


if __name__ == "__main__":
    wells = sys.argv[1:] or list_wells()
    info = model_info()
    print(f"Model trained {info['trained_at']} on {info['training_rows']} rows\n")
    for well in wells:
        risk = predict_well(well)
        flag = "HIGH RISK" if risk >= 0.75 else "WARNING" if risk >= 0.5 else "normal"
        print(f"{well}: {risk:6.1%}  {flag}")