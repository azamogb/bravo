import tkinter as tk
from tkinter import ttk, messagebox

from charts import ChartPanel
from reports import (
    technical_report,
    stakeholder_report,
    save_report_to_file
)


# =========================================================
# Colour Palette
BG = "#F3F1EB"
CARD = "#FFFFFF"
TEXT = "#303030"
MUTED = "#777777"

GREEN = "#20A077"
GREEN_DARK = "#147A5C"
LIGHT_GREEN = "#E8F3DE"

LIGHT_RED = "#F9E8E8"
RED = "#9B3438"

LIGHT_YELLOW = "#FAF0DC"
ORANGE = "#D96A3B"

BORDER = "#D7D5CF"



# Temporary Risk Data
# This will later be replaced by predict.py.

WELL_RISK = {
    "WELL-01": 82,
    "WELL-02": 14,
    "WELL-03": 58,
    "WELL-04": 9,
    "WELL-05": 21
}

# Main Window
window = tk.Tk()

window.title(
    "Digital Oilfield Monitor"
)

window.geometry(
    "1200x850"
)

window.minsize(
    1050,
    750
)

window.configure(
    bg=BG
)

# Tkinter Variables
well_var = tk.StringVar(
    value="WELL-01"
)

current_metric = tk.StringVar(
    value="oil"
)

current_period = tk.IntVar(
    value=7
)

threshold_var = tk.DoubleVar(
    value=75
)

# Widget References
risk_label = None
status_message = None
threshold_label = None
email_entry = None

well_labels = {}
metric_buttons = {}
period_buttons = {}

chart_panel = None

# Styles
style = ttk.Style()

try:
    style.theme_use("clam")
except tk.TclError:
    pass


style.configure(
    "Modern.TButton",
    font=(
        "Segoe UI",
        10,
        "bold"
    ),
    padding=(
        14,
        7
    ),
    background=GREEN,
    foreground="white",
    borderwidth=0
)

style.map(
    "Modern.TButton",
    background=[
        (
            "active",
            GREEN_DARK
        ),
        (
            "pressed",
            GREEN_DARK
        )
    ]
)


style.configure(
    "Modern.TCombobox",
    font=(
        "Segoe UI",
        10
    ),
    padding=6
)

# Helper Functions
def create_card(parent, **kwargs):
    """
    Creates a reusable dashboard card.
    """

    return tk.Frame(
        parent,
        bg=CARD,
        highlightbackground=BORDER,
        highlightthickness=1,
        **kwargs
    )


def create_section_title(
    parent,
    text,
    row=0,
    column=0
):
    """
    Creates a consistent section heading.
    """

    label = tk.Label(
        parent,
        text=text,
        font=(
            "Segoe UI",
            11,
            "bold"
        ),
        bg=CARD,
        fg=TEXT
    )

    label.grid(
        row=row,
        column=column,
        sticky="w"
    )

    return label


def get_risk_status(risk):
    """
    Determines the risk classification.

    The selected threshold determines the boundary
    between HIGH RISK and WARNING.
    """

    threshold = threshold_var.get()

    if risk >= threshold:
        return (
            "HIGH RISK",
            RED,
            LIGHT_RED
        )

    if risk >= 50:
        return (
            "WARNING",
            ORANGE,
            LIGHT_YELLOW
        )

    return (
        "NORMAL",
        GREEN,
        LIGHT_GREEN
    )

# Well Status
def update_well_status():
    """
    Updates the status cards for all wells.

    Temporary values are currently used.

    Later integration:
        Replace WELL_RISK with results from predict.py.
    """

    for well, label in well_labels.items():

        risk = WELL_RISK[well]

        status, colour, background = (
            get_risk_status(risk)
        )

        label.config(
            text=(
                f"{well}\n"
                f"{risk}%  {status}"
            ),
            fg=colour,
            bg=background
        )


def update_selected_well():
    """
    Changes the selected well context.

    Selecting a well does not automatically run
    diagnostics.
    """

    well = well_var.get()

    risk_label.config(
        text="--",
        fg=MUTED
    )

    status_message.config(
        text=(
            f"{well} selected. "
            "Run diagnostics to assess current risk."
        ),
        fg=MUTED
    )


# Diagnostics
def run_diagnostics():
    """
    Runs predictive maintenance diagnostics.

    Temporary risk values are currently used.

    Later integration:
        Replace WELL_RISK lookup with:

        predict_failure_risk(well)

    from predict.py.
    """

    well = well_var.get()

    risk = WELL_RISK.get(
        well,
        0
    )

    status, colour, background = (
        get_risk_status(risk)
    )

    risk_label.config(
        text=f"{risk}%",
        fg=colour
    )

    status_message.config(
        text=(
            f"Diagnostic result for "
            f"{well}: {status}."
        ),
        fg=colour
    )

    chart_panel.plot_risk_trend(
        well,
        risk
    )


# =========================================================
# Metric Selection
# =========================================================

def select_metric(metric):
    """
    Changes the selected performance metric.
    """

    current_metric.set(metric)

    update_metric_buttons()

    chart_panel.plot_performance(
        metric,
        current_period.get()
    )


def update_metric_buttons():
    """
    Updates the visual state of metric buttons.
    """

    for metric, button in metric_buttons.items():

        if metric == current_metric.get():

            button.config(
                bg=GREEN,
                fg="white"
            )

        else:

            button.config(
                bg="#F4F3EF",
                fg=TEXT
            )


# Period Selection
def select_period(days):
    """
    Changes the performance trend period.
    """

    current_period.set(days)

    update_period_buttons()

    chart_panel.plot_performance(
        current_metric.get(),
        days
    )


def update_period_buttons():
    """
    Updates the visual state of the period buttons.
    """

    for days, button in period_buttons.items():

        if days == current_period.get():

            button.config(
                bg=GREEN,
                fg="white"
            )

        else:

            button.config(
                bg="#F4F3EF",
                fg=TEXT
            )


# Threshold
def update_threshold(value):
    """
    Updates the displayed threshold.

    Changing the threshold does not automatically
    run diagnostics.
    """

    threshold = float(value)

    threshold_var.set(
        threshold
    )

    threshold_label.config(
        text=f"{threshold:.0f}%"
    )

    update_well_status()

# Reports
def show_technical_report():
    """
    Generates and displays the technical report.
    """

    well = well_var.get()

    try:
        report = technical_report()

    except Exception as error:
        messagebox.showerror(
            "Report Error",
            (
                "The technical report could not "
                "be generated yet.\n\n"
                f"{error}"
            )
        )
        return

    show_report_window(
        "Technical Report",
        report
    )


def show_stakeholder_report():
    """
    Generates and displays the stakeholder report.
    """

    well = well_var.get()

    try:
        report = stakeholder_report()

    except Exception as error:
        messagebox.showerror(
            "Report Error",
            (
                "The stakeholder report could "
                "not be generated yet.\n\n"
                f"{error}"
            )
        )
        return

    show_report_window(
        "Stakeholder Report",
        report
    )


def show_report_window(title, report):
    """
    Displays a generated report in a separate
    text window.
    """

    report_window = tk.Toplevel(
        window
    )

    report_window.title(
        title
    )

    report_window.geometry(
        "750x500"
    )

    report_window.configure(
        bg=BG
    )

    text = tk.Text(
        report_window,
        font=(
            "Consolas",
            10
        ),
        bg=CARD,
        fg=TEXT,
        wrap="none",
        padx=15,
        pady=15
    )

    text.pack(
        fill="both",
        expand=True,
        padx=15,
        pady=15
    )

    text.insert(
        "1.0",
        report
    )

    text.config(
        state="disabled"
    )


def save_current_report():
    """
    Saves a stakeholder report as a .txt file.
    """


    try:
        report = stakeholder_report()

        filename = "Stakeholder_report"

        save_report_to_file(
            report,
            filename
        )

        messagebox.showinfo(
            "Report Saved",
            f"Report saved as:\n{filename}"
        )

    except Exception as error:

        messagebox.showerror(
            "Report Error",
            (
                "The report could not be saved.\n\n"
                f"{error}"
            )
        )


def email_report():
    """
    Placeholder for the SMTP email module.

    This will later call send_email() from emailer.py.
    """

    email = email_entry.get().strip()

    if not email:

        messagebox.showwarning(
            "Email Required",
            "Enter an email address first."
        )

        return

    messagebox.showinfo(
        "Email Module",
        (
            "Email sending will be connected "
            "when emailer.py is integrated."
        )
    )


# =========================================================
# Main Dashboard Layout
# =========================================================

main = tk.Frame(
    window,
    bg=BG
)

main.pack(
    fill="both",
    expand=True,
    padx=18,
    pady=15
)


main.grid_columnconfigure(
    0,
    weight=1
)

main.grid_columnconfigure(
    1,
    weight=1
)

main.grid_rowconfigure(
    2,
    weight=1
)

# Header
header = create_card(
    main
)

header.grid(
    row=0,
    column=0,
    columnspan=2,
    sticky="ew",
    pady=(0, 12)
)

header.grid_columnconfigure(
    0,
    weight=1
)

title_frame = tk.Frame(
    header,
    bg=CARD
)

title_frame.grid(
    row=0,
    column=0,
    sticky="w",
    padx=18,
    pady=12
)

tk.Label(
    title_frame,
    text="Digital Oilfield Monitor",
    font=(
        "Segoe UI",
        20,
        "bold"
    ),
    bg=CARD,
    fg=TEXT
).pack(
    anchor="w"
)

tk.Label(
    title_frame,
    text=(
        "Production Monitoring & "
        "Predictive Maintenance"
    ),
    font=(
        "Segoe UI",
        9
    ),
    bg=CARD,
    fg=MUTED
).pack(
    anchor="w",
    pady=(2, 0)
)


# Well selection
well_frame = tk.Frame(
    header,
    bg=CARD
)

well_frame.grid(
    row=0,
    column=1,
    padx=18,
    pady=12
)

tk.Label(
    well_frame,
    text="Select Well",
    font=(
        "Segoe UI",
        9,
        "bold"
    ),
    bg=CARD,
    fg=MUTED
).grid(
    row=0,
    column=0,
    sticky="w"
)

well_combo = ttk.Combobox(
    well_frame,
    textvariable=well_var,
    values=list(WELL_RISK.keys()),
    state="readonly",
    width=15,
    style="Modern.TCombobox"
)

well_combo.grid(
    row=1,
    column=0,
    pady=(4, 0)
)

well_combo.bind(
    "<<ComboboxSelected>>",
    lambda event: update_selected_well()
)


# Well Status Card
well_status_card = create_card(
    main
)

well_status_card.grid(
    row=1,
    column=0,
    sticky="nsew",
    padx=(0, 6),
    pady=(0, 12)
)

well_status_card.grid_columnconfigure(
    0,
    weight=1
)

create_section_title(
    well_status_card,
    "Well Status"
).grid(
    row=0,
    column=0,
    sticky="w",
    padx=14,
    pady=(12, 8)
)


well_status_frame = tk.Frame(
    well_status_card,
    bg=CARD
)

well_status_frame.grid(
    row=1,
    column=0,
    sticky="ew",
    padx=12,
    pady=(0, 12)
)

for index, well in enumerate(WELL_RISK):

    well_status_frame.grid_columnconfigure(
        index,
        weight=1
    )

    label = tk.Label(
        well_status_frame,
        text="",
        font=(
            "Segoe UI",
            8,
            "bold"
        ),
        justify="center",
        padx=7,
        pady=8
    )

    label.grid(
        row=0,
        column=index,
        sticky="ew",
        padx=3
    )

    well_labels[well] = label



# Diagnostics Card
diagnostics_card = create_card(
    main
)

diagnostics_card.grid(
    row=1,
    column=1,
    sticky="nsew",
    padx=(6, 0),
    pady=(0, 12)
)

diagnostics_card.grid_columnconfigure(
    0,
    weight=1
)

create_section_title(
    diagnostics_card,
    "Predictive Maintenance"
).grid(
    row=0,
    column=0,
    sticky="w",
    padx=14,
    pady=(12, 5)
)


diagnostics_content = tk.Frame(
    diagnostics_card,
    bg=CARD
)

diagnostics_content.grid(
    row=1,
    column=0,
    sticky="ew",
    padx=14,
    pady=(0, 10)
)

diagnostics_content.grid_columnconfigure(
    0,
    weight=1
)


risk_label = tk.Label(
    diagnostics_content,
    text="--",
    font=(
        "Segoe UI",
        24,
        "bold"
    ),
    bg=CARD,
    fg=MUTED
)

risk_label.grid(
    row=0,
    column=0,
    sticky="w"
)


status_message = tk.Label(
    diagnostics_content,
    text=(
        "Select a well and run diagnostics."
    ),
    font=(
        "Segoe UI",
        9
    ),
    bg=CARD,
    fg=MUTED
)

status_message.grid(
    row=1,
    column=0,
    sticky="w",
    pady=(2, 8)
)


diagnostics_button = ttk.Button(
    diagnostics_content,
    text="Run Diagnostics",
    style="Modern.TButton",
    command=run_diagnostics
)

diagnostics_button.grid(
    row=0,
    column=1,
    rowspan=2,
    padx=(20, 0)
)


# Performance Trend Card
performance_card = create_card(
    main
)

performance_card.grid(
    row=2,
    column=0,
    sticky="nsew",
    padx=(0, 6),
    pady=(0, 12)
)

performance_card.grid_rowconfigure(
    1,
    weight=1
)

performance_card.grid_columnconfigure(
    0,
    weight=1
)


performance_header = tk.Frame(
    performance_card,
    bg=CARD
)

performance_header.grid(
    row=0,
    column=0,
    sticky="ew",
    padx=14,
    pady=(10, 5)
)

performance_header.grid_columnconfigure(
    0,
    weight=1
)

create_section_title(
    performance_header,
    "Performance Trend"
).grid(
    row=0,
    column=0,
    sticky="w"
)


period_frame = tk.Frame(
    performance_header,
    bg=CARD
)

period_frame.grid(
    row=0,
    column=1,
    sticky="e"
)


for column, days in enumerate([7, 15, 30]):

    button = tk.Button(
        period_frame,
        text=f"{days}D",
        font=(
            "Segoe UI",
            8,
            "bold"
        ),
        relief="flat",
        borderwidth=0,
        padx=8,
        pady=4,
        command=lambda d=days: select_period(d)
    )

    button.grid(
        row=0,
        column=column,
        padx=2
    )

    period_buttons[days] = button


performance_chart_frame = tk.Frame(
    performance_card,
    bg=CARD
)

performance_chart_frame.grid(
    row=1,
    column=0,
    sticky="nsew",
    padx=10,
    pady=(0, 10)
)


# Risk Assessment Card
risk_card = create_card(
    main
)

risk_card.grid(
    row=2,
    column=1,
    sticky="nsew",
    padx=(6, 0),
    pady=(0, 12)
)

risk_card.grid_rowconfigure(
    1,
    weight=1
)

risk_card.grid_columnconfigure(
    0,
    weight=1
)


create_section_title(
    risk_card,
    "Risk Assessment"
).grid(
    row=0,
    column=0,
    sticky="w",
    padx=14,
    pady=(10, 5)
)


risk_chart_frame = tk.Frame(
    risk_card,
    bg=CARD
)

risk_chart_frame.grid(
    row=1,
    column=0,
    sticky="nsew",
    padx=10,
    pady=(0, 10)
)


# Create Chart Panel
chart_panel = ChartPanel(
    performance_chart_frame,
    risk_parent=risk_chart_frame
)

# Bottom Controls
bottom_frame = tk.Frame(
    main,
    bg=BG
)

bottom_frame.grid(
    row=3,
    column=0,
    columnspan=2,
    sticky="ew"
)

bottom_frame.grid_columnconfigure(
    0,
    weight=1
)

bottom_frame.grid_columnconfigure(
    1,
    weight=1
)

bottom_frame.grid_columnconfigure(
    2,
    weight=1
)

# Alert Threshold Card
threshold_card = create_card(
    bottom_frame
)

threshold_card.grid(
    row=0,
    column=0,
    sticky="nsew",
    padx=(0, 6)
)

create_section_title(
    threshold_card,
    "Alert Threshold"
).grid(
    row=0,
    column=0,
    sticky="w",
    padx=12,
    pady=(9, 2)
)


threshold_label = tk.Label(
    threshold_card,
    text="75%",
    font=(
        "Segoe UI",
        15,
        "bold"
    ),
    bg=CARD,
    fg=RED
)

threshold_label.grid(
    row=0,
    column=1,
    sticky="e",
    padx=12,
    pady=(9, 2)
)


threshold_scale = tk.Scale(
    threshold_card,
    from_=50,
    to=95,
    orient="horizontal",
    variable=threshold_var,
    showvalue=False,
    resolution=1,
    bg=CARD,
    troughcolor="#E7E5DF",
    highlightthickness=0,
    command=update_threshold
)

threshold_scale.grid(
    row=1,
    column=0,
    columnspan=2,
    sticky="ew",
    padx=12,
    pady=(0, 8)
)

threshold_card.grid_columnconfigure(
    0,
    weight=1
)

# Metric Navigation Card
metric_card = create_card(
    bottom_frame
)

metric_card.grid(
    row=0,
    column=1,
    sticky="nsew",
    padx=6
)

create_section_title(
    metric_card,
    "Metrics"
).grid(
    row=0,
    column=0,
    columnspan=4,
    sticky="w",
    padx=12,
    pady=(9, 5)
)


metrics = [
    ("oil", "Oil"),
    ("gas", "Gas"),
    ("pressure", "Pressure"),
    ("water", "Water"),
    ("choke", "Choke"),
    ("vibration", "Vibration"),
    ("motor_current", "Motor")
]


for index, (metric, label) in enumerate(metrics):

    row = 1 + (index // 4)
    column = index % 4

    button = tk.Button(
        metric_card,
        text=label,
        font=(
            "Segoe UI",
            8,
            "bold"
        ),
        relief="flat",
        borderwidth=0,
        padx=7,
        pady=4,
        command=lambda m=metric: select_metric(m)
    )

    button.grid(
        row=row,
        column=column,
        padx=2,
        pady=2
    )

    metric_buttons[metric] = button

# Reports & Notifications Card
reports_card = create_card(
    bottom_frame
)

reports_card.grid(
    row=0,
    column=2,
    sticky="nsew",
    padx=(6, 0)
)

create_section_title(
    reports_card,
    "Reports & Notifications"
).grid(
    row=0,
    column=0,
    columnspan=2,
    sticky="w",
    padx=12,
    pady=(9, 5)
)


report_buttons_frame = tk.Frame(
    reports_card,
    bg=CARD
)

report_buttons_frame.grid(
    row=1,
    column=0,
    columnspan=2,
    sticky="ew",
    padx=10
)


tk.Button(
    report_buttons_frame,
    text="Technical",
    font=(
        "Segoe UI",
        8,
        "bold"
    ),
    relief="flat",
    bg="#F4F3EF",
    fg=TEXT,
    padx=6,
    pady=4,
    command=show_technical_report
).grid(
    row=0,
    column=0,
    padx=2
)


tk.Button(
    report_buttons_frame,
    text="Stakeholder",
    font=(
        "Segoe UI",
        8,
        "bold"
    ),
    relief="flat",
    bg="#F4F3EF",
    fg=TEXT,
    padx=6,
    pady=4,
    command=show_stakeholder_report
).grid(
    row=0,
    column=1,
    padx=2
)


tk.Button(
    report_buttons_frame,
    text="Save",
    font=(
        "Segoe UI",
        8,
        "bold"
    ),
    relief="flat",
    bg="#F4F3EF",
    fg=TEXT,
    padx=6,
    pady=4,
    command=save_current_report
).grid(
    row=0,
    column=2,
    padx=2
)


email_entry = ttk.Entry(
    reports_card,
    width=22
)

email_entry.grid(
    row=2,
    column=0,
    padx=(12, 4),
    pady=(7, 9)
)

email_entry.insert(
    0,
    "Enter email address"
)


ttk.Button(
    reports_card,
    text="Email",
    style="Modern.TButton",
    command=email_report
).grid(
    row=2,
    column=1,
    padx=(4, 12),
    pady=(7, 9)
)

# Initial Dashboard State
update_well_status()
update_metric_buttons()
update_period_buttons()
update_selected_well()


window.mainloop()