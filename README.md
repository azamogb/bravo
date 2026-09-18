# bravo
PYTHON project for Ncdmb/renaissance training 
# Digital Oilfield Monitoring & Predictive Maintenance System

A Python-based desktop application for monitoring simulated oilfield production data and predicting potential pump failures using Machine Learning.

The system combines **SQLite, Pandas, Scikit-learn, Tkinter, Matplotlib, and SMTP email alerts** to provide a simple SCADA-like monitoring and predictive maintenance solution.

## Features

* Generate synthetic production data for 5 oil wells over 30 days
* Store and retrieve production data using SQLite
* Visualize:

  * Oil Production
  * Pressure
  * Water Cut
* Predict pump failure risk using a Random Forest model
* Display risk levels based on the prediction score
* Automatically send an email alert when failure risk exceeds **75%**
* Generate Technical and Stakeholder reports
* Send reports to an email address directly from the application

## System Architecture

```text
Synthetic Data
      ↓
    SQLite
      ↓
   Pandas
      ↓
Random Forest ML Model
      ↓
 Failure Risk Score
      ↓
 Tkinter Dashboard
   ↙    ↓     ↘
Charts Reports Email Alerts
```

## Technologies Used

| Technology   | Purpose                      |
| ------------ | ---------------------------- |
| Python       | Core programming language    |
| Pandas       | Data processing and analysis |
| SQLite       | Local database               |
| Scikit-learn | Machine Learning             |
| Joblib       | Model saving/loading         |
| Tkinter      | Desktop GUI                  |
| Matplotlib   | Data visualization           |
| SMTP         | Email notifications          |

## Project Structure

```text
oilfield_project/
│
├── data/
│   └── oilfield.db
├── models/
│   └── pump_failure_model.pkl
├── reports/
│
├── generate_data.py
├── db_setup.py
├── data_loader.py
├── train_model.py
├── predict.py
├── charts.py
├── reports.py
├── emailer.py
├── app.py
├── config.py
└── README.md
```

## Installation

Clone the repository and install the required packages:

```bash
pip install pandas numpy scikit-learn joblib matplotlib
```

Tkinter and SQLite are included with most standard Python installations.

## How to Run

### 1. Generate the data

```bash
python generate_data.py
```

### 2. Set up the database

```bash
python db_setup.py
```

### 3. Train the Machine Learning model

```bash
python train_model.py
```

This creates:

```text
models/pump_failure_model.pkl
```

### 4. Start the application

```bash
python app.py
```

## Machine Learning

The system uses a **Random Forest Classifier** to predict pump failure risk.

### Features

* Oil Rate
* Water Cut
* Pressure
* Temperature

### Target

```text
Pump_Status
0 = Normal
1 = Failure
```

The model produces a probability between **0 and 1**, which is displayed by the application as a failure-risk percentage.

## Risk Levels

```text
Risk ≥ 75%  → CRITICAL
Risk ≥ 50%  → WARNING
Risk < 50%  → NORMAL
```

When the risk exceeds **75%**, the system automatically sends an alert to the configured technical team email.

## Reports

The application provides two report types:

**Technical Report**

* Mean
* Standard deviation
* Minimum/maximum values
* Failure days
* Average pressure

**Stakeholder Report**

* Total oil produced
* Operational days
* Overall field status

## Email Configuration

Email credentials should **not** be stored directly in the source code.

Set the email password as an environment variable:

### Windows

```bash
set EMAIL_PASS=your_app_password
```

### macOS/Linux

```bash
export EMAIL_PASS=your_app_password
```

For Gmail, an **App Password** should be used rather than a normal account password.

## Project Objective

The objective of this project is to demonstrate how Python and Machine Learning can be used to monitor oilfield production data, identify potential equipment failures, visualize operational conditions, and provide automated alerts for predictive maintenance.

## Team

**Team Bravo**

* Abdulmalik Alhassan
* Imrana Bello
* Aniekeme Oton
* Chiazam Ogamba
* Chigozie Agbo
* Enomfon Akpanudo

## Project Status

This project was developed as a **5-day sprint prototype** focused on demonstrating the core functionality of a digital oilfield monitoring and predictive maintenance system.


