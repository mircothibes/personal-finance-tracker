import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from sqlalchemy import text, select

from app.db import engine, SessionLocal, get_transactions, delete_transaction
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


# ---------------------
# Filters / lookups
# ---------------------
def _load_filter_options(cb_category: ttk.Combobox, cb_account: ttk.Combobox):
    """Load Category and Account names into comboboxes (with empty option)."""
    with SessionLocal() as s:
        cats = [r[0] for r in s.execute(select(Category.name).order_by(Category.name)).all()]
        accs = [r[0] for r in s.execute(select(Account.name).order_by(Account.name)).all()]
    cb_category["values"] = [""] + cats
    cb_account["values"] = [""] + accs
    cb_category.set("")
    cb_account.set("")


def _resolve_category_id(name: str | None):
    if not name:
        return None
    with SessionLocal() as s:
        row = s.execute(select(Category.id).where(Category.name == name)).first()
        return row[0] if row else None


def _resolve_account_id(name: str | None):
    if not name:
        return None
    with SessionLocal() as s:
        row = s.execute(select(Account.id).where(Account.name == name)).first()
        return row[0] if row else None


def clear_filters_and_refresh(tree, cb_type, cb_category, cb_account):
    cb_type.set("")
    cb_category.set("")
    cb_account.set("")
    refresh_table(tree, cb_type, cb_category, cb_account)


def delete_selected(tree, cb_type, cb_category, cb_account):
    """Delete selected transaction and refresh keeping filters."""
    sel = tree.selection()
    if not sel:
        messagebox.showinfo("Delete", "No transaction selected.")
        return

    tx_id = int(tree.item(sel[0], "values")[0])
    if not messagebox.askyesno("Confirm", f"Delete transaction ID {tx_id}?"):
        return

    with SessionLocal() as s:
        ok = delete_transaction(s, tx_id)

    if ok:
        messagebox.showinfo("Delete", f"✅ Transaction {tx_id} deleted.")
        refresh_table(tree, cb_type, cb_category, cb_account)
    else:
        messagebox.showerror("Delete", f"❌ Could not delete ID {tx_id}.")


def refresh_table(tree, cb_type=None, cb_category=None, cb_account=None):
    """Load transactions into the Treeview applying filters (type/category/account)."""
    # clear table
    for item in tree.get_children():
        tree.delete(item)

    # read filters
    tx_type = cb_type.get().strip() or None if cb_type else None
    cat_id = _resolve_category_id(cb_category.get().strip()) if cb_category and cb_category.get().strip() else None
    acc_id = _resolve_account_id(cb_account.get().strip()) if cb_account and cb_account.get().strip() else None

    with SessionLocal() as s:
        # maps id -> name for pretty display
        acc_map = dict(s.execute(select(Account.id, Account.name)).all())
        cat_map = dict(s.execute(select(Category.id, Category.name)).all())

        rows = get_transactions(
            s,
            tx_type=tx_type,
            category_id=cat_id,
            account_id=acc_id,
        )

    for r in rows:
        account_name = acc_map.get(getattr(r, "account_id", None), "")
        category_name = cat_map.get(getattr(r, "category_id", None), "")
        tree.insert(
            "",
            "end",
            values=(
                r.id,
                r.date.isoformat(),
                r.type,
                f"{float(r.amount):.2f}",
                account_name,      # 🔹 nome em vez de id
                category_name,     # 🔹 nome em vez de id
                (r.notes or "")[:80],
            ),
        )

    with SessionLocal() as s:
        rows = get_transactions(
            s,
            tx_type=tx_type,
            category_id=cat_id,
            account_id=acc_id,
        )

    for r in rows:
        tree.insert(
            "",
            "end",
            values=(
                r.id,
                r.date.isoformat(),
                r.type,
                f"{r.amount:.2f}",
                r.account_id,
                r.category_id,
                (r.notes or "")[:80],
            ),
        )


def open_add_transaction(root, tree, cb_type, cb_category, cb_account):
    """Open the modal and refresh the table after it closes."""
    dlg = AddTransactionDialog(root)
    root.wait_window(dlg)  # wait until modal is closed
    refresh_table(tree, cb_type, cb_category, cb_account)


def run():
    root = tk.Tk()
    root.title("Finance Tracker")
    root.geometry("900x600")
    root.resizable(True, True)

    container = ttk.Frame(root, padding=16)
    container.pack(fill="both", expand=True)

    title = ttk.Label(container, text="Personal Finance Tracker", font=("Segoe UI", 14, "bold"))
    title.pack(anchor="w")

    subtitle = ttk.Label(container, text="MVP with DB connection and add transaction dialog.", font=("Segoe UI", 10))
    subtitle.pack(anchor="w", pady=(4, 16))

    row = ttk.Frame(container)
    row.pack(fill="x", pady=(8, 0))

    ttk.Button(row, text="Test DB", command=test_db_connection).pack(side="left")

    # Add Transaction now refreshes the table after closing the modal
    ttk.Button(
        row,
        text="Add Transaction…",
        command=lambda: open_add_transaction(root, tree, cb_type, cb_category, cb_account)
    ).pack(side="left", padx=8)

    ttk.Button(row, text="Exit", command=root.destroy).pack(side="right")

    # --- Filters + Table Section ---
    filters = ttk.Frame(container)
    filters.pack(fill="x", pady=(16, 4))

    ttk.Label(filters, text="Type").pack(side="left", padx=(0, 4))
    cb_type = ttk.Combobox(filters, values=["", "expense", "income"], width=10, state="readonly")
    cb_type.pack(side="left", padx=(0, 12))

    ttk.Label(filters, text="Category").pack(side="left")
    cb_category = ttk.Combobox(filters, width=18, state="readonly")
    cb_category.pack(side="left", padx=(4, 12))

    ttk.Label(filters, text="Account").pack(side="left")
    cb_account = ttk.Combobox(filters, width=18, state="readonly")
    cb_account.pack(side="left", padx=(4, 12))

    cb_type = ttk.Combobox(filters, values=["", "expense", "income"], width=10, state="readonly")
    cb_type.pack(side="left", padx=(0, 12))
    cb_type.set("")  

    # load options into filters
    _load_filter_options(cb_category, cb_account)

    ttk.Button(
        filters,
        text="Apply",
        command=lambda: refresh_table(tree, cb_type, cb_category, cb_account)
    ).pack(side="left", padx=(4, 4))

    ttk.Button(
        filters,
        text="Clear",
        command=lambda: clear_filters_and_refresh(tree, cb_type, cb_category, cb_account)
    ).pack(side="left")

    # allow Enter to apply filters
    for w in (cb_type, cb_category, cb_account):
        w.bind("<Return>", lambda e: refresh_table(tree, cb_type, cb_category, cb_account))

    # --- Transactions Table ---
    table_frame = ttk.Frame(container)
    table_frame.pack(fill="both", expand=True, pady=(4, 8))

    columns = ("id", "date", "type", "amount", "account_id", "category_id", "notes")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)
    for col in columns:
        tree.heading(col, text=col.title())
        tree.column(col, anchor="center", width=100)
    tree.column("notes", width=240, anchor="w")
    tree.pack(side="left", fill="both", expand=True)

    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscroll=scrollbar.set)

    # --- Delete Button (keeps filters) ---
    ttk.Button(
        container,
        text="Delete Selected",
        command=lambda: delete_selected(tree, cb_type, cb_category, cb_account)
    ).pack(pady=(0, 10))

    # --- Status Bar ---
    status = ttk.Label(container, text=f"Connected URL: {os.getenv('DATABASE_URL','(not set)')}",
                       anchor="w", relief="groove")
    status.pack(fill="x", pady=(8, 0))

    # Load initial data
    refresh_table(tree, cb_type, cb_category, cb_account)

    # MAIN LOOP
    root.mainloop()


if __name__ == "__main__":
    run()


















