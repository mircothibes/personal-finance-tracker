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
            exists = s.query(Account).filter_by(name=name).first()
            if not exists:
                s.add(Account(name=name))
        s.commit()
        print("✅ Seeded accounts.")

if __name__ == "__main__":
    main()

