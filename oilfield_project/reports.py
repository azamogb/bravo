# import pandas as pd

# from data_loader import load_well_data, load_all_data


# def technical_report(well_id: str) -> str:
#     """
#     Generates a technical report for engineers.

#     The report contains descriptive statistics for:
#     Oil Rate, Pressure, Water Cut and Temperature.

#     It also reports failure days and average pressure.
#     """

#     df = load_well_data(well_id)

#     if df.empty:
#         return f"No data available for {well_id}."

#     stats = df[
#         [
#             "Oil_Rate",
#             "Pressure",
#             "Water_Cut",
#             "Temperature"
#         ]
#     ].describe()

#     failures = int(
#         df["Pump_Status"].sum()
#     )

#     report = (
#         f"TECHNICAL REPORT — {well_id}\n"
#     )

#     report += "=" * 40 + "\n\n"

#     report += (
#         stats.to_string()
#         + "\n\n"
#     )

#     report += (
#         f"Failure days: {failures}/{len(df)}\n"
#     )

#     report += (
#         f"Avg pressure: "
#         f"{df['Pressure'].mean():.1f} psi"
#     )

#     return report


# def stakeholder_report(well_id: str) -> str:
#     """
#     Generates a high-level report for managers
#     and other non-technical stakeholders.
#     """

#     df = load_well_data(well_id)

#     if df.empty:
#         return f"No data available for {well_id}."

#     total_oil = df["Oil_Rate"].sum()

#     failures = int(
#         df["Pump_Status"].sum()
#     )

#     operational_days = len(df) - failures

#     status = (
#         "ATTENTION NEEDED"
#         if failures > 3
#         else "OPERATIONAL"
#     )

#     report = (
#         f"FIELD STATUS SUMMARY — {well_id}\n"
#     )

#     report += "=" * 40 + "\n\n"

#     report += (
#         f"Total oil produced: "
#         f"{total_oil:,.0f} bbl\n"
#     )

#     report += (
#         f"Days operational:   "
#         f"{operational_days}/{len(df)}\n"
#     )

#     report += (
#         f"Overall status:     "
#         f"{status}"
#     )

#     return report


# def save_report_to_file(text: str, path: str):
#     """
#     Saves a generated report to a text file.

#     The resulting .txt file can later be attached
#     by the email module.
#     """

#     with open(
#         path,
#         "w",
#         encoding="utf-8"
#     ) as file:
#         file.write(text)
"""
reports.py

Generates plain-text reports covering ALL wells at once.

- technical_report()    -> detailed per-well readings, technical tone,
                           returned as a formatted string
- stakeholder_report()  -> plain-language, executive-style summary,
                           returned as a formatted string
- save_report_to_file() -> saves a report string as a PDF file
"""

import os
from datetime import datetime

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Preformatted
from reportlab.lib.units import inch

from data_loader import load_well_data
from config import WELL_IDS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "reports")


def _get_latest_conditions():
    """Latest reading for every well in WELL_IDS, as one DataFrame."""
    rows = []
    for well_id in WELL_IDS:
        df = load_well_data(well_id)
        if df.empty:
            continue
        rows.append(df.sort_values("Date").iloc[-1])
    return pd.DataFrame(rows)


def technical_report():
    """
    Detailed, technical-tone report covering every well's latest
    sensor readings, formatted as an aligned table.
    """
    df = _get_latest_conditions()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append("=" * 72)
    lines.append("TECHNICAL DIAGNOSTICS REPORT".center(72))
    lines.append(f"Generated: {now}".center(72))
    lines.append("=" * 72)
    lines.append("")

    header = (
        f"{'Well':<10}{'Oil Rate':>10}{'Water Cut':>11}"
        f"{'Pressure':>10}{'Temp':>8}{'Status':>13}"
    )
    lines.append(header)
    lines.append("-" * 72)

    for _, row in df.iterrows():
        status = "FAILURE" if row["Pump_Status"] == 1 else "NORMAL"
        lines.append(
            f"{row['Well_ID']:<10}"
            f"{row['Oil_Rate']:>10.1f}"
            f"{row['Water_Cut']:>11.1f}"
            f"{row['Pressure']:>10.1f}"
            f"{row['Temperature']:>8.1f}"
            f"{status:>13}"
        )

    lines.append("-" * 72)
    total = len(df)
    flagged = int((df["Pump_Status"] == 1).sum())
    lines.append(f"Total wells monitored: {total}    Flagged for failure: {flagged}")
    lines.append("=" * 72)

    return "\n".join(lines)


def stakeholder_report():
    """
    Plain-language, executive-style summary of field conditions,
    written in the tone of a real report sent to non-technical
    stakeholders.
    """
    df = _get_latest_conditions()
    now = datetime.now().strftime("%B %d, %Y")

    total = len(df)
    flagged_df = df[df["Pump_Status"] == 1]
    flagged_count = len(flagged_df)
    healthy_count = total - flagged_count
    avg_oil_rate = df["Oil_Rate"].mean()
    total_oil_rate = df["Oil_Rate"].sum()

    lines = []
    lines.append("WELL FIELD PERFORMANCE SUMMARY")
    lines.append(now)
    lines.append("")
    lines.append("Overview")
    lines.append("-" * 40)
    lines.append(
        f"As of today, {healthy_count} of {total} monitored wells are "
        f"producing within normal parameters. Combined field output is "
        f"approximately {total_oil_rate:,.0f} barrels per day, averaging "
        f"{avg_oil_rate:,.0f} bbl/day per well."
    )
    lines.append("")

    lines.append("Wells Requiring Attention")
    lines.append("-" * 40)
    if flagged_count > 0:
        lines.append(
            f"{flagged_count} well(s) are currently showing signs of "
            f"reduced performance and may be impacting total output:"
        )
        lines.append("")
        for _, row in flagged_df.iterrows():
            lines.append(
                f"  - {row['Well_ID']}: producing {row['Oil_Rate']:.0f} bbl/day "
                f"(below normal range); pressure reading indicates a "
                f"possible equipment issue."
            )
    else:
        lines.append("No wells are currently flagged. All units are performing normally.")
    lines.append("")

    lines.append("Recommended Next Steps")
    lines.append("-" * 40)
    if flagged_count > 0:
        lines.append(
            "We recommend prioritizing field inspection of the well(s) "
            "listed above to prevent further production loss. A follow-up "
            "update will be provided once corrective action is taken."
        )
    else:
        lines.append(
            "No corrective action is required at this time. Routine "
            "monitoring will continue as scheduled."
        )
    lines.append("")
    lines.append("This report was generated automatically from live field data.")

    return "\n".join(lines)


def save_report_to_file(report, filename):
    """
    Saves a report string as a PDF file inside the reports/ folder,
    preserving its exact spacing/alignment (important for the
    technical report's table layout).

    `filename` may be passed with or without an extension -- it will
    always be saved with a .pdf extension.

    Returns the full filepath of the saved PDF.
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    base_name = os.path.splitext(filename)[0]
    filepath = os.path.join(REPORTS_DIR, f"{base_name}.pdf")

    styles = getSampleStyleSheet()
    mono_style = ParagraphStyle(
        "ReportMono",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=9,
        leading=12,
    )

    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    story = [Preformatted(report, mono_style)]
    doc.build(story)

    return filepath