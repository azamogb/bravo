import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from data_loader import load_all_data
from config import MODEL_PATH


# 1. Load
df = load_all_data()

# 2. Features (X) and target (y)
feature_cols = ['Oil_Rate', 'Water_Cut', 'Pressure', 'Temperature',]
X = df[feature_cols]
y = df['Pump_Status']

# 3. Train/test split (80/20)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 4. Train
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=5,
    random_state=42
)
model.fit(X_train, y_train)

# 5. Evaluate
y_prob = model.predict_proba(X_test)[:, 1]
print(classification_report(y_test, model.predict(X_test)))
print(f"AUC: {roc_auc_score(y_test, y_prob):.3f}")

# 6. Save
joblib.dump(model, MODEL_PATH)
print(f"Model saved to {MODEL_PATH}")