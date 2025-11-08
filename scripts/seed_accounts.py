import os, sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


from app.db import SessionLocal
from app.models import Account

ACCOUNTS = [
    "Cash",
    "Bank Account",
    "Credit Card",
    "Savings",
    "Wallet",
]

def main():
    with SessionLocal() as s:
        for name in ACCOUNTS:
            if not s.query(Account).filter_by(name=name).first():
                s.add(Account(name=name))
        s.commit()
        print("✅ Seeded accounts.", ", ".join(ACCOUNTS))

if __name__ == "__main__":
    main()

