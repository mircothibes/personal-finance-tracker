import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import matplotlib
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sqlalchemy import select, extract, func

from app.db import SessionLocal
from app.models import Transaction, Category

matplotlib.use("Agg")  # prevent backend issues on WSL/Ubuntu


def open_dashboard(master: tk.Misc):
    """Open dashboard window with charts and summary."""
    win = tk.Toplevel(master)
    win.title("Finance Dashboard")
    win.geometry("920x600")
    win.grab_set()

    ttk.Label(
        win,
        text="📊 Finance Dashboard",
        font=("Segoe UI", 14, "bold")
    ).pack(anchor="w", padx=16, pady=(10, 0))

    ttk.Separator(win).pack(fill="x", pady=8)

    try:
        with SessionLocal() as s:
            # ---- totals ----
            total_income = s.scalar(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.type == "income")
            )
            total_expense = s.scalar(
                select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.type == "expense")
            )
            net_balance = total_income - total_expense

            # ---- expense by category ----
            cat_rows = s.execute(
                select(Category.name, func.sum(Transaction.amount))
                .join(Transaction, Transaction.category_id == Category.id)
                .where(Transaction.type == "expense")
                .group_by(Category.name)
                .order_by(func.sum(Transaction.amount).desc())
            ).all()

            # ---- monthly totals ----
            month_rows = s.execute(
                select(
                    extract("month", Transaction.date),
                    Transaction.type,
                    func.sum(Transaction.amount),
                )
                .group_by(extract("month", Transaction.date), Transaction.type)
                .order_by(extract("month", Transaction.date))
            ).all()
    except Exception as e:
        messagebox.showerror("Error", f"Database error:\n{e}")
        win.destroy()
        return

    # ---------- summary ----------
    summary_frame = ttk.Frame(win, padding=10)
    summary_frame.pack(fill="x")

    ttk.Label(summary_frame, text=f"Total Income: {total_income:.2f} €", foreground="green").pack(anchor="w")
    ttk.Label(summary_frame, text=f"Total Expense: {total_expense:.2f} €", foreground="red").pack(anchor="w")
    ttk.Label(summary_frame, text=f"Net Balance: {net_balance:.2f} €", foreground="blue").pack(anchor="w")

    ttk.Separator(win).pack(fill="x", pady=8)

    # ---------- charts frame ----------
    charts = ttk.Frame(win)
    charts.pack(fill="both", expand=True, padx=10, pady=10)

    # --- Pie Chart: Expenses by Category ---
    fig1 = Figure(figsize=(4.5, 3.5), dpi=100)
    ax1 = fig1.add_subplot(111)
    if cat_rows:
        labels, values = zip(*cat_rows)
        ax1.pie(values, labels=labels, autopct="%1.1f%%", startangle=140)
        ax1.set_title("Expenses by Category")
    else:
        ax1.text(0.5, 0.5, "No expenses yet", ha="center", va="center")

    canvas1 = FigureCanvasTkAgg(fig1, master=charts)
    canvas1.draw()
    canvas1.get_tk_widget().grid(row=0, column=0, padx=8, pady=8)

    # --- Bar Chart: Monthly Income vs Expense ---
    months = sorted(set(int(m) for m, _, _ in month_rows))
    income_data = {int(m): float(v) for m, t, v in month_rows if t == "income"}
    expense_data = {int(m): float(v) for m, t, v in month_rows if t == "expense"}

    fig2 = Figure(figsize=(4.5, 3.5), dpi=100)
    ax2 = fig2.add_subplot(111)

    if months:
        incomes = [income_data.get(m, 0) for m in months]
        expenses = [expense_data.get(m, 0) for m in months]
        month_labels = [datetime(2024, m, 1).strftime("%b") for m in months]

        x = range(len(months))
        ax2.bar(x, incomes, width=0.4, label="Income", align="center")
        ax2.bar([i + 0.4 for i in x], expenses, width=0.4, label="Expense", align="center")
        ax2.set_xticks([i + 0.2 for i in x])
        ax2.set_xticklabels(month_labels)
        ax2.set_title("Monthly Income vs Expense")
        ax2.legend()
    else:
        ax2.text(0.5, 0.5, "No data yet", ha="center", va="center")

    canvas2 = FigureCanvasTkAgg(fig2, master=charts)
    canvas2.draw()
    canvas2.get_tk_widget().grid(row=0, column=1, padx=8, pady=8)

    ttk.Button(win, text="Close", command=win.destroy).pack(pady=(10, 12))

