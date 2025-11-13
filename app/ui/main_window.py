import os
import csv
import time
import pathlib
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from dotenv import load_dotenv
from sqlalchemy import text, select

from app.ui.dashboard_window import open_dashboard
from app.db import engine, SessionLocal, get_transactions, delete_transaction
from app.models import Category, Account, Transaction

load_dotenv()


# ---------- tiny helpers ----------
def info(t, m): messagebox.showinfo(t, m)
def err(t, m):  messagebox.showerror(t, m)


def test_db_connection():
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        info("DB Test", "✅ Connected successfully!")
    except Exception as e:
        err("DB Test", f"❌ Connection failed:\n{e}")


def id_from_name(model, name: str | None):
    if not name:
        return None
    with SessionLocal() as s:
        row = s.execute(select(model.id).where(model.name == name)).first()
        return row[0] if row else None


def maps(session):
    # id -> name maps
    acc = dict(session.execute(select(Account.id, Account.name)).all())
    cat = dict(session.execute(select(Category.id, Category.name)).all())
    return acc, cat


def load_filter_options(cb_cat: ttk.Combobox, cb_acc: ttk.Combobox):
    with SessionLocal() as s:
        cats = [r[0] for r in s.execute(select(Category.name).order_by(Category.name)).all()]
        accs = [r[0] for r in s.execute(select(Account.name).order_by(Account.name)).all()]
    cb_cat["values"] = [""] + cats
    cb_acc["values"] = [""] + accs
    cb_cat.set("")
    cb_acc.set("")


def parse_date(s: str | None):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


# ---------- dialog (add/edit) ----------
class TransactionDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, tx_id: int | None = None):
        super().__init__(master)
        self.title("Edit Transaction" if tx_id else "Add Transaction")
        self.resizable(False, False)
        self.grab_set()
        self.tx_id = tx_id

        pad = {"padx": 8, "pady": 6}
        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0)

        self.var_type = tk.StringVar(value="expense")
        self.var_date = tk.StringVar(value=date.today().isoformat())
        self.var_amount = tk.StringVar(value="")
        self.var_account = tk.StringVar()
        self.var_category = tk.StringVar()

        def row(label: str, widget: ttk.Widget):
            r = len(frm.grid_slaves()) // 2
            lbl = ttk.Label(frm, text=label)
            lbl.grid(row=r, column=0, sticky="w", padx=pad["padx"], pady=pad["pady"])
            widget.grid(row=r, column=1, padx=pad["padx"], pady=pad["pady"])

        row("Type", ttk.Combobox(frm, textvariable=self.var_type,
                                 values=["expense", "income"], state="readonly"))
        row("Date (YYYY-MM-DD)", ttk.Entry(frm, textvariable=self.var_date, width=18))
        row("Amount", ttk.Entry(frm, textvariable=self.var_amount, width=18))
        self.cmb_account = ttk.Combobox(frm, textvariable=self.var_account, state="readonly")
        row("Account", self.cmb_account)
        self.cmb_category = ttk.Combobox(frm, textvariable=self.var_category, state="readonly")
        row("Category", self.cmb_category)

        ttk.Label(frm, text="Notes (optional)").grid(row=5, column=0, sticky="w", padx=pad["padx"], pady=pad["pady"])
        self.txt_notes = ttk.Entry(frm, width=28)
        self.txt_notes.grid(row=5, column=1, padx=pad["padx"], pady=pad["pady"])

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(btns, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Save", command=self.on_save).grid(row=0, column=1)

        self.var_type.trace_add("write", lambda *_: self.load_categories())
        self.load_accounts()
        self.load_categories()
        if self.tx_id:
            self.load_existing()

        # focus first field
        self.after(50, lambda: self.focus_force())

    def load_accounts(self):
        with SessionLocal() as s:
            rows = s.execute(select(Account.id, Account.name).order_by(Account.name)).all()
        self._acc_map = {name: _id for (_id, name) in rows}
        names = [name for (_id, name) in rows]
        self.cmb_account["values"] = names
        if names:
            self.var_account.set(names[0])

    def load_categories(self):
        typ = self.var_type.get()
        with SessionLocal() as s:
            rows = s.execute(
                select(Category.id, Category.name)
                .where(Category.type == typ)
                .order_by(Category.name)
            ).all()
        self._cat_map = {name: _id for (_id, name) in rows}
        names = [name for (_id, name) in rows]
        self.cmb_category["values"] = names
        self.var_category.set(names[0] if names else "")

    def load_existing(self):
        with SessionLocal() as s:
            tx = s.get(Transaction, self.tx_id)
            if not tx:
                err("Error", f"Transaction {self.tx_id} not found.")
                self.destroy()
                return
            self.var_type.set(tx.type)
            self.var_date.set(tx.date.isoformat())
            self.var_amount.set(str(float(tx.amount)))
            self.load_categories()
            acc = s.execute(select(Account.name).where(Account.id == tx.account_id)).first()
            cat = s.execute(select(Category.name).where(Category.id == tx.category_id)).first()
            if acc:
                self.var_account.set(acc[0])
            if cat:
                self.var_category.set(cat[0])
            self.txt_notes.insert(0, tx.notes or "")

    def on_save(self):
        # --- validations ---
        try:
            amt = Decimal(self.var_amount.get())
            if amt < 0:
                raise InvalidOperation
        except Exception:
            err("Validation", "Amount must be a positive number.")
            return

        try:
            tx_date = datetime.strptime(self.var_date.get(), "%Y-%m-%d").date()
        except ValueError:
            err("Validation", "Date must be in format YYYY-MM-DD.")
            return

        typ = self.var_type.get()
        if typ not in ("income", "expense"):
            err("Validation", "Type must be 'income' or 'expense'.")
            return

        acc_name = self.var_account.get()
        cat_name = self.var_category.get()

        if acc_name not in self._acc_map:
            err("Validation", "Please select a valid account.")
            return

        if cat_name and cat_name not in self._cat_map:
            err("Validation", "Please select a valid category.")
            return

        notes = self.txt_notes.get().strip() or None

        # --- DB write ---
        try:
            with SessionLocal() as s:
                # cat_id calculado uma única vez, visível para if / else
                cat_id = self._cat_map.get(cat_name)

                if self.tx_id:
                    tx = s.get(Transaction, self.tx_id)
                    assert tx is not None  # garante para o Pyright que tx não é None

                    tx.date = tx_date
                    tx.amount = amt
                    tx.type = typ
                    tx.account_id = self._acc_map[acc_name]
                    tx.category_id = cat_id  # type: ignore[assignment]
                    tx.notes = notes
                else:
                    s.add(
                        Transaction(
                            date=tx_date,
                            amount=amt,
                            type=typ,
                            account_id=self._acc_map[acc_name],
                            category_id=cat_id,  # type: ignore[arg-type]
                            notes=notes,
                        )
                    )

                s.commit()

            info("Success", "✅ Transaction saved!")
            self.destroy()

        except Exception as e:
            err("DB Error", f"Could not save transaction:\n{e}")  


# ---------- listing / filters / export ----------
def filtered_rows(cb_type=None, cb_cat=None, cb_acc=None, ent_from=None, ent_to=None, ent_search=None):
    tx_type = (cb_type.get().strip() or None) if cb_type else None
    cat_id = id_from_name(Category, cb_cat.get().strip()) if cb_cat and cb_cat.get().strip() else None
    acc_id = id_from_name(Account, cb_acc.get().strip()) if cb_acc and cb_acc.get().strip() else None
    d_from = parse_date(ent_from.get()) if ent_from else None
    d_to = parse_date(ent_to.get()) if ent_to else None
    q = ent_search.get().strip() if ent_search else None

    with SessionLocal() as s:
        acc_map, cat_map = maps(s)
        rows = get_transactions(
            s,
            tx_type=tx_type,
            category_id=cat_id,
            account_id=acc_id,
            date_from=d_from,
            date_to=d_to,
            notes_query=q,
        )
    return rows, acc_map, cat_map


def refresh_table(tree, cb_type=None, cb_cat=None, cb_acc=None,
                  ent_from=None, ent_to=None, total_var: tk.StringVar | None = None,
                  ent_search=None):
    for i in tree.get_children():
        tree.delete(i)

    rows, acc_map, cat_map = filtered_rows(cb_type, cb_cat, cb_acc, ent_from, ent_to, ent_search)
    inc = exp = 0.0
    for r in rows:
        amt = float(r.amount)
        inc += amt if r.type == "income" else 0.0
        exp += amt if r.type == "expense" else 0.0
        tree.insert(
            "",
            "end",
            values=(
                r.id,
                r.date.isoformat(),
                r.type,
                f"{amt:.2f}",
                acc_map.get(r.account_id, ""),
                cat_map.get(r.category_id, ""),
                (r.notes or "")[:80],
            ),
        )
    if total_var is not None:
        total_var.set(f"Totals — Income: {inc:.2f} | Expense: {exp:.2f} | Net: {(inc - exp):.2f}")


def clear_filters(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search):
    cb_type.set("")
    cb_cat.set("")
    cb_acc.set("")
    ent_from.delete(0, "end")
    ent_to.delete(0, "end")
    ent_search.delete(0, "end")
    refresh_table(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)


def export_csv(cb_type, cb_cat, cb_acc, ent_from, ent_to, ent_search):
    rows, acc_map, cat_map = filtered_rows(cb_type, cb_cat, cb_acc, ent_from, ent_to, ent_search)
    project_root = pathlib.Path(__file__).resolve().parents[2]  # <repo root>
    outdir = project_root / "exports"
    outdir.mkdir(exist_ok=True)
    path = outdir / f"transactions_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    try:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "date", "type", "amount", "account", "category", "notes"])
            for r in rows:
                w.writerow([
                    r.id,
                    r.date.isoformat(),
                    r.type,
                    f"{float(r.amount):.2f}",
                    acc_map.get(r.account_id, ""),
                    cat_map.get(r.category_id, ""),
                    r.notes or "",
                ])
        info("Export CSV", f"✅ Exported {len(rows)} rows to:\n{path}")
    except Exception as e:
        err("Export CSV", f"❌ Failed to export:\n{e}")


def del_selected(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search):
    sel = tree.selection()
    if not sel:
        return info("Delete", "No transaction selected.")
    tx_id = int(tree.item(sel[0], "values")[0])
    if not messagebox.askyesno("Confirm", f"Delete transaction ID {tx_id}?"):
        return
    with SessionLocal() as s:
        ok = delete_transaction(s, tx_id)
    info("Delete", f"✅ Transaction {tx_id} deleted.") if ok else err("Delete", "❌ Could not delete.")
    refresh_table(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)


def open_add(root, tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search):
    dlg = TransactionDialog(root)
    root.wait_window(dlg)
    refresh_table(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)


def open_edit(root, tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search):
    sel = tree.selection()
    if not sel:
        return info("Edit", "No transaction selected.")
    tx_id = int(tree.item(sel[0], "values")[0])
    dlg = TransactionDialog(root, tx_id=tx_id)
    root.wait_window(dlg)
    refresh_table(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)


# ---------- main window ----------
def run():
    root = tk.Tk()
    root.title("Finance Tracker")

    # make window visible/focused (WSLg/tmux friendly)
    root.withdraw()
    root.update_idletasks()
    root.geometry("980x600+160+120")
    root.deiconify()
    root.lift()
    root.focus_force()
    root.attributes("-topmost", True)
    root.after(500, lambda: root.attributes("-topmost", False))
    root.resizable(True, True)

    container = ttk.Frame(root, padding=16)
    container.pack(fill="both", expand=True)
    ttk.Label(container, text="Personal Finance Tracker", font=("Segoe UI", 14, "bold")).pack(anchor="w")
    ttk.Label(container, text="MVP with DB connection and CRUD.", font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 16))

    # top row (db + dashboard)
    top = ttk.Frame(container)
    top.pack(fill="x", pady=(8, 0))
    ttk.Button(top, text="Test DB", command=test_db_connection).pack(side="left")
    ttk.Button(top, text="Dashboard", command=lambda: open_dashboard(root)).pack(side="left", padx=8)

    # filters
    filters = ttk.Frame(container)
    filters.pack(fill="x", pady=(12, 4))
    ttk.Label(filters, text="Type").pack(side="left", padx=(0, 4))
    cb_type = ttk.Combobox(filters, values=["", "expense", "income"], width=10, state="readonly")
    cb_type.set("")
    cb_type.pack(side="left", padx=(0, 12))
    ttk.Label(filters, text="Category").pack(side="left")
    cb_cat = ttk.Combobox(filters, width=18, state="readonly")
    cb_cat.pack(side="left", padx=(4, 12))
    ttk.Label(filters, text="Account").pack(side="left")
    cb_acc = ttk.Combobox(filters, width=18, state="readonly")
    cb_acc.pack(side="left", padx=(4, 12))
    load_filter_options(cb_cat, cb_acc)
    ttk.Label(filters, text="From").pack(side="left", padx=(8, 4))
    ent_from = ttk.Entry(filters, width=12)
    ent_from.pack(side="left")
    ttk.Label(filters, text="To").pack(side="left", padx=(8, 4))
    ent_to = ttk.Entry(filters, width=12)
    ent_to.pack(side="left")
    ttk.Label(filters, text="Search").pack(side="left", padx=(8, 4))
    ent_search = ttk.Entry(filters, width=18)
    ent_search.pack(side="left")

    # totals
    total_var = tk.StringVar(value="Totals — Income: 0.00 | Expense: 0.00 | Net: 0.00")
    ttk.Label(container, textvariable=total_var, anchor="w").pack(fill="x", pady=(0, 4))

    # table
    table_frame = ttk.Frame(container)
    table_frame.pack(fill="both", expand=True, pady=(4, 8))
    columns = ("id", "date", "type", "amount", "account", "category", "notes")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)
    for c in columns:
        tree.heading(c, text=c.title())
        tree.column(c, anchor="center", width=110 if c != "notes" else 300)
    tree.column("notes", anchor="w")
    tree.pack(side="left", fill="both", expand=True)
    sb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    sb.pack(side="right", fill="y")
    tree.configure(yscrollcommand=sb.set)

    # double click -> edit
    tree.bind("<Double-1>", lambda e: open_edit(root, tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search))

    # actions
    actions = ttk.Frame(container)
    actions.pack(fill="x", pady=(0, 10))
    ttk.Button(
        actions, text="Add",
        command=lambda: open_add(root, tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)
    ).pack(side="left")
    ttk.Button(
        actions, text="Edit",
        command=lambda: open_edit(root, tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)
    ).pack(side="left", padx=8)
    ttk.Button(
        actions, text="Delete",
        command=lambda: del_selected(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)
    ).pack(side="left", padx=8)
    ttk.Button(
        actions, text="Apply",
        command=lambda: refresh_table(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)
    ).pack(side="left", padx=8)
    ttk.Button(
        actions, text="Clear",
        command=lambda: clear_filters(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)
    ).pack(side="left", padx=8)
    ttk.Button(
        actions, text="Export CSV",
        command=lambda: export_csv(cb_type, cb_cat, cb_acc, ent_from, ent_to, ent_search)
    ).pack(side="left", padx=8)
    ttk.Button(actions, text="Exit", command=root.destroy).pack(side="right")

    # status
    ttk.Label(
        container,
        text=f"Connected URL: {os.getenv('DATABASE_URL','(not set)')}",
        anchor="w",
        relief="groove"
    ).pack(fill="x", pady=(8, 0))

    # initial + enter-to-apply (inclui Search)
    refresh_table(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search)
    for w in (cb_type, cb_cat, cb_acc, ent_from, ent_to, ent_search):
        w.bind("<Return>", lambda e: refresh_table(tree, cb_type, cb_cat, cb_acc, ent_from, ent_to, total_var, ent_search))

    root.mainloop()


if __name__ == "__main__":
    run()
























