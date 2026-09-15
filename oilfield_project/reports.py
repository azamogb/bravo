import pandas as pd

from data_loader import load_well_data, load_all_data


def technical_report(well_id: str) -> str:
    """
    Generates a technical report for engineers.

    The report contains descriptive statistics for:
    Oil Rate, Pressure, Water Cut and Temperature.

    It also reports failure days and average pressure.
    """

    df = load_well_data(well_id)

    if df.empty:
        return f"No data available for {well_id}."

    stats = df[
        [
            "Oil_Rate",
            "Pressure",
            "Water_Cut",
            "Temperature"
        ]
    ].describe()

    failures = int(
        df["Pump_Status"].sum()
    )

    report = (
        f"TECHNICAL REPORT — {well_id}\n"
    )

    report += "=" * 40 + "\n\n"

    report += (
        stats.to_string()
        + "\n\n"
    )

    report += (
        f"Failure days: {failures}/{len(df)}\n"
    )

    report += (
        f"Avg pressure: "
        f"{df['Pressure'].mean():.1f} psi"
    )

    return report


def stakeholder_report(well_id: str) -> str:
    """
    Generates a high-level report for managers
    and other non-technical stakeholders.
    """

    df = load_well_data(well_id)

    if df.empty:
        return f"No data available for {well_id}."

    total_oil = df["Oil_Rate"].sum()

    failures = int(
        df["Pump_Status"].sum()
    )

    operational_days = len(df) - failures

    status = (
        "ATTENTION NEEDED"
        if failures > 3
        else "OPERATIONAL"
    )

    report = (
        f"FIELD STATUS SUMMARY — {well_id}\n"
    )

    report += "=" * 40 + "\n\n"

    report += (
        f"Total oil produced: "
        f"{total_oil:,.0f} bbl\n"
    )

    report += (
        f"Days operational:   "
        f"{operational_days}/{len(df)}\n"
    )

    report += (
        f"Overall status:     "
        f"{status}"
    )

    return report


def save_report_to_file(text: str, path: str):
    """
    Saves a generated report to a text file.

    The resulting .txt file can later be attached
    by the email module.
    """

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:
        file.write(text)