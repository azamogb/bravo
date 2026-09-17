"""
Chart drawing for the dashboard (matplotlib figures embedded in Tk).

Extracted verbatim from app.py -- every function here only operates on
the ax/figure/canvas/data passed to it as arguments; none of them
depend on app.py's widgets or global state.
"""

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Wedge, Circle
import matplotlib.dates as mdates

from config import (
    PANEL_BG, PANEL_BORDER, ACCENT_CYAN, TEXT, MUTED,
    GREEN, YELLOW, RED, GRID, BG_HIGH,
    MOTOR_CURRENT_OVERLOAD_A, VIBRATION_ANOMALY_MM_S,
)


# ----------------------------------------------------------------
# Axes styling / construction
# ----------------------------------------------------------------
def style_axes(ax):
    ax.set_facecolor(PANEL_BG)
    for spine in ax.spines.values():
        spine.set_color(PANEL_BORDER)
    ax.tick_params(colors=MUTED, labelsize=7)
    ax.grid(color=GRID, linewidth=0.6, linestyle="--", alpha=0.8)
    ax.yaxis.label.set_color(MUTED)
    ax.xaxis.label.set_color(MUTED)
    # ax.title, ax._left_title and ax._right_title are three separate
    # text objects in matplotlib; colour all of them so a loc="left"
    # title never falls back to the default black-on-dark.
    for title in (ax.title, ax._left_title, ax._right_title):
        title.set_color(TEXT)


def date_axis(ax):
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))


def make_chart(parent, figsize, **pack):
    """Creates a styled figure embedded in a Tk parent. Returns
    (figure, ax, canvas)."""
    figure = Figure(figsize=figsize, dpi=100, facecolor=PANEL_BG)
    ax = figure.add_subplot(111)
    style_axes(ax)
    canvas = FigureCanvasTkAgg(figure, master=parent)
    canvas.get_tk_widget().pack(**pack)
    return figure, ax, canvas


# ----------------------------------------------------------------
# Speedometer gauge
# ----------------------------------------------------------------
def _value_to_angle(value, vmax=100):
    value = max(0, min(vmax, value))
    return 180 - (value / vmax * 180)


def draw_gauge(ax, figure, canvas, value, zones, value_text, sub_text,
               colour, vmax=100):
    """
    zones: list of (start, end, colour) sweeps over 0..vmax.
    value: number to point the needle at, or None for no needle.
    """
    ax.clear()
    ax.set_facecolor(PANEL_BG)
    ax.set_aspect("equal")
    ax.axis("off")

    for start, end, zone_colour in zones:
        if end <= start:
            continue
        ax.add_patch(Wedge((0, 0), 1.0, _value_to_angle(end, vmax),
                           _value_to_angle(start, vmax), width=0.30,
                           facecolor=zone_colour, edgecolor=PANEL_BG,
                           linewidth=2))

    if value is not None:
        angle = np.radians(_value_to_angle(value, vmax))
        ax.plot([0, 0.8 * np.cos(angle)], [0, 0.8 * np.sin(angle)],
                color="white", linewidth=3, solid_capstyle="round", zorder=5)
        ax.add_patch(Circle((0, 0), 0.06, facecolor="white", zorder=6))

    ax.text(0, -0.30, value_text, fontsize=18, fontweight="bold",
            ha="center", va="center", color=colour)
    ax.text(0, -0.52, sub_text, fontsize=8, fontweight="bold",
            ha="center", va="center", color=colour)

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-0.62, 1.12)
    figure.tight_layout(pad=0.2)
    canvas.draw()


# ----------------------------------------------------------------
# Raw telemetry (multi-series overlay)
# ----------------------------------------------------------------
TELEMETRY_SERIES = [
    ("Vibration", RED),
    ("Motor_Current", ACCENT_CYAN),
    ("Temperature", YELLOW),
    ("Pressure", GREEN),
]


def chart_plot_telemetry(ax, figure, canvas, df):
    """
    Overlays vibration, motor current, temperature and pressure. Each
    series is scaled to 0-100% of its own range so they share one
    axis. Days where the pump was recorded as failed are shaded red.
    """
    ax.clear()
    style_axes(ax)

    dates = df["Date"]

    for column, colour in TELEMETRY_SERIES:
        values = df[column].values.astype(float)
        span = values.max() - values.min()
        normalised = (values - values.min()) / span * 100 if span else values * 0 + 50
        ax.plot(dates, normalised, color=colour, linewidth=1.6,
                label=column.replace("_", " "))

    for day in df[df["Pump_Status"] == 1]["Date"]:
        ax.axvspan(day - np.timedelta64(12, "h"), day + np.timedelta64(12, "h"),
                   color=RED, alpha=0.10, linewidth=0)

    ax.set_ylim(-5, 105)
    ax.set_ylabel("% of range", fontsize=8)
    ax.set_title(f"Raw Telemetry \u2014 last {len(df)} days", fontsize=9,
                 fontweight="bold", loc="left", pad=6, color=TEXT)
    date_axis(ax)

    legend = ax.legend(loc="upper left", ncol=4, fontsize=7, frameon=False)
    for text in legend.get_texts():
        text.set_color(TEXT)

    figure.tight_layout(pad=0.6)
    canvas.draw()


# ----------------------------------------------------------------
# Pump diagnostics (acoustic vibration spectrum)
# ----------------------------------------------------------------
def synth_spectrum(vib_rms, seed):
    """
    Builds a vibration spectrum from the well's current vibration
    level. Real deployments should replace this with an FFT of the
    high-frequency accelerometer signal; the daily-average Vibration
    column in the database is far too coarse to transform directly.
    """
    rng = np.random.default_rng(seed)
    fs, n = 500, 2048
    t = np.arange(n) / fs

    signal = (1.0 * np.sin(2 * np.pi * 25 * t)
              + 0.45 * np.sin(2 * np.pi * 75 * t)
              + 0.25 * np.sin(2 * np.pi * 125 * t)
              + 0.35 * rng.standard_normal(n))

    anomaly = vib_rms >= VIBRATION_ANOMALY_MM_S
    if anomaly:
        boost = vib_rms / VIBRATION_ANOMALY_MM_S
        signal += (1.6 * boost * np.sin(2 * np.pi * 50 * t)
                   + 0.6 * boost * np.sin(2 * np.pi * 100 * t))

    spectrum = np.abs(np.fft.rfft(signal)) / n * 2 * 250
    freqs = np.fft.rfftfreq(n, 1 / fs)
    mask = freqs <= 240
    return freqs[mask], spectrum[mask], anomaly


def chart_plot_fft(ax, figure, canvas, df, window_days):
    """Returns (vib_rms, anomaly_flag) for the caller's labels."""

    well = str(df["Well_ID"].iloc[0]) if "Well_ID" in df else "well"
    vib_rms = float(df["Vibration"].tail(window_days).max())
    freqs, spectrum, anomaly = synth_spectrum(vib_rms, seed=hash(well) & 0xFFFF)

    ax.clear()
    style_axes(ax)

    ax.plot(freqs, spectrum, color=ACCENT_CYAN, linewidth=1.2)
    ax.fill_between(freqs, spectrum, color=ACCENT_CYAN, alpha=0.12)

    if anomaly:
        peak_index = int(np.argmax(spectrum))
        peak_f, peak_a = freqs[peak_index], spectrum[peak_index]
        band = (freqs > peak_f - 6) & (freqs < peak_f + 6)
        ax.plot(freqs[band], spectrum[band], color=RED, linewidth=1.6)
        ax.annotate(
            f"Anomaly Detected\n{peak_f:.0f} Hz peak\nimbalance / misalignment",
            xy=(peak_f, peak_a), xytext=(0.95, 0.90), textcoords="axes fraction",
            ha="right", va="top", fontsize=7, color=TEXT, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", fc=BG_HIGH, ec=RED, lw=1),
            arrowprops=dict(arrowstyle="-", color=RED, lw=1),
        )

    ax.set_xlabel("Hz", fontsize=8)
    ax.set_ylabel("Amplitude", fontsize=8)
    ax.set_xlim(0, 240)
    ax.set_title(f"Vibration RMS {vib_rms:.2f} mm/s ({window_days}-day peak)",
                 fontsize=8, loc="left", pad=4, color=RED if anomaly else MUTED)

    figure.tight_layout(pad=0.6)
    canvas.draw()
    return vib_rms, anomaly


# ----------------------------------------------------------------
# Electrical driver (ESP motor current)
# ----------------------------------------------------------------
def chart_plot_esp(ax, figure, canvas, df):
    """Returns (latest_amps, overloaded) for the caller's labels."""

    dates, amps = df["Date"], df["Motor_Current"].values.astype(float)

    ax.clear()
    style_axes(ax)

    ax.plot(dates, amps, color=ACCENT_CYAN, linewidth=1.6, marker="o",
            markersize=2.5)
    ax.axhline(MOTOR_CURRENT_OVERLOAD_A, color=RED, linewidth=1,
               linestyle="--", alpha=0.9)
    ax.text(dates.iloc[-1], MOTOR_CURRENT_OVERLOAD_A + 3,
            f"Overload {MOTOR_CURRENT_OVERLOAD_A:.0f} A", fontsize=7,
            color=RED, va="bottom", ha="right",
            bbox=dict(boxstyle="round,pad=0.2", fc=PANEL_BG, ec="none"))

    over = amps > MOTOR_CURRENT_OVERLOAD_A
    if over.any():
        ax.scatter(dates[over], amps[over], color=RED, s=18, zorder=5)

    ax.set_ylabel("A", fontsize=8)
    ax.set_ylim(0, max(150, amps.max() * 1.1))
    date_axis(ax)

    figure.tight_layout(pad=0.6)
    canvas.draw()

    latest = float(amps[-1])
    return latest, latest > MOTOR_CURRENT_OVERLOAD_A


# ----------------------------------------------------------------
# Wellhead: choke position sparkline
# ----------------------------------------------------------------
def chart_plot_choke(ax, figure, canvas, df):
    """Returns the latest choke position (%)."""

    dates, choke = df["Date"], df["Choke_Position"].values.astype(float)

    ax.clear()
    style_axes(ax)
    ax.plot(dates, choke, color=ACCENT_CYAN, linewidth=1.4)
    ax.fill_between(dates, choke, color=ACCENT_CYAN, alpha=0.12)
    ax.set_ylim(0, 100)
    ax.set_yticks([0, 100])
    ax.set_xticks([dates.iloc[0], dates.iloc[-1]])
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.tick_params(labelsize=6, length=2)
    ax.grid(False)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    figure.tight_layout(pad=0.3)
    canvas.draw()
    return float(choke[-1])