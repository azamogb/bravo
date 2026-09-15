import tkinter as tk
import random

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


# Dashboard colours
CARD = "#FFFFFF"
TEXT = "#303030"
MUTED = "#777777"
GREEN = "#20A077"
GRAPH_GRID = "#E5E3DD"


# Temporary data for GUI testing.
# This will later be replaced with data from data_loader.py.

METRICS = {
    "oil": {
        "label": "Oil Rate",
        "title": "Oil Production",
        "unit": "bbl/day",
        "data": [100, 120, 115, 140, 135, 145, 132]
    },

    "gas": {
        "label": "Gas Rate",
        "title": "Gas Production",
        "unit": "MMscf/day",
        "data": [50, 65, 60, 75, 80, 78, 85]
    },

    "pressure": {
        "label": "Pressure",
        "title": "Well Pressure",
        "unit": "psi",
        "data": [70, 75, 72, 78, 80, 77, 82]
    },

    "water": {
        "label": "Water Cut",
        "title": "Water Cut",
        "unit": "%",
        "data": [20, 25, 23, 30, 28, 32, 29]
    },

    "choke": {
        "label": "Choke Position",
        "title": "Choke Position",
        "unit": "%",
        "data": [45, 50, 48, 55, 60, 58, 63]
    },

    "vibration": {
        "label": "Vibration",
        "title": "Equipment Vibration",
        "unit": "mm/s",
        "data": [2.1, 2.5, 2.3, 3.1, 3.5, 3.2, 3.8]
    },

    "motor_current": {
        "label": "Motor Current",
        "title": "Motor Current",
        "unit": "A",
        "data": [18, 21, 20, 24, 27, 26, 29]
    }
}


class ChartPanel(tk.Frame):
    """
    Handles all Matplotlib charts used by the dashboard.

    The figures and canvases are created once and then
    updated whenever the selected metric or period changes.
    """

    def __init__(self, parent, risk_parent=None):
        super().__init__(
            parent,
            bg=CARD
        )

        self.current_metric = "oil"
        self.current_period = 7

        # Performance Trend Chart
        self.fig = Figure(
            figsize=(7.5, 3.1),
            dpi=100,
            facecolor=CARD
        )

        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(
            self.fig,
            master=self
        )

        self.canvas_widget = self.canvas.get_tk_widget()

        self.canvas_widget.configure(
            bg=CARD,
            highlightthickness=0
        )

        self.canvas_widget.pack(
            fill="both",
            expand=True
        )

        # Risk Assessment Chart
        self.risk_frame = None
        self.risk_fig = None
        self.risk_ax = None
        self.risk_canvas = None

        if risk_parent is not None:
            self.create_risk_chart(risk_parent)

        self.plot_performance(
            self.current_metric,
            self.current_period
        )

    # Performance Chart
    def plot_performance(self, metric, days):
        """
        Updates the performance trend chart.

        Temporary data is expanded or reduced to match
        the selected number of days.
        """

        self.current_metric = metric
        self.current_period = days

        metric_info = METRICS[metric]

        base_data = metric_info["data"]

        data = self.generate_period_data(
            base_data,
            days
        )

        self.ax.clear()

        x_values = list(range(1, days + 1))

        self.ax.plot(
            x_values,
            data,
            linewidth=2.5,
            marker="o",
            markersize=4
        )

        self.ax.set_title(
            metric_info["title"],
            fontsize=11,
            fontweight="bold",
            color=TEXT,
            pad=10
        )

        self.ax.set_ylabel(
            metric_info["unit"],
            fontsize=9,
            color=MUTED
        )

        self.ax.set_xlabel(
            "Day",
            fontsize=9,
            color=MUTED
        )

        self.ax.tick_params(
            axis="both",
            labelsize=8,
            colors=MUTED
        )

        self.ax.grid(
            True,
            axis="y",
            color=GRAPH_GRID,
            linewidth=0.8
        )

        self.ax.set_facecolor(CARD)

        for spine in self.ax.spines.values():
            spine.set_color(GRAPH_GRID)

        self.fig.tight_layout()

        self.canvas.draw()

    
    # Temporary Performance Data
    @staticmethod
    def generate_period_data(base_data, days):
        """
        Generates temporary chart data for 7, 15 and 30 days.

        This function exists only for GUI testing.
        It can later be replaced with actual database values.
        """

        if days <= len(base_data):
            return base_data[-days:]

        data = list(base_data)

        while len(data) < days:
            previous = data[-1]

            variation = random.uniform(
                -0.06,
                0.06
            )

            next_value = previous * (
                1 + variation
            )

            data.append(
                round(next_value, 2)
            )

        return data

    # Risk Chart Creation
    def create_risk_chart(self, parent):
        """
        Creates the risk assessment chart once.

        The chart is subsequently updated rather than
        creating a new Figure every time diagnostics run.
        """

        self.risk_frame = parent

        self.risk_fig = Figure(
            figsize=(4.2, 2.4),
            dpi=100,
            facecolor=CARD
        )

        self.risk_ax = self.risk_fig.add_subplot(111)

        self.risk_canvas = FigureCanvasTkAgg(
            self.risk_fig,
            master=parent
        )

        risk_widget = self.risk_canvas.get_tk_widget()

        risk_widget.configure(
            bg=CARD,
            highlightthickness=0
        )

        risk_widget.pack(
            fill="both",
            expand=True
        )

        self.plot_risk_trend(
            "WELL-01",
            82
        )
   
    # Risk Assessment Chart
    def plot_risk_trend(self, well_id, current_risk):
        """
        Updates the risk assessment chart.

        Temporary risk history is generated from the
        supplied current risk value.
        """

        if self.risk_ax is None:
            return

        self.risk_ax.clear()

        history = self.generate_risk_history(
            current_risk
        )

        days = list(
            range(1, len(history) + 1)
        )

        self.risk_ax.plot(
            days,
            history,
            linewidth=2.5,
            marker="o",
            markersize=4
        )

        self.risk_ax.axhline(
            75,
            linestyle="--",
            linewidth=1.5
        )

        self.risk_ax.set_title(
            f"{well_id} Risk Trend",
            fontsize=10,
            fontweight="bold",
            color=TEXT
        )

        self.risk_ax.set_xlabel(
            "Assessment",
            fontsize=8,
            color=MUTED
        )

        self.risk_ax.set_ylabel(
            "Risk (%)",
            fontsize=8,
            color=MUTED
        )

        self.risk_ax.set_ylim(
            0,
            100
        )

        self.risk_ax.tick_params(
            axis="both",
            labelsize=8,
            colors=MUTED
        )

        self.risk_ax.grid(
            True,
            axis="y",
            color=GRAPH_GRID,
            linewidth=0.8
        )

        self.risk_ax.set_facecolor(CARD)

        for spine in self.risk_ax.spines.values():
            spine.set_color(GRAPH_GRID)

        self.risk_fig.tight_layout()

        self.risk_canvas.draw()

    # Temporary Risk History
    @staticmethod
    def generate_risk_history(current_risk):
        """
        Generates temporary risk history for testing.
        """

        history = []

        for index in range(5):
            if index == 4:
                value = current_risk
            else:
                variation = random.randint(
                    -8,
                    8
                )

                value = current_risk + variation

            value = max(
                0,
                min(100, value)
            )

            history.append(value)

        return history