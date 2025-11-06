import sys, os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.db import SessionLocal, get_transactions, delete_transaction

def main():
    with SessionLocal() as s:
        rows = get_transactions(s)
        print(f"found {len(rows)} transactions")
        if rows:
            first = rows[0]
            print(f"deleting id={first.id}")
            ok = delete_transaction(s, first.id)
            print("deleted?", ok)
            rows2 = get_transactions(s)
            print(f"after delete: {len(rows2)} transactions")

if __name__ == "__main__":
    main()

