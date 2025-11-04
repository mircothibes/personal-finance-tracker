import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

def test_db_connection():
    url = os.getenv("DATABASE_URL")
    if not url:
        messagebox.showerror("DB Test", "DATABASE_URL not set in .env")
        return

    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        messagebox.showinfo("DB Test", "✅ Connected successfully!")
    except Exception as e:
        messagebox.showerror("DB Test", f"❌ Connection failed:\n{e}")

def run():
    root = tk.Tk()
    root.title("Finance Tracker")
    root.geometry("520x260")
    root.resizable(False, False)

    container = ttk.Frame(root, padding=16)
    container.pack(fill="both", expand=True)

    title = ttk.Label(container, text="Personal Finance Tracker",
                      font=("Segoe UI", 14, "bold"))
    title.pack(anchor="w")

    subtitle = ttk.Label(
        container,
        text="This is the first UI draft (MVP).",
        font=("Segoe UI", 10)
    )
    subtitle.pack(anchor="w", pady=(4, 16))

    # Buttons row
    buttons = ttk.Frame(container)
    buttons.pack(fill="x", pady=(8, 0))

    test_btn = ttk.Button(buttons, text="Test DB", command=test_db_connection)
    test_btn.pack(side="left")

    ttk.Button(buttons, text="Exit", command=root.destroy).pack(side="right")

    # status bar
    status = ttk.Label(container, text=f"Today: {date.today().isoformat()}",
                       anchor="w", relief="groove")
    status.pack(fill="x", pady=(16, 0))

    root.mainloop()

if __name__ == "__main__":
    run()

