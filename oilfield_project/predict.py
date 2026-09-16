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


if __name__ == "__main__":
    wells = sys.argv[1:] or list_wells()
    info = model_info()
    print(f"Model trained {info['trained_at']} on {info['training_rows']} rows\n")
    for well in wells:
        risk = predict_well(well)
        flag = "HIGH RISK" if risk >= 0.75 else "WARNING" if risk >= 0.5 else "normal"
        print(f"{well}: {risk:6.1%}  {flag}")