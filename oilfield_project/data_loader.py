import pandas as pd
import joblib

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

from data_loader import load_data


# Features the model will learn from
FEATURES = [
    "Oil_Rate",
    "Water_Cut",
    "Pressure",
    "Temperature",
    "Gas Rate",
    "GOR",
    "Choke_position",
    "Vibration",
    "Motor_Current",
    "Pump_Status"
]

# Target we want the model to predict
TARGET = "Pump_Status"


def train_model():

    # Load data from SQLite
    df = load_data()

    print(f"Total records loaded: {len(df)}")

    # Separate input features and target
    X = df[FEATURES]
    y = df[TARGET]

    # Split data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y
    )

    print(f"Training records: {len(X_train)}")
    print(f"Testing records: {len(X_test)}")

    # Create Random Forest model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=5,
        random_state=42
    )

    # Train the model
    model.fit(X_train, y_train)

    print("\nModel training completed!")

    # Make predictions
    predictions = model.predict(X_test)

    # Calculate probability of failure
    probabilities = model.predict_proba(X_test)[:, 1]

    # Evaluate the model
    print("\nClassification Report:")
    print(classification_report(y_test, predictions))

    print("ROC-AUC Score:")
    print(roc_auc_score(y_test, probabilities))

    # Save the trained model
    joblib.dump(model, "models/pump_failure_model.pkl")

    print("\nModel saved successfully!")
    print("Location: models/pump_failure_model.pkl")


if __name__ == "__main__":
    train_model()