"""
dark_theme_prototype.py

STANDALONE STYLE PREVIEW ONLY.

Purpose:
    Prototype the new "control-room" dark theme (matching the
    reference screenshot) before wiring it into the real app.py.
    All data here is randomly generated / hardcoded placeholder --
    none of the real alert, sound, auto-monitor or email logic
    from app.py is included yet.

Run this file directly to preview the look:
    python dark_theme_prototype.py

Once you confirm the style looks right, I'll port these exact
colours/layout into app.py and reconnect every feature we've
already built (flashing banner, alert sound, auto-monitor,
automated email, threshold slider, reports).
"""

import random
import tkinter as tk
from datetime import datetime

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Wedge, Circle


# ----------------------------------------------------------------
# Dark "control room" colour palette
# ----------------------------------------------------------------
BG = "#0A0E17"            # window background
PANEL_BG = "#0F1626"      # card background
PANEL_BORDER = "#1E3A52"  # subtle panel edge
ACCENT_CYAN = "#33D6FF"   # panel titles / glow border
TEXT = "#E8F1F5"
MUTED = "#5E7C90"

GREEN = "#22E5A0"
YELLOW = "#FFD93D"
ORANGE = "#FF9A3D"
RED = "#FF4457"

GRID = "#182838"


def dark_card(parent, glow=ACCENT_CYAN, **kwargs):
    """Panel with a thin neon-style border, matching the reference image."""
    return tk.Frame(
        parent,
        bg=PANEL_BG,
        highlightbackground=glow,
        highlightthickness=1,
        bd=0,
        **kwargs,
    )


def panel_title(parent, text):
    tk.Label(
        parent,
        text=text,
        font=("Consolas", 10, "bold"),
        bg=PANEL_BG,
        fg=ACCENT_CYAN,
        anchor="w",
    ).pack(fill="x", padx=10, pady=(8, 4))


def style_axes(ax):
    ax.set_facecolor(PANEL_BG)
    for spine in ax.spines.values():
        spine.set_color(PANEL_BORDER)
    ax.tick_params(colors=MUTED, labelsize=7)
    ax.grid(color=GRID, linewidth=0.6, linestyle="--", alpha=0.8)
    ax.title.set_color(TEXT)
    ax.yaxis.label.set_color(MUTED)
    ax.xaxis.label.set_color(MUTED)


window = tk.Tk()
window.title("Dark Theme Prototype - Style Preview")
window.geometry("1400x820")
window.configure(bg=BG)

root = tk.Frame(window, bg=BG)
root.pack(fill="both", expand=True, padx=14, pady=10)

root.columnconfigure(0, weight=2)
root.columnconfigure(1, weight=3)
root.columnconfigure(2, weight=2)
root.rowconfigure(1, weight=3)
root.rowconfigure(2, weight=2)


# ----------------------------------------------------------------
# Header
# ----------------------------------------------------------------
header = tk.Frame(root, bg=BG)
header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 10))
header.columnconfigure(0, weight=1)

tk.Label(
    header,
    text="\U0001F6E2  INTELLIGENT ASSET MONITORING & PRED-MAINT ENGINE:",
    font=("Consolas", 13, "bold"),
    bg=BG,
    fg=TEXT,
).grid(row=0, column=0, sticky="w")

clock_label = tk.Label(
    header, text="", font=("Consolas", 10), bg=BG, fg=MUTED
)
clock_label.grid(row=0, column=1, sticky="e")


def tick_clock():
    clock_label.config(text=datetime.now().strftime("%Y-%m-%d | %H:%M:%S UTC"))
    window.after(1000, tick_clock)


tick_clock()


# ----------------------------------------------------------------
# Left: Interactive Asset List
# ----------------------------------------------------------------
asset_card = dark_card(root)
asset_card.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 8))
panel_title(asset_card, "INTERACTIVE ASSET LIST")

ASSETS = [
    ("PRIME-WELL-01", "HIGH FAILURE RISK", RED),
    ("PRIME-WELL-03", "HIGH FAILURE RISK (ML ASSESSMENT)", RED),
    ("PRIME-WELL-04", "HIGH FAILURE RISK (ML ASSESSMENT)", RED),
    ("PRIME-WELL-05", "HIGH FAILURE RISK (ML STATUS)", RED),
    ("PRIME-WELL-02", "HIGH FAILURE RISK (MIOER)", GREEN),
]

for name, status, colour in ASSETS:
    row = tk.Frame(
        asset_card,
        bg=PANEL_BG,
        highlightbackground=colour if colour == RED else PANEL_BORDER,
        highlightthickness=1 if colour == RED else 0,
    )
    row.pack(fill="x", padx=8, pady=4)

    tk.Label(row, text=f"ASSET: {name}", font=("Consolas", 9, "bold"),
             bg=PANEL_BG, fg=TEXT, anchor="w").pack(fill="x", padx=8, pady=(6, 0))
    tk.Label(row, text=f"\u25cf {status}", font=("Consolas", 8),
             bg=PANEL_BG, fg=colour, anchor="w").pack(fill="x", padx=8, pady=(0, 6))


# ----------------------------------------------------------------
# Middle: ML Failure Forecast Engine
# ----------------------------------------------------------------
forecast_card = dark_card(root)
forecast_card.grid(row=1, column=1, sticky="nsew", padx=8)
panel_title(forecast_card, "ML FAILURE FORECAST ENGINE (LSTM MODEL)")

alert_box = tk.Frame(
    forecast_card, bg="#2A1414",
    highlightbackground=RED, highlightthickness=1,
)
alert_box.pack(fill="x", padx=10, pady=(0, 6))

tk.Label(
    alert_box,
    text="\u26a0  PREDICTED FAILURE MODE: ESP MOTOR SEIZE",
    font=("Consolas", 10, "bold"), bg="#2A1414", fg=RED,
).pack(anchor="w", padx=10, pady=(6, 0))
tk.Label(
    alert_box,
    text="ESTIMATED TIME TO FAIL: 14 DAYS   (Confidence: 94.2%)",
    font=("Consolas", 9, "bold"), bg="#2A1414", fg=ORANGE,
).pack(anchor="w", padx=10, pady=(0, 6))

telemetry_fig = Figure(figsize=(6, 3), dpi=100, facecolor=PANEL_BG)
telemetry_ax = telemetry_fig.add_subplot(111)
style_axes(telemetry_ax)

x = np.arange(24)
vibration = np.clip(20 + np.cumsum(np.random.normal(0.8, 1.2, 24)), 15, 50)
motor_current = np.clip(20 + np.cumsum(np.random.normal(0.3, 1.5, 24)), 15, 40)
temperature = np.clip(15 + np.cumsum(np.random.normal(0.1, 0.6, 24)), 10, 25)
pressure = np.full(24, 18) + np.random.normal(0, 0.4, 24)

telemetry_ax.plot(x, vibration, color=RED, linewidth=1.8, label="Vibration")
telemetry_ax.plot(x, motor_current, color=YELLOW, linewidth=1.8, label="Motor_Current")
telemetry_ax.plot(x, temperature, color=GREEN, linewidth=1.8, label="Temperature")
telemetry_ax.plot(x, pressure, color=ACCENT_CYAN, linewidth=1.4, label="Pressure")
telemetry_ax.set_title("Raw Telemetry", fontsize=9, loc="left")
telemetry_ax.legend(fontsize=6, facecolor=PANEL_BG, edgecolor=PANEL_BORDER,
                     labelcolor=TEXT, loc="upper left")
telemetry_fig.tight_layout()

FigureCanvasTkAgg(telemetry_fig, master=forecast_card).get_tk_widget().pack(
    fill="both", expand=True, padx=10, pady=(0, 10)
)


# ----------------------------------------------------------------
# Right: Multi-Phase Production Ratio
# ----------------------------------------------------------------
prod_card = dark_card(root)
prod_card.grid(row=1, column=2, sticky="nsew", padx=(8, 0))
panel_title(prod_card, "MULTI-PHASE PRODUCTION RATIO")

METRICS = [
    ("Oil_Rate", "1,250", "BOPD", 0.7, GREEN),
    ("Gas_Rate", "2.1", "MMCFD", 0.5, GREEN),
    ("Water_Cut", "45", "%", 0.45, ACCENT_CYAN),
    ("GOR", "1680", "SCF/STB", 0.8, GREEN),
]

for label, value, unit, frac, colour in METRICS:
    block = tk.Frame(prod_card, bg=PANEL_BG)
    block.pack(fill="x", padx=12, pady=8)

    tk.Label(block, text=label, font=("Consolas", 8), bg=PANEL_BG,
             fg=MUTED, anchor="w").pack(fill="x")
    tk.Label(block, text=f"{value}  {unit}", font=("Consolas", 14, "bold"),
             bg=PANEL_BG, fg=TEXT, anchor="w").pack(fill="x")

    bar_bg = tk.Frame(block, bg=GRID, height=5)
    bar_bg.pack(fill="x", pady=(4, 0))
    bar_fill = tk.Frame(bar_bg, bg=colour, height=5, width=int(200 * frac))
    bar_fill.place(x=0, y=0, relheight=1)


# ----------------------------------------------------------------
# Bottom-left: Pump Diagnostics (Vibration Spectrum / FFT)
# ----------------------------------------------------------------
pump_card = dark_card(root)
pump_card.grid(row=2, column=0, sticky="nsew", padx=(0, 8), pady=(10, 0))
panel_title(pump_card, "PUMP DIAGNOSTICS")

fft_fig = Figure(figsize=(4, 2.6), dpi=100, facecolor=PANEL_BG)
fft_ax = fft_fig.add_subplot(111)
style_axes(fft_ax)

freqs = np.linspace(0, 240, 300)
spectrum = 8 + 5 * np.random.rand(300)
spike = 200 * np.exp(-((freqs - 60) ** 2) / 10)
spectrum += spike

fft_ax.plot(freqs, spectrum, color=ACCENT_CYAN, linewidth=1.0)
fft_ax.set_title("Acoustic Vibration Spectrum (FFT)", fontsize=8, loc="left")
fft_ax.set_xlabel("Hz", fontsize=7)
fft_ax.annotate(
    "Anomaly Detected:\nPhase Misalignment",
    xy=(60, spectrum[np.argmin(np.abs(freqs - 60))]),
    xytext=(110, 180),
    fontsize=6.5, color="white",
    bbox=dict(boxstyle="round", fc=RED, ec=RED),
    arrowprops=dict(arrowstyle="->", color=RED),
)
fft_fig.tight_layout()

FigureCanvasTkAgg(fft_fig, master=pump_card).get_tk_widget().pack(
    fill="both", expand=True, padx=10, pady=(0, 10)
)


# ----------------------------------------------------------------
# Bottom-middle: Electrical Driver (ESP)
# ----------------------------------------------------------------
esp_card = dark_card(root)
esp_card.grid(row=2, column=1, sticky="nsew", padx=8, pady=(10, 0))
panel_title(esp_card, "ELECTRICAL DRIVER (ESP)")

tk.Label(
    esp_card,
    text="Motor_Current (Amperage Trace)     62.4 A (Overload Threshold)",
    font=("Consolas", 8, "bold"), bg=PANEL_BG, fg=RED,
).pack(anchor="w", padx=10)

amp_fig = Figure(figsize=(4, 2.4), dpi=100, facecolor=PANEL_BG)
amp_ax = amp_fig.add_subplot(111)
style_axes(amp_ax)

t = np.arange(24)
amps = 50 + 30 * np.abs(np.sin(t / 3)) + np.random.normal(0, 4, 24)
amp_ax.plot(t, amps, color=ACCENT_CYAN, linewidth=1.4)
amp_fig.tight_layout()

FigureCanvasTkAgg(amp_fig, master=esp_card).get_tk_widget().pack(
    fill="both", expand=True, padx=10, pady=(0, 10)
)


# ----------------------------------------------------------------
# Bottom-right: Wellhead Mechanics (choke gauge + status)
# ----------------------------------------------------------------
mech_card = dark_card(root)
mech_card.grid(row=2, column=2, sticky="nsew", padx=(8, 0), pady=(10, 0))
panel_title(mech_card, "WELLHEAD MECHANICS")

gauge_fig = Figure(figsize=(3, 2), dpi=100, facecolor=PANEL_BG)
gauge_ax = gauge_fig.add_subplot(111)
gauge_ax.set_facecolor(PANEL_BG)
gauge_ax.set_aspect("equal")
gauge_ax.axis("off")

choke_value = 45
zones = [(0, 50, GREEN), (50, 80, YELLOW), (80, 100, RED)]
for start, end, colour in zones:
    a0 = 180 - (start / 100 * 180)
    a1 = 180 - (end / 100 * 180)
    gauge_ax.add_patch(Wedge((0, 0), 1.0, a1, a0, width=0.3,
                              facecolor=colour, edgecolor=PANEL_BG, linewidth=2))

angle = np.radians(180 - (choke_value / 100 * 180))
gauge_ax.plot([0, 0.75 * np.cos(angle)], [0, 0.75 * np.sin(angle)],
              color="white", linewidth=2.5, solid_capstyle="round")
gauge_ax.add_patch(Circle((0, 0), 0.05, facecolor="white"))
gauge_ax.text(0, -0.3, f"{choke_value:.1f}%", fontsize=13, fontweight="bold",
              ha="center", color=TEXT)
gauge_ax.text(0, -0.5, "Open", fontsize=7, ha="center", color=MUTED)
gauge_ax.set_xlim(-1.1, 1.1)
gauge_ax.set_ylim(-0.6, 1.1)
gauge_fig.tight_layout()

FigureCanvasTkAgg(gauge_fig, master=mech_card).get_tk_widget().pack(padx=10, pady=(0, 4))

tk.Label(mech_card, text="Pump_Status:", font=("Consolas", 8),
         bg=PANEL_BG, fg=MUTED).pack(anchor="w", padx=12)
tk.Label(mech_card, text="RUNNING", font=("Consolas", 12, "bold"),
         bg=PANEL_BG, fg=GREEN).pack(anchor="w", padx=12, pady=(0, 10))


window.mainloop()