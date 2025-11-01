    import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import create_engine

def main() -> None:
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set. Check your .env file.")
    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version();")).scalar_one()
        print("✅ Connected to PostgreSQL")
        print(version)

if __name__ == "__main__":
    main()
