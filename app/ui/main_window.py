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


# ---------- utils ----------
def show_info(title, msg): messagebox.showinfo(title, msg)
def show_err(title, msg):  messagebox.showerror(title, msg)

def test_db_connection():
    try:
        with engine.connect() as c: c.execute(text("SELECT 1"))
        show_info("DB Test", "✅ Connected successfully!")
    except Exception as e:
        show_err("DB Test", f"❌ Connection failed:\n{e}")

def map_ids_to_names(session):
    acc_map = dict(session.execute(select(Account.id, Account.name)).all())
    cat_map = dict(session.execute(select(Category.id, Category.name)).all())
    return acc_map, cat_map

def id_from_name(model, name):
    if not name: return None
    with SessionLocal() as s:
        row = s.execute(select(model.id).where(model.name == name)).first()
        return row[0] if row else None

def load_filter_options(cb_category: ttk.Combobox, cb_account: ttk.Combobox):
    with SessionLocal() as s:
        cats = [r[0] for r in s.execute(select(Category.name).order_by(Category.name)).all()]
        accs = [r[0] for r in s.execute(select(Account.name).order_by(Account.name)).all()]
    cb_category["values"] = [""] + cats; cb_account["values"] = [""] + accs
    cb_category.set(""); cb_account.set("")


# ---------- dialog (add/edit) ----------
class TransactionDialog(tk.Toplevel):
    def __init__(self, master: tk.Misc, tx_id: int | None = None):
        super().__init__(master)
        self.title("Edit Transaction" if tx_id else "Add Transaction")
        self.resizable(False, False); self.grab_set()
        self.tx_id = tx_id

        pad = {"padx": 8, "pady": 6}
        frm = ttk.Frame(self, padding=12); frm.grid(row=0, column=0)

        self.var_type   = tk.StringVar(value="expense")
        self.var_date   = tk.StringVar(value=date.today().isoformat())
        self.var_amount = tk.StringVar(value="")
        self.var_account= tk.StringVar()
        self.var_category=tk.StringVar()

        def row(label, widget):
            r = len(frm.grid_slaves())//2
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", **pad)
            widget.grid(row=r, column=1, **pad)

        row("Type",   ttk.Combobox(frm, textvariable=self.var_type, values=["expense","income"], state="readonly"))
        row("Date (YYYY-MM-DD)", ttk.Entry(frm, textvariable=self.var_date, width=18))
        row("Amount", ttk.Entry(frm, textvariable=self.var_amount, width=18))
        self.cmb_account  = ttk.Combobox(frm, textvariable=self.var_account, state="readonly");  row("Account",  self.cmb_account)
        self.cmb_category = ttk.Combobox(frm, textvariable=self.var_category, state="readonly"); row("Category", self.cmb_category)

        ttk.Label(frm, text="Notes (optional)").grid(row=5, column=0, sticky="w", **pad)
        self.txt_notes = ttk.Entry(frm, width=28); self.txt_notes.grid(row=5, column=1, **pad)

        btns = ttk.Frame(frm); btns.grid(row=6, column=0, columnspan=2, sticky="e", pady=(10,0))
        ttk.Button(btns, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Save", command=self.on_save).grid(row=0, column=1)

        self.var_type.trace_add("write", lambda *_: self.load_categories())
        self.load_accounts(); self.load_categories()
        if self.tx_id: self.load_existing()

    def load_accounts(self):
        with SessionLocal() as s:
            rows = s.execute(select(Account.id, Account.name).order_by(Account.name)).all()
        self._acc_map = {name:_id for _id,name in [(i,n) for i,n in rows][::-1]}  # name->id
        names = [name for (_id,name) in rows]
        self.cmb_account["values"] = names
        if names: self.var_account.set(names[0])

    def load_categories(self):
        typ = self.var_type.get()
        with SessionLocal() as s:
            rows = s.execute(select(Category.id, Category.name).where(Category.type==typ).order_by(Category.name)).all()
        self._cat_map = {name:_id for _id,name in [(i,n) for i,n in rows][::-1]}
        names = [name for (_id,name) in rows]
        self.cmb_category["values"] = names
        self.var_category.set(names[0] if names else "")

    def load_existing(self):
        with SessionLocal() as s:
            tx = s.get(Transaction, self.tx_id)
            if not tx: show_err("Error", f"Transaction {self.tx_id} not found."); self.destroy(); return
            self.var_type.set(tx.type); self.var_date.set(tx.date.isoformat())
            self.var_amount.set(str(float(tx.amount))); self.txt_notes.insert(0, tx.notes or "")
            # reload categories to match type
            self.load_categories()
            acc = s.execute(select(Account.name).where(Account.id==tx.account_id)).first()
            cat = s.execute(select(Category.name).where(Category.id==tx.category_id)).first()
            if acc: self.var_account.set(acc[0])
            if cat: self.var_category.set(cat[0])

    def on_save(self):
        try:
            amt = Decimal(self.var_amount.get());  assert amt >= 0
        except Exception:
            return show_err("Validation","Amount must be a positive number.")
        try:
            tx_date = datetime.strptime(self.var_date.get(), "%Y-%m-%d").date()
        except ValueError:
            return show_err("Validation","Date must be in format YYYY-MM-DD.")
        typ = self.var_type.get()
        if typ not in ("income","expense"):
            return show_err("Validation","Type must be 'income' or 'expense'.")
        acc_name, cat_name = self.var_account.get(), self.var_category.get()
        if acc_name not in self._acc_map or (cat_name and cat_name not in self._cat_map):
            return show_err("Validation","Select valid Account and Category.")

        notes = self.txt_notes.get().strip() or None

        try:
            with SessionLocal() as s:
                if self.tx_id:
                    tx = s.get(Transaction, self.tx_id)
                    tx.date, tx.amount, tx.type = tx_date, amt, typ
                    tx.account_id, tx.category_id, tx.notes = self._acc_map[acc_name], self._cat_map.get(cat_name), notes
                else:
                    s.add(Transaction(
                        date=tx_date, amount=amt, type=typ,
                        account_id=self._acc_map[acc_name],
                        category_id=self._cat_map.get(cat_name), notes=notes
                    ))
                s.commit()
            show_info("Success","✅ Transaction saved!"); self.destroy()
        except Exception as e:
            show_err("DB Error", f"Could not save transaction:\n{e}")


# ---------- table / filters ----------
def _parse_date_or_none(s: str | None):
    if not s: return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception:
        return None  # silencioso: filtro vazio/ruim é ignorado

def refresh_table(tree, cb_type=None, cb_category=None, cb_account=None, ent_from=None, ent_to=None):
    for i in tree.get_children(): tree.delete(i)
    tx_type = (cb_type.get().strip() or None) if cb_type else None
    cat_id  = id_from_name(Category, cb_category.get().strip()) if cb_category and cb_category.get().strip() else None
    acc_id  = id_from_name(Account,  cb_account.get().strip())  if cb_account  and cb_account.get().strip()  else None
    d_from  = _parse_date_or_none(ent_from.get()) if ent_from else None
    d_to    = _parse_date_or_none(ent_to.get())   if ent_to   else None
    with SessionLocal() as s:
        acc_map, cat_map = map_ids_to_names(s)
        rows = get_transactions(s, tx_type=tx_type, category_id=cat_id, account_id=acc_id,
                                date_from=d_from, date_to=d_to)
    for r in rows:
        tree.insert("", "end", values=(
            r.id, r.date.isoformat(), r.type, f"{float(r.amount):.2f}",
            acc_map.get(r.account_id,""), cat_map.get(r.category_id,""),
            (r.notes or "")[:80],
        ))

def clear_filters_and_refresh(tree, cb_type, cb_category, cb_account, ent_from, ent_to):
    cb_type.set(""); cb_category.set(""); cb_account.set("")
    ent_from.delete(0, "end"); ent_to.delete(0, "end")
    refresh_table(tree, cb_type, cb_category, cb_account, ent_from, ent_to)

def delete_selected(tree, cb_type, cb_category, cb_account, ent_from, ent_to):
    sel = tree.selection()
    if not sel: return show_info("Delete","No transaction selected.")
    tx_id = int(tree.item(sel[0], "values")[0])
    if not messagebox.askyesno("Confirm", f"Delete transaction ID {tx_id}?"): return
    with SessionLocal() as s: ok = delete_transaction(s, tx_id)
    show_info("Delete", f"✅ Transaction {tx_id} deleted.") if ok else show_err("Delete","❌ Could not delete.")
    refresh_table(tree, cb_type, cb_category, cb_account, ent_from, ent_to)

def open_add(root, tree, cb_type, cb_category, cb_account, ent_from, ent_to):
    dlg = TransactionDialog(root); root.wait_window(dlg)
    refresh_table(tree, cb_type, cb_category, cb_account, ent_from, ent_to)

def open_edit(root, tree, cb_type, cb_category, cb_account, ent_from, ent_to):
    sel = tree.selection()
    if not sel: return show_info("Edit","No transaction selected.")
    tx_id = int(tree.item(sel[0], "values")[0])
    dlg = TransactionDialog(root, tx_id=tx_id); root.wait_window(dlg)
    refresh_table(tree, cb_type, cb_category, cb_account, ent_from, ent_to)


# ---------- main window ----------
def run():
    root = tk.Tk()
    root.title("Finance Tracker")
    root.geometry("980x600")
    root.resizable(True, True)

    container = ttk.Frame(root, padding=16); container.pack(fill="both", expand=True)

    ttk.Label(container, text="Personal Finance Tracker", font=("Segoe UI", 14, "bold")).pack(anchor="w")
    ttk.Label(container, text="MVP with DB connection and add/edit transactions.", font=("Segoe UI", 10)).pack(anchor="w", pady=(4, 16))

    top = ttk.Frame(container); top.pack(fill="x", pady=(8, 0))
    ttk.Button(top, text="Test DB", command=test_db_connection).pack(side="left")

    # Filters
    filters = ttk.Frame(container); filters.pack(fill="x", pady=(12, 4))
    ttk.Label(filters, text="Type").pack(side="left", padx=(0, 4))
    cb_type = ttk.Combobox(filters, values=["", "expense", "income"], width=10, state="readonly"); cb_type.set("")
    cb_type.pack(side="left", padx=(0, 12))

    ttk.Label(filters, text="Category").pack(side="left")
    cb_category = ttk.Combobox(filters, width=18, state="readonly"); cb_category.pack(side="left", padx=(4, 12))

    ttk.Label(filters, text="Account").pack(side="left")
    cb_account = ttk.Combobox(filters, width=18, state="readonly"); cb_account.pack(side="left", padx=(4, 12))
    load_filter_options(cb_category, cb_account)

    ttk.Label(filters, text="From").pack(side="left", padx=(8, 4))
    ent_from = ttk.Entry(filters, width=12); ent_from.pack(side="left")
    ttk.Label(filters, text="To").pack(side="left", padx=(8, 4))
    ent_to   = ttk.Entry(filters, width=12); ent_to.pack(side="left")

    # Table
    table_frame = ttk.Frame(container); table_frame.pack(fill="both", expand=True, pady=(4, 8))
    columns = ("id","date","type","amount","account","category","notes")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)
    for col in columns:
        tree.heading(col, text=col.title()); tree.column(col, anchor="center", width=110 if col!="notes" else 240)
    tree.column("notes", width=300, anchor="w")
    tree.pack(side="left", fill="both", expand=True)

    # ✅ Scrollbar correto (corrige o TclError)
    scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    scrollbar.pack(side="right", fill="y")
    tree.configure(yscrollcommand=scrollbar.set)

    tree.bind("<Double-1>", lambda e: open_edit(root, tree, cb_type, cb_category, cb_account, ent_from, ent_to))

    # Actions
    actions = ttk.Frame(container); actions.pack(fill="x", pady=(0, 10))
    ttk.Button(actions, text="Add Transaction…",
               command=lambda: open_add(root, tree, cb_type, cb_category, cb_account, ent_from, ent_to)).pack(side="left")
    ttk.Button(actions, text="Edit Selected",
               command=lambda: open_edit(root, tree, cb_type, cb_category, cb_account, ent_from, ent_to)).pack(side="left", padx=8)
    ttk.Button(actions, text="Delete Selected",
               command=lambda: delete_selected(tree, cb_type, cb_category, cb_account, ent_from, ent_to)).pack(side="left", padx=8)
    ttk.Button(actions, text="Apply Filters",
               command=lambda: refresh_table(tree, cb_type, cb_category, cb_account, ent_from, ent_to)).pack(side="left", padx=8)
    ttk.Button(actions, text="Clear",
               command=lambda: clear_filters_and_refresh(tree, cb_type, cb_category, cb_account, ent_from, ent_to)).pack(side="left", padx=8)
    ttk.Button(actions, text="Exit", command=root.destroy).pack(side="right")

    status = ttk.Label(container, text=f"Connected URL: {os.getenv('DATABASE_URL','(not set)')}", anchor="w", relief="groove")
    status.pack(fill="x", pady=(8, 0))

    # initial load
    refresh_table(tree, cb_type, cb_category, cb_account, ent_from, ent_to)
    for w in (cb_type, cb_category, cb_account, ent_from, ent_to):
        w.bind("<Return>", lambda e: refresh_table(tree, cb_type, cb_category, cb_account, ent_from, ent_to))

    root.mainloop()


if __name__ == "__main__":
    run()





















