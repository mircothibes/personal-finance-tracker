import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://finance:finance@db:5432/finance_db")
engine = create_engine(DATABASE_URL)

# Default categories
CATEGORIES = [
    ("Salary", "income"),
    ("Bonus", "income"),
    ("Investments", "income"),
    ("Food", "expense"),
    ("Rent", "expense"),
    ("Transport", "expense"),
    ("Entertainment", "expense"),
]

def seed_categories():
    with engine.begin() as conn:
        for name, type_ in CATEGORIES:
            conn.execute(
                text(
                    "INSERT INTO categories (name, type) "
                    "VALUES (:name, :type) "
                    "ON CONFLICT (name) DO NOTHING"
                ),
                {"name": name, "type": type_},
            )
    print("✅ Categories seeded successfully!")

if __name__ == "__main__":
    seed_categories()

