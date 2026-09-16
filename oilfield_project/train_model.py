"""
Trains the pump-failure model and saves it to config.MODEL_PATH.

    python train_model.py

Reads every well's records through data_loader (so the database is the
single source of truth), trains a Random Forest to predict Pump_Status
(1 = failure) from the FEATURE_COLUMNS in config.py, prints how well it
does on a held-out test split, and pickles the model together with the
column list it expects so predict.py can validate its inputs.
"""

import os
import pickle
from datetime import datetime

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, roc_auc_score,
                             classification_report, confusion_matrix)
from sklearn.model_selection import train_test_split, cross_val_score

from config import MODEL_PATH, FEATURE_COLUMNS, TARGET_COLUMN
from data_loader import load_data


RANDOM_STATE = 42


def train():
    df = load_data()

    missing = [c for c in FEATURE_COLUMNS + [TARGET_COLUMN] if c not in df.columns]
    if missing:
        raise SystemExit(f"Data is missing required columns: {missing}")

    X = df[FEATURE_COLUMNS].astype(float)
    y = df[TARGET_COLUMN].astype(int)

    print(f"Training rows: {len(df)}  |  failures: {int(y.sum())} "
          f"({y.mean():.1%})  |  features: {len(FEATURE_COLUMNS)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, stratify=y, random_state=RANDOM_STATE
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=6,
        min_samples_leaf=2,
        class_weight="balanced",      # failures are the minority class
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )

    # Cross-validated score on the training portion gives a more honest
    # picture than a single split on a small dataset.
    cv_auc = cross_val_score(model, X_train, y_train, cv=5, scoring="roc_auc")
    print(f"5-fold CV ROC-AUC: {cv_auc.mean():.3f} (+/- {cv_auc.std():.3f})")

    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)

    print(f"\nHeld-out test ({len(X_test)} rows)")
    print(f"  accuracy : {accuracy_score(y_test, pred):.3f}")
    print(f"  ROC-AUC  : {roc_auc_score(y_test, proba):.3f}")
    print("  confusion matrix [[TN FP] [FN TP]]:")
    print("   ", confusion_matrix(y_test, pred).tolist())
    print()
    print(classification_report(y_test, pred, target_names=["normal", "failure"]))

    print("Feature importance:")
    order = np.argsort(model.feature_importances_)[::-1]
    for i in order:
        print(f"  {FEATURE_COLUMNS[i]:<16} {model.feature_importances_[i]:.3f}")

    # Refit on everything before saving so the deployed model has seen
    # all available data.
    model.fit(X, y)

    bundle = {
        "model": model,
        "feature_columns": list(FEATURE_COLUMNS),
        "target_column": TARGET_COLUMN,
        "trained_at": datetime.now().isoformat(timespec="seconds"),
        "training_rows": int(len(df)),
    }

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    with open(MODEL_PATH, "wb") as handle:
        pickle.dump(bundle, handle)

    print(f"\nSaved model to {MODEL_PATH}")


if __name__ == "__main__":
    train()