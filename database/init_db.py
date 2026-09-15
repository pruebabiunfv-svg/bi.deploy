import os
import re
from pathlib import Path
from database.db import get_connection

DB_NAME = os.getenv("APP_DATABASE", "inversion_bi")


def _validate_name(name):
    if not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise ValueError("APP_DATABASE solo puede contener letras, números y guion bajo")


def create_database():
    _validate_name(DB_NAME)
    with get_connection(include_database=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )


def apply_schema():
    schema = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    statements = [s.strip() for s in schema.split(";") if s.strip()]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for statement in statements:
                cur.execute(statement)


def seed_assets():
    tickers = [t.strip().upper() for t in os.getenv(
        "TICKERS", "AAPL,MSFT,NVDA,AMZN,GOOGL,SPY,QQQ"
    ).split(",") if t.strip()]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for ticker in tickers:
                asset_type = "ETF" if ticker in {"SPY", "QQQ"} else "STOCK"
                cur.execute(
                    "INSERT INTO assets (ticker, asset_type) VALUES (%s,%s) "
                    "ON DUPLICATE KEY UPDATE active=1",
                    (ticker, asset_type),
                )


def list_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            return [next(iter(row.values())) for row in cur.fetchall()]


def init_database():
    create_database()
    apply_schema()
    seed_assets()
    tables = list_tables()
    print(f"Base '{DB_NAME}' lista. Tablas: {', '.join(tables)}")


if __name__ == "__main__":
    init_database()
