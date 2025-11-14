# app/ui/dashboard_window.py
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from app.db import SessionLocal, get_transactions
from app.models import Category


def _load_aggregates():
    """
    Load aggregates from the database for the last 12 months:
    - total income
    - total expense
    - net
    - expenses grouped by category (for pie chart)
    """
    today = date.today()
    year_ago = date(today.year - 1, today.month, 1)

    with SessionLocal() as s:
        rows = get_transactions(s, date_from=year_ago, date_to=today)

        # Map category_id -> category_name
        cat_rows = s.query(Category.id, Category.name).all()
        cat_map = {cid: cname for cid, cname in cat_rows}

    total_income = 0.0
    total_expense = 0.0

    # expenses by category_id
    expense_by_cat_id: dict[int, float] = {}

    for tx in rows:
        amt = float(tx.amount)

        if tx.type == "income":
            total_income += amt
        else:
            total_expense += amt
            if tx.category_id is not None:
                expense_by_cat_id[tx.category_id] = (
                    expense_by_cat_id.get(tx.category_id, 0.0) + amt
                )

    net = total_income - total_expense

    # Convert to labels/values using category names
    labels: list[str] = []
    values: list[float] = []

    for cid, value in expense_by_cat_id.items():
        name = cat_map.get(cid, f"Category {cid}")
        labels.append(name)
        values.append(value)

    return total_income, total_expense, net, labels, values


def open_dashboard(master: tk.Misc) -> None:
    """
    Open a dashboard window with totals and a pie chart of expenses by category.
    """
    try:
        total_income, total_expense, net, labels, values = _load_aggregates()
    except Exception as e:
        messagebox.showerror("Dashboard", f"Could not load data:\n{e}")
        return

    win = tk.Toplevel(master)
    win.title("Finance Dashboard")
    win.geometry("900x600")
    win.resizable(True, True)

    # Show on top of the main window
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

    # --- matplotlib figure: pie chart ---------------------------------------
    fig = Figure(figsize=(7, 4))
    ax = fig.add_subplot(111)

    if values:
        ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=90,
        )
        ax.set_title("Expenses by category (last 12 months)")
        ax.axis("equal")  # make it look like a circle
    else:
        ax.text(0.5, 0.5, "No expense data to display", ha="center", va="center")
        ax.axis("off")

    fig.tight_layout()

    canvas = FigureCanvasTkAgg(fig, master=container)
    canvas.draw()
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack(fill="both", expand=True)

    # Close button
    ttk.Button(container, text="Close", command=win.destroy).pack(pady=(8, 0))
