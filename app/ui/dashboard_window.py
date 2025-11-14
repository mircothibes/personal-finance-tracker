# app/ui/dashboard_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from collections import defaultdict

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app.db import SessionLocal, get_transactions
from app.models import Transaction


def _load_aggregates():
    """
    Load simple aggregates from the database:
    - total income
    - total expense
    - net
    - monthly sums for the last 12 months
    """
    today = date.today()
    year_ago = date(today.year - 1, today.month, 1)

    with SessionLocal() as s:
        rows = get_transactions(s, date_from=year_ago, date_to=today)

    total_income = 0.0
    total_expense = 0.0

    # key: "YYYY-MM" -> value: net (income - expense)
    monthly = defaultdict(float)

    for tx in rows:
        amt = float(tx.amount)
        ym = tx.date.strftime("%Y-%m")

        if tx.type == "income":
            total_income += amt
            monthly[ym] += amt
        else:
            total_expense += amt
            monthly[ym] -= amt

    net = total_income - total_expense

    # Sort months chronologically
    sorted_months = sorted(monthly.keys())
    x_labels = sorted_months
    y_values = [monthly[m] for m in sorted_months]

    return total_income, total_expense, net, x_labels, y_values


def open_dashboard(master: tk.Misc) -> None:
    """
    Open a simple dashboard window with totals and a bar chart.
    """
    try:
        total_income, total_expense, net, x_labels, y_values = _load_aggregates()
    except Exception as e:
        messagebox.showerror("Dashboard", f"Could not load data:\n{e}")
        return

    win = tk.Toplevel(master)
    win.title("Finance Dashboard")
    win.geometry("900x600")
    win.resizable(True, True)

    # Make window appear nicely over the main window
    win.transient(master)  # type: ignore[arg-type]
    win.lift()
    win.focus_force()

    container = ttk.Frame(win, padding=16)
    container.pack(fill="both", expand=True)

    ttk.Label(
        container,
        text="Dashboard",
        font=("Segoe UI", 14, "bold")
    ).pack(anchor="w")

    ttk.Label(
        container,
        text="Summary of incomes and expenses (last 12 months).",
        font=("Segoe UI", 10)
    ).pack(anchor="w", pady=(4, 12))

    # --- summary cards -------------------------------------------------------
    summary = ttk.Frame(container)
    summary.pack(fill="x", pady=(0, 12))

    def card(parent, title, value):
        frame = ttk.LabelFrame(parent, text=title, padding=8)
        frame.pack(side="left", padx=8, fill="x", expand=True)
        ttk.Label(
            frame,
            text=f"{value:,.2f}",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="center")

    card(summary, "Total Income", total_income)
    card(summary, "Total Expense", total_expense)
    card(summary, "Net", net)

    # --- matplotlib figure ---------------------------------------------------
    fig = Figure(figsize=(7, 4))
    ax = fig.add_subplot(111)

    if x_labels:
        ax.bar(x_labels, y_values)
        ax.set_title("Net by month")
        ax.set_xlabel("Month")
        ax.set_ylabel("Net amount")
        ax.tick_params(axis="x", rotation=45)
    else:
        ax.text(0.5, 0.5, "No data to display", ha="center", va="center")

    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=container)
    canvas.draw()
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill="both", expand=True)

    # Close button
    ttk.Button(container, text="Close", command=win.destroy).pack(pady=(8, 0))

