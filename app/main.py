import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.engine import create_engine


def main() -> None:
    # Force .env to override anything else
    load_dotenv(override=True)

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set. Check your .env file.")

    print(f"[DEBUG] DATABASE_URL = {db_url!r}")

    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        version = conn.execute(text("SELECT version();")).scalar_one()
        print("✅ Connected to PostgreSQL")
        print(version)


if __name__ == "__main__":
    main()
