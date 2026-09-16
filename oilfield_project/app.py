import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
import subprocess
import threading
import time
from datetime import datetime


try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from alerts import play_alert_sound_async, stop_alert_sound
from emailer import send_email
import reports
from data_loader import load_well, list_wells
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Wedge, Circle
import matplotlib.dates as mdates
from config import (
    TECH_EMAIL, ALERT_COOLDOWN_SECONDS, AUTO_MONITOR_INTERVAL_MS,
    RISK_THRESHOLD, FLEET_NAME, FEATURE_COLUMNS,
    MOTOR_CURRENT_OVERLOAD_A, VIBRATION_ANOMALY_MM_S,
)

# ML module. When predict.py imports and a trained model exists at
# config.MODEL_PATH, its predict_risk() drives the risk score; otherwise
# the dashboard falls back to a rule-based estimate so the GUI stays
# fully usable. Run train_model.py to create the model.
try:
    from predict import predict_risk as ml_predict_risk
except ImportError:
    ml_predict_risk = None

from config import MODEL_PATH
ML_ACTIVE = ml_predict_risk is not None and os.path.isfile(MODEL_PATH)


# ----------------------------------------------------------------
# Dark "control room" colour palette
# ----------------------------------------------------------------
BG = "#0A0E17"            # window / outer background
PANEL_BG = "#0F1626"      # card background
PANEL_BORDER = "#1E3A52"  # subtle panel edge (unselected)
ACCENT_CYAN = "#33D6FF"   # panel titles / glow border / selection

TEXT = "#E8F1F5"
MUTED = "#8FAFC4"

GREEN = "#22E5A0"
GREEN_DARK = "#149E72"
YELLOW = "#FFD93D"
ORANGE = "#FF9A3D"
RED = "#FF4457"

GRID = "#182838"

# Status badge backgrounds, one per risk level
BG_HIGH = "#2A1414"
BG_WARN = "#2E2711"
BG_NORMAL = "#0F2A20"

UNSELECTED_BTN_BG = "#152238"

MONO = "Consolas"
SANS = "Segoe UI"


# ================================================================
# CHART DRAWING (matplotlib)
# ================================================================
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


# ----------------------------------------------------------------
# Main window
# ----------------------------------------------------------------
window = tk.Tk()
window.title("Digital Oilfield Monitor")
window.geometry("1500x900")
window.minsize(1250, 800)
window.configure(bg=BG)

try:
    window.state("zoomed")
except tk.TclError:
    try:
        window.attributes("-zoomed", True)
    except tk.TclError:
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        window.geometry(f"{screen_w}x{screen_h}+0+0")


def load_logo_photo(max_height=36):
    """Loads assets/logo.png|jpg if present; returns None otherwise."""

    if not PIL_AVAILABLE:
        return None

    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "assets")

    for filename in ("logo.png", "logo.jpg", "logo.jpeg"):
        path = os.path.join(assets_dir, filename)
        if os.path.isfile(path):
            try:
                image = Image.open(path)
                ratio = max_height / image.height
                image = image.resize(
                    (max(1, int(image.width * ratio)), max_height), Image.LANCZOS
                )
                return ImageTk.PhotoImage(image)
            except Exception as error:
                print(f"Could not load logo from {path}: {error}")
                return None
    return None


# ----------------------------------------------------------------
# State
# ----------------------------------------------------------------
WELLS = list_wells()

well_var = tk.StringVar(value=WELLS[0])
current_period = tk.IntVar(value=30)
threshold_var = tk.DoubleVar(value=RISK_THRESHOLD * 100)
auto_monitor_var = tk.BooleanVar(value=False)

well_risk_cache = {}          # well -> last computed risk (0-100)
current_gauge_risk = None     # risk currently drawn on the gauge, or None

last_alert_sent_at = {}
banner_flash_job = None
banner_flash_on = False
auto_monitor_job = None

asset_rows = {}
period_buttons = {}
kpi_tiles = {}                # key -> {"value": Label, "bar": Canvas, "colour": str}

# Widgets assigned during UI construction
status_message = None
threshold_label = None
selected_well_label = None
email_entry = None
alert_banner = None
alert_banner_label = None
alert_dismiss_button = None
forecast_callout = None
forecast_line1 = None
forecast_line2 = None
esp_value_label = None
pump_status_label = None
choke_value_label = None


# ----------------------------------------------------------------
# ttk styles
# ----------------------------------------------------------------
style = ttk.Style()
try:
    style.theme_use("clam")
except tk.TclError:
    pass

style.configure(
    "Modern.TButton", font=(SANS, 10, "bold"), padding=(14, 7),
    background=ACCENT_CYAN, foreground="#04121A", borderwidth=0,
)
style.map("Modern.TButton",
          background=[("active", GREEN_DARK), ("pressed", GREEN_DARK)])

style.configure("Alert.TCheckbutton", font=(SANS, 9, "bold"),
                background=PANEL_BG, foreground=TEXT)
style.map(
    "Alert.TCheckbutton",
    background=[("active", PANEL_BG)],
    foreground=[("active", ACCENT_CYAN)],
    indicatorcolor=[("selected", ACCENT_CYAN), ("!selected", PANEL_BG)],
    indicatorbackground=[("selected", ACCENT_CYAN), ("!selected", PANEL_BG)],
    indicatorforeground=[("!selected", PANEL_BORDER)],
)


# ----------------------------------------------------------------
# Layout / styling helpers
# ----------------------------------------------------------------
def dark_card(parent, glow=ACCENT_CYAN, **kwargs):
    return tk.Frame(parent, bg=PANEL_BG, highlightbackground=glow,
                    highlightthickness=1, bd=0, **kwargs)


def panel_header(parent, title, subtitle=None):
    """Title row for a card. Returns the header frame so callers can
    pack extra controls on the right."""

    header = tk.Frame(parent, bg=PANEL_BG)
    header.pack(fill="x", padx=12, pady=(8, 2))

    title_col = tk.Frame(header, bg=PANEL_BG)
    title_col.pack(side="left")

    tk.Label(title_col, text=title, font=(MONO, 10, "bold"),
             bg=PANEL_BG, fg=ACCENT_CYAN, anchor="w").pack(anchor="w")

    if subtitle:
        tk.Label(title_col, text=subtitle, font=(MONO, 8),
                 bg=PANEL_BG, fg=MUTED, anchor="w").pack(anchor="w")

    return header


def get_risk_status(risk):
    threshold = threshold_var.get()
    if risk >= threshold:
        return "HIGH RISK", RED, BG_HIGH
    if risk >= 50:
        return "WARNING", ORANGE, BG_WARN
    return "NORMAL", GREEN, BG_NORMAL


# ----------------------------------------------------------------
# Risk / failure prediction
# ----------------------------------------------------------------
def _clip01(x):
    return float(max(0.0, min(1.0, x)))


RISK_WINDOW_DAYS = 3


def predict_failure(well):
    """
    Returns a dict describing the failure forecast for a well:
        risk        0-100
        mode        predicted failure mode text
        eta_days    estimated days to failure (None when NORMAL)
        confidence  0-100

    Uses predict.py when available. The failure-mode / ETA logic is
    rule-based until the ML module provides those directly.
    """

    df = load_well(well)

    # Score the worst reading in the recent window so a well that
    # tripped two days ago is still flagged, not just one whose very
    # last record happens to look bad.
    recent_rows = df.tail(RISK_WINDOW_DAYS)
    vib = float(recent_rows["Vibration"].max())
    amps = float(recent_rows["Motor_Current"].max())
    pressure = float(recent_rows["Pressure"].min())
    temp = float(recent_rows["Temperature"].max())

    vib_score = _clip01((vib - 1.0) / 6.0)
    amps_score = _clip01((amps - 40.0) / 80.0)
    press_score = _clip01((2000.0 - pressure) / 1200.0)
    temp_score = _clip01((temp - 95.0) / 25.0)

    risk = None
    if ML_ACTIVE:
        try:
            # predict_risk returns the highest failure probability across
            # the rows given, so pass the same recent window scored above.
            raw = float(ml_predict_risk(recent_rows[FEATURE_COLUMNS]))
            risk = raw * 100.0 if raw <= 1.0 else raw
        except Exception as error:
            print(f"predict.py failed for {well}, using rule-based risk: {error}")

    if risk is None:
        risk = 100.0 * (0.40 * vib_score + 0.35 * amps_score
                        + 0.20 * press_score + 0.05 * temp_score)

    risk = float(max(0.0, min(100.0, risk)))

    # Rule-based failure mode from the dominant driver
    if risk < 50:
        mode = "NO FAILURE PREDICTED"
    else:
        drivers = {
            "ESP MOTOR SEIZE": amps_score * 0.6 + vib_score * 0.4,
            "PUMP BEARING WEAR": vib_score,
            "GAS LOCK / PRESSURE DEPLETION": press_score,
            "MOTOR OVERHEAT": temp_score * 0.7 + amps_score * 0.3,
        }
        mode = max(drivers, key=drivers.get)

    eta_days = None if risk < 50 else max(1, int(round(60 * (1 - risk / 100))))

    # Recent trend agreement makes the estimate more "confident"
    recent = df["Vibration"].tail(5).values
    trend_agree = 1.0 if len(recent) < 2 or (recent[-1] >= recent[0]) == (risk >= 50) else 0.6
    confidence = round(70 + 25 * trend_agree * abs(risk - 50) / 50, 1)

    return {"risk": risk, "mode": mode, "eta_days": eta_days,
            "confidence": confidence}


def get_well_risk(well):
    """Risk 0-100 for the asset list / auto-monitor (cached)."""
    if well not in well_risk_cache:
        well_risk_cache[well] = predict_failure(well)["risk"]
    return well_risk_cache[well]


# ----------------------------------------------------------------
# Risk gauge
# ----------------------------------------------------------------
def draw_risk_gauge(value):
    global current_gauge_risk
    current_gauge_risk = value

    threshold = threshold_var.get()
    zones = [(0, 50, GREEN), (50, threshold, ORANGE), (threshold, 100, RED)]
    status, colour, _ = get_risk_status(value)
    draw_gauge(gauge_ax, gauge_figure, gauge_canvas, value, zones,
                      f"{value:.0f}%", status, colour)


def reset_risk_gauge():
    global current_gauge_risk
    current_gauge_risk = None
    draw_gauge(gauge_ax, gauge_figure, gauge_canvas, None,
                      [(0, 100, PANEL_BORDER)], "--", "FAILURE RISK", MUTED)


# ----------------------------------------------------------------
# High-risk alerts: banner, sound, automated email
# ----------------------------------------------------------------
def start_banner_flash():
    global banner_flash_job, banner_flash_on

    if alert_banner is None:
        return

    banner_flash_on = not banner_flash_on
    flash_bg = RED if banner_flash_on else BG_HIGH
    flash_fg = "#04121A" if banner_flash_on else RED

    alert_banner.config(bg=flash_bg, highlightbackground=RED)
    alert_banner_label.config(bg=flash_bg, fg=flash_fg)
    alert_dismiss_button.config(bg=flash_bg, fg=flash_fg)

    banner_flash_job = window.after(600, start_banner_flash)


def stop_banner_flash():
    global banner_flash_job

    if banner_flash_job is not None:
        window.after_cancel(banner_flash_job)
        banner_flash_job = None

    if alert_banner is not None:
        alert_banner.grid_remove()

    stop_alert_sound()


def show_alert_banner(well, risk):
    if alert_banner is None:
        return

    alert_banner_label.config(
        text=f"\u26a0  HIGH RISK: {well} is at {risk:.0f}% failure risk "
             f"\u2014 technical team has been alerted."
    )
    alert_banner.grid()

    if banner_flash_job is None:
        start_banner_flash()


def dismiss_alert_banner():
    stop_banner_flash()


def build_alert_email(well, forecast):
    subject = f"[Oilfield Monitor] HIGH RISK ALERT - {well} ({forecast['risk']:.0f}%)"
    eta = forecast["eta_days"]
    body = (
        f"Automated alert from the Digital Oilfield Monitor.\n\n"
        f"Well: {well}\n"
        f"Risk score: {forecast['risk']:.0f}%\n"
        f"Predicted failure mode: {forecast['mode']}\n"
        f"Estimated time to fail: {eta} day(s)\n"
        f"Model confidence: {forecast['confidence']:.1f}%\n"
        f"Threshold: {threshold_var.get():.0f}%\n"
        f"Detected at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"This well has crossed the configured risk threshold and "
        f"requires attention. This message was sent automatically -- "
        f"no action is needed to trigger it."
    )
    return subject, body


def _send_alert_email_worker(well, forecast):
    subject, body = build_alert_email(well, forecast)
    try:
        send_email(TECH_EMAIL, subject, body)
        window.after(0, lambda: status_message.config(
            text=f"Automatic alert email sent to technical team for {well}.",
            fg=RED))
    except Exception as error:
        error_text = str(error)
        window.after(0, lambda: status_message.config(
            text=f"Could not send automatic alert email for {well}: {error_text}",
            fg=RED))


def trigger_high_risk_alert(well, forecast):
    risk = forecast["risk"]
    show_alert_banner(well, risk)
    play_alert_sound_async()

    now = time.time()
    last_sent = last_alert_sent_at.get(well, 0)

    if now - last_sent < ALERT_COOLDOWN_SECONDS:
        remaining_min = int((ALERT_COOLDOWN_SECONDS - (now - last_sent)) / 60) + 1
        status_message.config(
            text=f"{well} is HIGH RISK. Email already sent recently "
                 f"(next alert possible in ~{remaining_min} min).",
            fg=RED)
        return

    last_alert_sent_at[well] = now
    threading.Thread(target=_send_alert_email_worker,
                     args=(well, forecast), daemon=True).start()


def toggle_auto_monitor():
    global auto_monitor_job

    if auto_monitor_var.get():
        status_message.config(
            text="Auto-monitor enabled: all wells re-checked "
                 f"every {AUTO_MONITOR_INTERVAL_MS // 1000}s.", fg=MUTED)
        auto_monitor_tick()
    else:
        if auto_monitor_job is not None:
            window.after_cancel(auto_monitor_job)
            auto_monitor_job = None
        status_message.config(text="Auto-monitor disabled.", fg=MUTED)


def auto_monitor_tick():
    global auto_monitor_job

    if not auto_monitor_var.get():
        return

    any_high_risk = False

    for well in WELLS:
        forecast = predict_failure(well)
        well_risk_cache[well] = forecast["risk"]
        status, _, _ = get_risk_status(forecast["risk"])
        if status == "HIGH RISK":
            any_high_risk = True
            trigger_high_risk_alert(well, forecast)

    update_well_status()

    if not any_high_risk:
        stop_banner_flash()

    auto_monitor_job = window.after(AUTO_MONITOR_INTERVAL_MS, auto_monitor_tick)


# ----------------------------------------------------------------
# Asset list + well selection
# ----------------------------------------------------------------
def update_well_status():
    for well, widgets in asset_rows.items():
        risk = get_well_risk(well)
        status, colour, background = get_risk_status(risk)
        widgets["status"].config(text=f"\u25cf {risk:.0f}%  {status}",
                                 fg=colour, bg=background)
        widgets["name_label"].config(bg=background)
        widgets["frame"].config(bg=background)


def highlight_selected_asset():
    selected = well_var.get()
    for well, widgets in asset_rows.items():
        if well == selected:
            widgets["frame"].config(highlightbackground=ACCENT_CYAN,
                                    highlightthickness=2)
        else:
            widgets["frame"].config(highlightbackground=PANEL_BORDER,
                                    highlightthickness=1)


def select_well(well):
    well_var.set(well)
    highlight_selected_asset()
    selected_well_label.config(text=f"Selected: {well}")

    reset_risk_gauge()
    set_forecast_neutral(well)
    refresh_panels()

    status_message.config(
        text=f"{well} selected. Run diagnostics to assess current risk.",
        fg=MUTED)


def refresh_panels():
    """Redraws every data panel for the selected well and period."""
    plot_telemetry()
    update_kpi_tiles()
    plot_fft()
    plot_esp()
    plot_wellhead()


# ----------------------------------------------------------------
# ML Failure Forecast callout
# ----------------------------------------------------------------
def set_forecast_neutral(well):
    forecast_callout.config(highlightbackground=PANEL_BORDER, bg=PANEL_BG)
    forecast_line1.config(text=f"FAILURE FORECAST: {well}", fg=TEXT, bg=PANEL_BG)
    forecast_line2.config(text="Run diagnostics to generate a prediction.",
                          fg=MUTED, bg=PANEL_BG)
    sync_callout_icon()


def set_forecast(well, forecast):
    status, colour, background = get_risk_status(forecast["risk"])
    forecast_callout.config(highlightbackground=colour, bg=background)
    forecast_line1.config(text=f"PREDICTED FAILURE MODE: {forecast['mode']}",
                          fg=colour, bg=background)

    if forecast["eta_days"] is None:
        line2 = (f"RISK: {forecast['risk']:.0f}%  \u2022  {status}  \u2022  "
                 f"Confidence: {forecast['confidence']:.1f}%")
    else:
        line2 = (f"RISK: {forecast['risk']:.0f}%  \u2022  "
                 f"ESTIMATED TIME TO FAIL: {forecast['eta_days']} DAYS  "
                 f"(Confidence: {forecast['confidence']:.1f}%)")

    forecast_line2.config(text=line2, fg=TEXT, bg=background)
    sync_callout_icon()


def run_diagnostics():
    well = well_var.get()
    forecast = predict_failure(well)
    well_risk_cache[well] = forecast["risk"]

    status, colour, _ = get_risk_status(forecast["risk"])

    draw_risk_gauge(forecast["risk"])
    set_forecast(well, forecast)
    update_well_status()

    status_message.config(text=f"Diagnostic result for {well}: {status}.",
                          fg=colour)

    if status == "HIGH RISK":
        trigger_high_risk_alert(well, forecast)
    else:
        stop_banner_flash()


# ----------------------------------------------------------------
# Panel: raw telemetry (multi-series)
# ----------------------------------------------------------------
def select_period(days):
    current_period.set(days)
    update_period_buttons()
    refresh_panels()


def update_period_buttons():
    selected = current_period.get()
    for period, button in period_buttons.items():
        if period == selected:
            button.config(bg=ACCENT_CYAN, fg="#04121A")
        else:
            button.config(bg=UNSELECTED_BTN_BG, fg=TEXT)


def plot_telemetry():
    chart_plot_telemetry(tele_ax, tele_figure, tele_canvas,
                          load_well(well_var.get(), current_period.get()))


# ----------------------------------------------------------------
# Panel: multi-phase production KPI tiles
# ----------------------------------------------------------------
KPI_SPECS = [
    ("Oil_Rate", "Oil_Rate", "BOPD", ACCENT_CYAN, "{:,.0f}"),
    ("Gas_Rate", "Gas_Rate", "MSCF/D", YELLOW, "{:,.0f}"),
    ("Water_Cut", "Water_Cut", "%", ACCENT_CYAN, "{:.1f}"),
    ("GOR", "GOR", "SCF/STB", GREEN, "{:,.0f}"),
]


def build_kpi_tile(parent, key, label, unit, colour):
    tile = tk.Frame(parent, bg=PANEL_BG)
    tile.pack(fill="x", padx=12, pady=5)

    bar = tk.Frame(tile, bg=colour, width=4)
    bar.pack(side="left", fill="y")

    body = tk.Frame(tile, bg=PANEL_BG)
    body.pack(side="left", fill="both", expand=True, padx=(10, 0))

    tk.Label(body, text=label, font=(MONO, 8), bg=PANEL_BG, fg=MUTED,
             anchor="w").pack(anchor="w")

    value_row = tk.Frame(body, bg=PANEL_BG)
    value_row.pack(anchor="w")

    value = tk.Label(value_row, text="--", font=(MONO, 20, "bold"),
                     bg=PANEL_BG, fg=colour)
    value.pack(side="left")
    tk.Label(value_row, text=f"  {unit}", font=(MONO, 9), bg=PANEL_BG,
             fg=MUTED).pack(side="left", anchor="s", pady=(0, 5))

    progress = tk.Canvas(body, height=4, bg=GRID, highlightthickness=0)
    progress.pack(fill="x", pady=(2, 0))

    kpi_tiles[key] = {"value": value, "bar": progress, "colour": colour}


def update_kpi_tiles():
    well = well_var.get()
    df = load_well(well, current_period.get())
    latest = df.iloc[-1]

    for key, column, unit, colour, fmt in KPI_SPECS:
        tile = kpi_tiles[key]
        value = float(latest[column])
        tile["value"].config(text=fmt.format(value))

        peak = float(df[column].max()) or 1.0
        fraction = max(0.0, min(1.0, value / peak))
        canvas = tile["bar"]
        canvas.delete("all")
        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 1)
        canvas.create_rectangle(0, 0, width * fraction, 4, fill=colour, width=0)


# ----------------------------------------------------------------
# Panel: pump diagnostics (acoustic vibration spectrum)
# ----------------------------------------------------------------
def plot_fft():
    chart_plot_fft(fft_ax, fft_figure, fft_canvas,
                    load_well(well_var.get(), current_period.get()),
                    RISK_WINDOW_DAYS)


# ----------------------------------------------------------------
# Panel: electrical driver (ESP motor current)
# ----------------------------------------------------------------
def plot_esp():
    latest, overloaded = chart_plot_esp(
        esp_ax, esp_figure, esp_canvas,
        load_well(well_var.get(), current_period.get()))

    if overloaded:
        esp_value_label.config(text=f"{latest:.1f} A  (OVERLOAD)", fg=RED)
    else:
        esp_value_label.config(text=f"{latest:.1f} A  (nominal)", fg=GREEN)


# ----------------------------------------------------------------
# Panel: wellhead mechanics (risk gauge + choke + pump status)
# ----------------------------------------------------------------
def plot_wellhead():
    df = load_well(well_var.get(), current_period.get())
    latest_choke = chart_plot_choke(choke_ax, choke_figure, choke_canvas, df)
    choke_value_label.config(text=f"{latest_choke:.1f}% Open")

    if int(df["Pump_Status"].iloc[-1]) == 1:
        pump_status_label.config(text="FAILED", fg=RED)
    else:
        pump_status_label.config(text="RUNNING", fg=GREEN)


# ----------------------------------------------------------------
# Alert threshold
# ----------------------------------------------------------------
def update_threshold(value):
    threshold = float(value)
    threshold_label.config(text=f"{threshold:.0f}%")
    update_well_status()
    if current_gauge_risk is not None:
        draw_risk_gauge(current_gauge_risk)


# ----------------------------------------------------------------
# Reports and email
# ----------------------------------------------------------------
last_report = None      # most recently generated reports.Report


def _open_file(path):
    """Opens a file with the OS default application (best effort)."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)                          # noqa
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as error:
        messagebox.showinfo("Report saved", f"Saved to:\n{path}\n\n({error})")


def _report_finished(report):
    global last_report
    last_report = report

    status_message.config(
        text=f"{report.title} generated. Enter an address and click "
             f"Send Report to email it.", fg=GREEN)

    if messagebox.askyesno(
            report.title,
            f"{report.title} generated.\n\nSaved to:\n{report.pdf_path}\n\n"
            f"Open the PDF now?"):
        _open_file(report.pdf_path)


def _run_report(builder, *args):
    """Generates a report on a worker thread so the GUI stays responsive."""

    status_message.config(text="Generating report...", fg=MUTED)

    def worker():
        try:
            report = builder(*args)
            window.after(0, lambda: _report_finished(report))
        except Exception as error:
            error_text = str(error)
            window.after(0, lambda: messagebox.showerror(
                "Report Failed", f"Could not generate the report:\n{error_text}"))

    threading.Thread(target=worker, daemon=True).start()


def technical_report():
    """Mean / max / standard deviation of every metric for the selected well."""
    _run_report(reports.technical_report, well_var.get(), current_period.get())


def stakeholder_report():
    """Total oil produced and field status across all wells."""
    _run_report(reports.stakeholder_report, current_period.get())


def send_report():
    """Emails the last generated report (PDF attached) to the address entered."""

    email = email_entry.get().strip()

    if not email or email == "name@company.com":
        messagebox.showwarning("Email Required", "Please enter an email address.")
        return
    if "@" not in email or "." not in email:
        messagebox.showwarning("Invalid Email", "Please enter a valid email address.")
        return
    if last_report is None:
        messagebox.showwarning(
            "No Report",
            "Generate a Technical or Stakeholder report first, then send it.")
        return

    report = last_report
    subject = f"[Oilfield Monitor] {report.title}"
    body = (
        f"{report.title}\n"
        f"Sent from the Digital Oilfield Monitor dashboard on "
        f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
        f"The full report is attached as PDF; a plain-text copy follows.\n\n"
        f"{'-' * 62}\n{report.text}"
    )

    status_message.config(text=f"Sending {report.title} to {email}...", fg=MUTED)

    def worker():
        try:
            send_email(email, subject, body, attachments=[report.pdf_path])
            window.after(0, lambda: (
                status_message.config(text=f"Report emailed to {email}.", fg=GREEN),
                messagebox.showinfo("Report Sent", f"{report.title} sent to {email}.")))
        except Exception as error:
            error_text = str(error)
            window.after(0, lambda: (
                status_message.config(text="Report email failed.", fg=RED),
                messagebox.showerror("Send Failed",
                                     f"Could not send the report:\n{error_text}")))

    threading.Thread(target=worker, daemon=True).start()


# ==================================================================
# UI CONSTRUCTION
# ==================================================================
root = tk.Frame(window, bg=BG)
root.pack(fill="both", expand=True, padx=14, pady=10)

root.columnconfigure(0, weight=2, uniform="cols")
root.columnconfigure(1, weight=4, uniform="cols")
root.columnconfigure(2, weight=2, uniform="cols")
root.rowconfigure(3, weight=5)
root.rowconfigure(4, weight=4)


# ------------------------------------------------------------
# Header
# ------------------------------------------------------------
header = tk.Frame(root, bg=BG)
header.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 8))

title_frame = tk.Frame(header, bg=BG)
title_frame.pack(side="left")

logo_photo = load_logo_photo()
if logo_photo is not None:
    logo_label = tk.Label(title_frame, image=logo_photo, bg=BG)
    logo_label.image = logo_photo
    logo_label.pack(side="left", padx=(0, 12))

tk.Label(title_frame,
         text="\U0001F6E2  INTELLIGENT ASSET MONITORING & PRED-MAINT ENGINE:",
         font=(MONO, 14, "bold"), bg=BG, fg=TEXT).pack(side="left")
tk.Label(title_frame, text=f" {FLEET_NAME}", font=(MONO, 14, "bold"),
         bg=BG, fg=ACCENT_CYAN).pack(side="left")
tk.Label(title_frame, text="   \u25cf LIVE MONITORING", font=(MONO, 9, "bold"),
         bg=BG, fg=GREEN).pack(side="left", padx=(10, 0), pady=(3, 0))

clock_label = tk.Label(header, text="", font=(MONO, 10), bg=BG, fg=MUTED)
clock_label.pack(side="right")


def tick_clock():
    clock_label.config(text=datetime.now().strftime("%Y-%m-%d  |  %H:%M:%S"))
    window.after(1000, tick_clock)


# ------------------------------------------------------------
# High-risk alert banner (hidden until a well crosses threshold)
# ------------------------------------------------------------
alert_banner = tk.Frame(root, bg=BG_HIGH, highlightbackground=RED,
                        highlightthickness=1)
alert_banner.grid(row=1, column=0, columnspan=3, sticky="ew", pady=(0, 8))

alert_banner_label = tk.Label(alert_banner, text="", font=(SANS, 10, "bold"),
                              bg=BG_HIGH, fg=RED, anchor="w", padx=14, pady=8)
alert_banner_label.pack(side="left", fill="x", expand=True)

alert_dismiss_button = tk.Button(
    alert_banner, text="Dismiss", font=(SANS, 8, "bold"), bg=BG_HIGH, fg=RED,
    bd=0, relief="flat", activebackground=RED, activeforeground="#04121A",
    cursor="hand2", command=dismiss_alert_banner)
alert_dismiss_button.pack(side="right", padx=10)

alert_banner.grid_remove()


# ------------------------------------------------------------
# Control strip
# ------------------------------------------------------------
control_card = dark_card(root)
control_card.grid(row=2, column=0, columnspan=3, sticky="ew", pady=(0, 8))

control_inner = tk.Frame(control_card, bg=PANEL_BG)
control_inner.pack(fill="x", padx=14, pady=8)

selected_well_label = tk.Label(control_inner, text=f"Selected: {well_var.get()}",
                               font=(MONO, 10, "bold"), bg=PANEL_BG, fg=ACCENT_CYAN)
selected_well_label.pack(side="left")

ttk.Button(control_inner, text="Run Diagnostics", command=run_diagnostics,
           style="Modern.TButton").pack(side="left", padx=(16, 0))

ttk.Checkbutton(control_inner, text="Auto-Monitor All Wells",
                variable=auto_monitor_var, command=toggle_auto_monitor,
                style="Alert.TCheckbutton").pack(side="left", padx=(16, 0))

tk.Label(control_inner, text="Period:", font=(MONO, 9, "bold"), bg=PANEL_BG,
         fg=MUTED).pack(side="left", padx=(24, 6))

for days, label in [(7, "7 Days"), (15, "15 Days"), (30, "30 Days")]:
    button = tk.Button(control_inner, text=label, font=(SANS, 8, "bold"),
                       bg=UNSELECTED_BTN_BG, fg=TEXT, bd=0, relief="flat",
                       cursor="hand2", padx=10, pady=5,
                       command=lambda value=days: select_period(value))
    button.pack(side="left", padx=2)
    period_buttons[days] = button

threshold_label = tk.Label(control_inner, text=f"{threshold_var.get():.0f}%",
                           font=(MONO, 12, "bold"), bg=PANEL_BG, fg=ACCENT_CYAN,
                           width=5)
threshold_label.pack(side="right")

tk.Scale(control_inner, from_=0, to=100, orient="horizontal",
         variable=threshold_var, command=update_threshold, showvalue=False,
         resolution=1, length=160, bg=PANEL_BG, fg=TEXT, troughcolor=GRID,
         activebackground=ACCENT_CYAN, highlightthickness=0, bd=0
         ).pack(side="right", padx=(0, 10))

tk.Label(control_inner, text="Alert Threshold:", font=(MONO, 9, "bold"),
         bg=PANEL_BG, fg=MUTED).pack(side="right", padx=(0, 8))


# ------------------------------------------------------------
# ROW 3: Asset List | ML Failure Forecast | Multi-Phase Production
# ------------------------------------------------------------

# --- Interactive Asset List ---
asset_card = dark_card(root)
asset_card.grid(row=3, column=0, sticky="nsew", padx=(0, 6), pady=(0, 6))
panel_header(asset_card, "INTERACTIVE ASSET LIST")

for well in WELLS:
    row_frame = tk.Frame(asset_card, bg=PANEL_BG, highlightbackground=PANEL_BORDER,
                         highlightthickness=1)
    row_frame.pack(fill="x", padx=10, pady=4)

    name_label = tk.Label(row_frame, text=f"ASSET: {well}", font=(MONO, 9, "bold"),
                          bg=PANEL_BG, fg=TEXT, anchor="w")
    name_label.pack(fill="x", padx=8, pady=(6, 0))

    status_label = tk.Label(row_frame, text="", font=(MONO, 8), bg=PANEL_BG,
                            fg=MUTED, anchor="w")
    status_label.pack(fill="x", padx=8, pady=(0, 6))

    for widget in (row_frame, name_label, status_label):
        widget.bind("<Button-1>", lambda e, w=well: select_well(w))
        widget.config(cursor="hand2")

    asset_rows[well] = {"frame": row_frame, "name_label": name_label,
                        "status": status_label}


# --- ML Failure Forecast Engine ---
forecast_card = dark_card(root)
forecast_card.grid(row=3, column=1, sticky="nsew", padx=6, pady=(0, 6))
panel_header(forecast_card, "ML FAILURE FORECAST ENGINE",
             "Machine-learning failure model (predict.py)" if ML_ACTIVE
             else "Rule-based estimate -- run train_model.py to enable the ML model")

forecast_callout = tk.Frame(forecast_card, bg=PANEL_BG, highlightbackground=PANEL_BORDER,
                            highlightthickness=2)
forecast_callout.pack(fill="x", padx=12, pady=(4, 4))

callout_icon = tk.Label(forecast_callout, text="\u26a0", font=(SANS, 22, "bold"),
                        bg=PANEL_BG, fg=MUTED, padx=12)
callout_icon.pack(side="left")

callout_text = tk.Frame(forecast_callout, bg=PANEL_BG)
callout_text.pack(side="left", fill="x", expand=True, pady=8)

forecast_line1 = tk.Label(callout_text, text="", font=(MONO, 12, "bold"),
                          bg=PANEL_BG, fg=TEXT, anchor="w")
forecast_line1.pack(anchor="w")
forecast_line2 = tk.Label(callout_text, text="", font=(MONO, 10),
                          bg=PANEL_BG, fg=MUTED, anchor="w")
forecast_line2.pack(anchor="w")


def sync_callout_icon():
    callout_icon.config(bg=forecast_callout.cget("bg"), fg=forecast_line1.cget("fg"))
    callout_text.config(bg=forecast_callout.cget("bg"))


tele_figure, tele_ax, tele_canvas = make_chart(
    forecast_card, (7, 3), fill="both", expand=True, padx=10, pady=(2, 8))


# --- Multi-Phase Production Ratio ---
kpi_card = dark_card(root)
kpi_card.grid(row=3, column=2, sticky="nsew", padx=(6, 0), pady=(0, 6))
panel_header(kpi_card, "MULTI-PHASE PRODUCTION RATIO", "Latest recorded values")

for key, column, unit, colour, fmt in KPI_SPECS:
    build_kpi_tile(kpi_card, key, column, unit, colour)


# ------------------------------------------------------------
# ROW 4: Pump Diagnostics | Electrical Driver | Wellhead Mechanics
# ------------------------------------------------------------

# --- Pump Diagnostics ---
pump_card = dark_card(root)
pump_card.grid(row=4, column=0, sticky="nsew", padx=(0, 6), pady=(6, 0))
pump_header = panel_header(pump_card, "PUMP DIAGNOSTICS", "Acoustic vibration spectrum")
tk.Label(pump_header, text="FFT", font=(MONO, 8, "bold"), bg=UNSELECTED_BTN_BG,
         fg=ACCENT_CYAN, padx=8, pady=2).pack(side="right")

fft_figure, fft_ax, fft_canvas = make_chart(
    pump_card, (3.4, 2.2), fill="both", expand=True, padx=8, pady=(2, 8))


# --- Electrical Driver (ESP) ---
esp_card = dark_card(root)
esp_card.grid(row=4, column=1, sticky="nsew", padx=6, pady=(6, 0))
esp_header = panel_header(esp_card, "ELECTRICAL DRIVER (ESP)",
                          "Motor_Current (amperage trace)")
esp_value_label = tk.Label(esp_header, text="--", font=(MONO, 10, "bold"),
                           bg=PANEL_BG, fg=GREEN)
esp_value_label.pack(side="right", padx=4)

esp_figure, esp_ax, esp_canvas = make_chart(
    esp_card, (7, 2.2), fill="both", expand=True, padx=8, pady=(2, 8))


# --- Wellhead Mechanics ---
wellhead_card = dark_card(root)
wellhead_card.grid(row=4, column=2, sticky="nsew", padx=(6, 0), pady=(6, 0))
panel_header(wellhead_card, "WELLHEAD MECHANICS & RISK")

wellhead_body = tk.Frame(wellhead_card, bg=PANEL_BG)
wellhead_body.pack(fill="both", expand=True, padx=8, pady=(0, 4))

gauge_col = tk.Frame(wellhead_body, bg=PANEL_BG)
gauge_col.pack(side="left", fill="y")

gauge_figure, gauge_ax, gauge_canvas = make_chart(
    gauge_col, (2.0, 1.55), fill="x")

choke_col = tk.Frame(wellhead_body, bg=PANEL_BG)
choke_col.pack(side="left", fill="both", expand=True, padx=(10, 0))

tk.Label(choke_col, text="Choke_Position:", font=(MONO, 8), bg=PANEL_BG,
         fg=MUTED).pack(anchor="w")
choke_value_label = tk.Label(choke_col, text="--", font=(MONO, 11, "bold"),
                             bg=PANEL_BG, fg=GREEN)
choke_value_label.pack(anchor="w")

choke_figure, choke_ax, choke_canvas = make_chart(
    choke_col, (1.8, 0.85), fill="x", pady=(2, 4))

tk.Label(choke_col, text="Pump_Status:", font=(MONO, 8), bg=PANEL_BG,
         fg=MUTED).pack(anchor="w")
pump_status_label = tk.Label(choke_col, text="--", font=(MONO, 14, "bold"),
                             bg=PANEL_BG, fg=GREEN)
pump_status_label.pack(anchor="w")

status_message = tk.Label(wellhead_card, text="", font=(MONO, 8, "bold"),
                          bg=PANEL_BG, fg=MUTED, wraplength=330, justify="left",
                          anchor="w")
status_message.pack(fill="x", padx=12, pady=(0, 8))


# ------------------------------------------------------------
# ROW 5: Reports & Notifications
# ------------------------------------------------------------
report_card = dark_card(root)
report_card.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 0))

report_inner = tk.Frame(report_card, bg=PANEL_BG)
report_inner.pack(fill="x", padx=14, pady=9)

report_title_col = tk.Frame(report_inner, bg=PANEL_BG)
report_title_col.pack(side="left")
tk.Label(report_title_col, text="REPORTS & NOTIFICATIONS", font=(MONO, 10, "bold"),
         bg=PANEL_BG, fg=ACCENT_CYAN).pack(anchor="w")
tk.Label(report_title_col, text="Generate reports or send results to stakeholders.",
         font=(MONO, 8), bg=PANEL_BG, fg=MUTED).pack(anchor="w")

ttk.Button(report_inner, text="Technical Report", command=technical_report,
           style="Modern.TButton").pack(side="left", padx=(20, 6))
ttk.Button(report_inner, text="Stakeholder Report", command=stakeholder_report,
           style="Modern.TButton").pack(side="left", padx=(0, 12))

email_entry = tk.Entry(report_inner, font=(SANS, 9), relief="solid", bd=1,
                       bg=PANEL_BG, fg=MUTED, insertbackground=TEXT)
email_entry.pack(side="left", fill="x", expand=True, ipady=5, padx=(0, 7))
email_entry.insert(0, "name@company.com")


def clear_email_placeholder(event):
    if email_entry.get() == "name@company.com":
        email_entry.delete(0, tk.END)
        email_entry.config(fg=TEXT)


def restore_email_placeholder(event):
    if not email_entry.get().strip():
        email_entry.insert(0, "name@company.com")
        email_entry.config(fg=MUTED)


email_entry.bind("<FocusIn>", clear_email_placeholder)
email_entry.bind("<FocusOut>", restore_email_placeholder)

ttk.Button(report_inner, text="Send Report", command=send_report,
           style="Modern.TButton").pack(side="left")


# ------------------------------------------------------------
# Initial display
# ------------------------------------------------------------
update_well_status()
highlight_selected_asset()
update_period_buttons()
reset_risk_gauge()
set_forecast_neutral(well_var.get())
tick_clock()

status_message.config(
    text=f"{well_var.get()} selected. Run diagnostics to assess current risk.",
    fg=MUTED)

# The KPI progress bars need real widget widths, so draw everything
# once the window has laid itself out.
window.after(100, refresh_panels)


def on_close():
    stop_alert_sound()
    window.destroy()


window.protocol("WM_DELETE_WINDOW", on_close)
window.mainloop()