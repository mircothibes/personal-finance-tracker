import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import sessionmaker
from .models import Transaction, Category, Account


load_dotenv()

DATABASE_URL = os.getenv(
        "DATABASE_URL", 
        "postgresql+psycopg2://finance:finance@localhost:5432/finance_db")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True, future=True)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


# ------------------------------
# Helpers: transactions query & delete
# ------------------------------
def get_transactions(
    session,
    tx_type: str | None = None,
    category_id: int | None = None,
    account_id: int | None = None,
    date_from: str | None = None,  # "YYYY-MM-DD" (ou datetime/date se preferir)
    date_to: str | None = None,
):
    """
    Return a list of Transaction objects applying optional filters.
    Eager-loads category and account to avoid N+1 queries.
    """
    filters = []
    if tx_type:
        filters.append(Transaction.type == tx_type)
    if category_id:
        filters.append(Transaction.category_id == category_id)
    if account_id:
        filters.append(Transaction.account_id == account_id)
    if date_from:
        filters.append(Transaction.date >= date_from)
    if date_to:
        filters.append(Transaction.date <= date_to)

    stmt = select(Transaction)

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(Transaction.date.desc(), Transaction.id.desc())
    return session.execute(stmt).scalars().all()


def delete_transaction(session, tx_id: int) -> bool:
    """
    Delete a transaction by ID. Returns True if deleted, False if not found.
    """
    tx = session.get(Transaction, tx_id)
    if not tx:
        return False
    session.delete(tx)
    session.commit()
    return True
