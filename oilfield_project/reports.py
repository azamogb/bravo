"""
Report generation for the dashboard.

    technical_report(well_id, days=30)   -> Report
    stakeholder_report(days=30)          -> Report

Each returns a Report with:
    title      report heading
    text       the full report as plain text (shown in the app / email body)
    txt_path   saved .txt file
    pdf_path   saved .pdf file (same content plus a chart)

Files are written to reports/ next to the project files.

Technical report (per well): mean, maximum and standard deviation of
every metric over the period, plus the current ML failure risk.

Stakeholder report (whole field): total oil and gas produced, oil per
well, and an overall field status derived from each well's risk.
"""

import os
from dataclasses import dataclass
from datetime import datetime

import pandas as pd
import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_pdf import PdfPages

from config import BASE_DIR, RISK_THRESHOLD, FLEET_NAME
from data_loader import load_well, list_wells

try:
    from predict import predict_well
except Exception:                     # predict.py missing or model not trained
    predict_well = None


REPORTS_DIR = os.path.join(BASE_DIR, "reports")

METRICS = [
    ("Oil_Rate", "Oil Rate", "bbl/day"),
    ("Gas_Rate", "Gas Rate", "Mscf/day"),
    ("GOR", "GOR", "scf/stb"),
    ("Water_Cut", "Water Cut", "%"),
    ("Pressure", "Pressure", "psi"),
    ("Temperature", "Temperature", "\u00b0F"),
    ("Choke_Position", "Choke Position", "%"),
    ("Vibration", "Vibration", "mm/s"),
    ("Motor_Current", "Motor Current", "A"),
]


@dataclass
class Report:
    title: str
    text: str
    txt_path: str
    pdf_path: str


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------
def _well_risk(well_id, df):
    """Failure risk 0-1: ML model when available, else latest Pump_Status."""
    if predict_well is not None:
        try:
            return float(predict_well(well_id))
        except Exception as error:
            print(f"reports: predict failed for {well_id}: {error}")
    return float(df["Pump_Status"].tail(3).max())


def _risk_label(risk):
    if risk >= RISK_THRESHOLD:
        return "HIGH RISK"
    if risk >= 0.5:
        return "WARNING"
    return "NORMAL"


def _timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _file_stamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _write_txt(path, text):
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _write_pdf(path, title, text, chart_builder):
    """
    One page of monospaced text (the report itself) followed by one
    page with a chart drawn by chart_builder(ax).
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    with PdfPages(path) as pdf:
        lines = text.splitlines()
        per_page = 52
        for start in range(0, len(lines), per_page):
            figure = Figure(figsize=(8.27, 11.69))          # A4 portrait
            figure.text(0.07, 0.95, title, fontsize=14, fontweight="bold",
                        va="top")
            figure.text(0.07, 0.92, "\n".join(lines[start:start + per_page]),
                        fontsize=8.2, family="monospace", va="top")
            pdf.savefig(figure)

        figure = Figure(figsize=(8.27, 11.69))
        ax = figure.add_axes([0.12, 0.55, 0.8, 0.35])
        chart_builder(ax)
        pdf.savefig(figure)


# ----------------------------------------------------------------
# Technical report
# ----------------------------------------------------------------
def technical_report(well_id, days=30):
    df = load_well(well_id, days)
    if df.empty:
        raise ValueError(f"No data found for {well_id}.")

    risk = _well_risk(well_id, df)
    status = _risk_label(risk)
    period = f"{df['Date'].iloc[0]:%d %b %Y} to {df['Date'].iloc[-1]:%d %b %Y}"

    lines = [
        f"TECHNICAL REPORT - {well_id}",
        f"{FLEET_NAME}  |  Digital Oilfield Monitor",
        f"Generated: {_timestamp()}",
        f"Period: {period} ({len(df)} daily records)",
        "",
        f"Current failure risk: {risk:.0%}  [{status}]",
        f"Recorded failure days in period: {int(df['Pump_Status'].sum())}",
        "",
        f"{'Metric':<16}{'Unit':<10}{'Mean':>12}{'Max':>12}{'Std Dev':>12}",
        "-" * 62,
    ]

    for column, label, unit in METRICS:
        series = df[column].astype(float)
        lines.append(
            f"{label:<16}{unit:<10}{series.mean():>12.2f}"
            f"{series.max():>12.2f}{series.std(ddof=0):>12.2f}"
        )

    latest = df.iloc[-1]
    lines += [
        "",
        "Latest readings:",
    ]
    for column, label, unit in METRICS:
        lines.append(f"  {label:<16}{float(latest[column]):>10.2f} {unit}")
    lines.append(f"  {'Pump status':<16}{'FAILED' if int(latest['Pump_Status']) else 'RUNNING':>10}")

    text = "\n".join(lines)
    stamp = _file_stamp()
    txt_path = os.path.join(REPORTS_DIR, f"technical_{well_id}_{stamp}.txt")
    pdf_path = os.path.join(REPORTS_DIR, f"technical_{well_id}_{stamp}.pdf")

    def chart(ax):
        ax.plot(df["Date"], df["Vibration"], marker="o", markersize=3,
                label="Vibration (mm/s)")
        ax2 = ax.twinx()
        ax2.plot(df["Date"], df["Motor_Current"], color="tab:red",
                 marker="s", markersize=3, label="Motor current (A)")
        ax.set_title(f"{well_id} - vibration and motor current, last {len(df)} days")
        ax.set_ylabel("Vibration (mm/s)")
        ax2.set_ylabel("Motor current (A)")
        ax.grid(alpha=0.3)
        handles = ax.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
        ax.legend(handles=handles, loc="upper left", fontsize=8)
        for label in ax.get_xticklabels():
            label.set_rotation(30)

    _write_txt(txt_path, text)
    _write_pdf(pdf_path, f"Technical Report - {well_id}", text, chart)

    return Report(f"Technical Report - {well_id}", text, txt_path, pdf_path)


# ----------------------------------------------------------------
# Stakeholder report
# ----------------------------------------------------------------
def stakeholder_report(days=30):
    wells = list_wells()
    frames = {well: load_well(well, days) for well in wells}

    per_well = []
    for well, df in frames.items():
        risk = _well_risk(well, df)
        per_well.append({
            "well": well,
            "oil": float(df["Oil_Rate"].sum()),
            "gas": float(df["Gas_Rate"].sum()),
            "risk": risk,
            "status": _risk_label(risk),
            "failure_days": int(df["Pump_Status"].sum()),
        })

    total_oil = sum(row["oil"] for row in per_well)
    total_gas = sum(row["gas"] for row in per_well)
    high = [row["well"] for row in per_well if row["status"] == "HIGH RISK"]
    warn = [row["well"] for row in per_well if row["status"] == "WARNING"]

    if high:
        field_status = "CRITICAL - immediate attention required"
    elif warn:
        field_status = "ATTENTION - wells under watch"
    else:
        field_status = "STABLE - all wells operating normally"

    any_df = next(iter(frames.values()))
    period = f"{any_df['Date'].iloc[0]:%d %b %Y} to {any_df['Date'].iloc[-1]:%d %b %Y}"

    lines = [
        "STAKEHOLDER REPORT - FIELD SUMMARY",
        f"{FLEET_NAME}  |  Digital Oilfield Monitor",
        f"Generated: {_timestamp()}",
        f"Period: {period} ({days} days)",
        "",
        f"FIELD STATUS: {field_status}",
        "",
        f"Total oil produced : {total_oil:,.0f} bbl",
        f"Total gas produced : {total_gas:,.0f} Mscf",
        f"Average daily oil  : {total_oil / days:,.0f} bbl/day",
        f"Wells monitored    : {len(wells)}",
        f"High-risk wells    : {', '.join(high) if high else 'none'}",
        f"Wells under watch  : {', '.join(warn) if warn else 'none'}",
        "",
        f"{'Well':<10}{'Oil (bbl)':>14}{'Gas (Mscf)':>14}{'Risk':>8}  Status",
        "-" * 62,
    ]
    for row in per_well:
        lines.append(
            f"{row['well']:<10}{row['oil']:>14,.0f}{row['gas']:>14,.0f}"
            f"{row['risk']:>8.0%}  {row['status']}"
        )

    text = "\n".join(lines)
    stamp = _file_stamp()
    txt_path = os.path.join(REPORTS_DIR, f"stakeholder_{stamp}.txt")
    pdf_path = os.path.join(REPORTS_DIR, f"stakeholder_{stamp}.pdf")

    def chart(ax):
        colours = ["tab:red" if r["status"] == "HIGH RISK"
                   else "tab:orange" if r["status"] == "WARNING"
                   else "tab:green" for r in per_well]
        ax.bar([r["well"] for r in per_well], [r["oil"] for r in per_well],
               color=colours)
        ax.set_title(f"Oil produced per well, last {days} days (colour = risk status)")
        ax.set_ylabel("bbl")
        ax.grid(axis="y", alpha=0.3)

    _write_txt(txt_path, text)
    _write_pdf(pdf_path, "Stakeholder Report - Field Summary", text, chart)

    return Report("Stakeholder Report - Field Summary", text, txt_path, pdf_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        report = technical_report(sys.argv[1])
    else:
        report = stakeholder_report()
    print(report.text)
    print(f"\nSaved: {report.txt_path}\n       {report.pdf_path}")