import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from sqlalchemy import text, select
from sqlalchemy.orm import Session

from app.db import engine, SessionLocal
from app.models import Category, Account, Transaction

load_dotenv()


def test_db_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        messagebox.showinfo("DB Test", "✅ Connected successfully!")
    except Exception as e:
        messagebox.showerror("DB Test", f"❌ Connection failed:\n{e}")


class AddTransactionDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc):
        super().__init__(master)
        self.title("Add Transaction")
        self.resizable(False, False)
        self.grab_set()  # modal

        pad = {"padx": 8, "pady": 6}
        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0)

        # type
        ttk.Label(frm, text="Type").grid(row=0, column=0, sticky="w", **pad)
        self.var_type = tk.StringVar(value="expense")
        self.cmb_type = ttk.Combobox(frm, textvariable=self.var_type, values=["expense", "income"], state="readonly")
        self.cmb_type.grid(row=0, column=1, **pad)
        self.cmb_type.bind("<<ComboboxSelected>>", lambda e: self._load_categories())

        # date
        ttk.Label(frm, text="Date (YYYY-MM-DD)").grid(row=1, column=0, sticky="w", **pad)
        self.var_date = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(frm, textvariable=self.var_date, width=18).grid(row=1, column=1, **pad)

        # amount
        ttk.Label(frm, text="Amount").grid(row=2, column=0, sticky="w", **pad)
        self.var_amount = tk.StringVar(value="")
        ttk.Entry(frm, textvariable=self.var_amount, width=18).grid(row=2, column=1, **pad)

        # account
        ttk.Label(frm, text="Account").grid(row=3, column=0, sticky="w", **pad)
        self.var_account = tk.StringVar()
        self.cmb_account = ttk.Combobox(frm, textvariable=self.var_account, state="readonly")
        self.cmb_account.grid(row=3, column=1, **pad)

        # category
        ttk.Label(frm, text="Category").grid(row=4, column=0, sticky="w", **pad)
        self.var_category = tk.StringVar()
        self.cmb_category = ttk.Combobox(frm, textvariable=self.var_category, state="readonly")
        self.cmb_category.grid(row=4, column=1, **pad)

        # notes
        ttk.Label(frm, text="Notes (optional)").grid(row=5, column=0, sticky="w", **pad)
        self.txt_notes = ttk.Entry(frm, width=28)
        self.txt_notes.grid(row=5, column=1, **pad)

        # buttons
        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Save", command=self._on_save).grid(row=0, column=1)

        # initial data
        self._load_accounts()
        self._load_categories()

    def _load_accounts(self):
        with SessionLocal() as ses:
            rows = ses.execute(select(Account.id, Account.name).order_by(Account.name)).all()
        names = [name for (_id, name) in rows]
        self._accounts_map = {name: _id for (_id, name) in rows}
        self.cmb_account["values"] = names
        if names:
            self.var_account.set(names[0])

    def _load_categories(self):
        typ = self.var_type.get()
        with SessionLocal() as ses:
            rows = ses.execute(
                select(Category.id, Category.name)
                .where(Category.type == typ)
                .order_by(Category.name)
            ).all()
        names = [name for (_id, name) in rows]
        self._categories_map = {name: _id for (_id, name) in rows}
        self.cmb_category["values"] = names
        if names:
            self.var_category.set(names[0])
        else:
            self.var_category.set("")

    def _on_save(self):
        # validations
        try:
            amt = Decimal(self.var_amount.get())
            if amt < 0:
                raise InvalidOperation
        except Exception:
            messagebox.showerror("Validation", "Amount must be a positive number.")
            return

        try:
            tx_date = datetime.strptime(self.var_date.get(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Validation", "Date must be in format YYYY-MM-DD.")
            return

        typ = self.var_type.get()
        if typ not in ("income", "expense"):
            messagebox.showerror("Validation", "Type must be 'income' or 'expense'.")
            return

        acc_name = self.var_account.get()
        cat_name = self.var_category.get()
        if not acc_name or acc_name not in self._accounts_map:
            messagebox.showerror("Validation", "Please select an account.")
            return
        if not cat_name or cat_name not in self._categories_map:
            messagebox.showerror("Validation", "Please select a category.")
            return

        notes = self.txt_notes.get().strip() or None

        # insert
        try:
            with SessionLocal() as ses:
                tx = Transaction(
                    date=tx_date,
                    amount=amt,
                    type=typ,
                    account_id=self._accounts_map[acc_name],
                    category_id=self._categories_map[cat_name],
                    notes=notes,
                )
                ses.add(tx)
                ses.commit()
            messagebox.showinfo("Success", "✅ Transaction saved!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("DB Error", f"Could not save transaction:\n{e}")


def run():
    root = tk.Tk()
    root.title("Finance Tracker")
    root.geometry("560x260")
    root.resizable(False, False)

    container = ttk.Frame(root, padding=16)
    container.pack(fill="both", expand=True)

    title = ttk.Label(container, text="Personal Finance Tracker", font=("Segoe UI", 14, "bold"))
    title.pack(anchor="w")

    subtitle = ttk.Label(container, text="MVP with DB connection and add transaction dialog.", font=("Segoe UI", 10))
    subtitle.pack(anchor="w", pady=(4, 16))

    row = ttk.Frame(container)
    row.pack(fill="x", pady=(8, 0))

    ttk.Button(row, text="Test DB", command=test_db_connection).pack(side="left")
    ttk.Button(row, text="Add Transaction…", command=lambda: AddTransactionDialog(root)).pack(side="left", padx=8)
    ttk.Button(row, text="Exit", command=root.destroy).pack(side="right")

    status = ttk.Label(container, text=f"Connected URL: {os.getenv('DATABASE_URL','(not set)')}", anchor="w", relief="groove")
    status.pack(fill="x", pady=(16, 0))

    root.mainloop()


if __name__ == "__main__":
    run()


