import os
import re
from pathlib import Path

from database.db import get_connection

DB_NAME = os.getenv("APP_DATABASE", "inversion_bi")

COMPANY_NAMES = {
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "NVDA": "NVIDIA Corporation",
    "AMZN": "Amazon.com, Inc.",
    "GOOGL": "Alphabet Inc.",
    "SPY": "SPDR S&P 500 ETF Trust",
    "QQQ": "Invesco QQQ Trust",
}


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


def _column_exists(cur, table_name, column_name):
    cur.execute(
        "SELECT COUNT(*) AS n FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s AND COLUMN_NAME=%s",
        (DB_NAME, table_name, column_name),
    )
    return int(cur.fetchone()["n"]) > 0


def _add_column(cur, table, column, ddl):
    if not _column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN {ddl}")


def apply_migrations():
    """Migración idempotente desde versiones anteriores del proyecto."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            _add_column(cur, "market_data", "adj_close", "adj_close DECIMAL(18,6) NULL AFTER close_price")
            _add_column(cur, "market_data", "currency", "currency VARCHAR(10) NULL AFTER volume")
            _add_column(cur, "market_data", "exchange_name", "exchange_name VARCHAR(80) NULL AFTER currency")

            _add_column(cur, "economic_indicators", "realtime_start", "realtime_start DATE NULL AFTER value")
            _add_column(cur, "economic_indicators", "realtime_end", "realtime_end DATE NULL AFTER realtime_start")
            _add_column(cur, "economic_indicators", "units", "units VARCHAR(80) NULL AFTER realtime_end")
            _add_column(cur, "economic_indicators", "frequency", "frequency VARCHAR(80) NULL AFTER units")

            for col, ddl in [
                ("domain", "domain VARCHAR(255) NULL AFTER source"),
                ("language", "language VARCHAR(50) NULL AFTER domain"),
                ("source_country", "source_country VARCHAR(100) NULL AFTER language"),
                ("social_image", "social_image VARCHAR(1500) NULL AFTER source_country"),
                ("seen_at", "seen_at DATETIME NULL AFTER social_image"),
            ]:
                _add_column(cur, "financial_news", col, ddl)

            for table in ["prediction_history", "backtesting", "model_metrics", "asset_ranking", "decision_log", "ai_decision_comment"]:
                _add_column(cur, table, "run_id", "run_id BIGINT NULL AFTER id")

            _add_column(cur, "backtesting", "max_drawdown", "max_drawdown DECIMAL(12,6) NULL AFTER benchmark_return")
            _add_column(cur, "backtesting", "trades_count", "trades_count INT NOT NULL DEFAULT 0 AFTER hit_rate")


def seed_assets():
    tickers = [
        t.strip().upper()
        for t in os.getenv("TICKERS", "AAPL,MSFT,NVDA,AMZN,GOOGL,SPY,QQQ").split(",")
        if t.strip()
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            for ticker in tickers:
                asset_type = "ETF" if ticker in {"SPY", "QQQ"} else "STOCK"
                company_name = COMPANY_NAMES.get(ticker, ticker)
                cur.execute(
                    """
                    INSERT INTO assets (ticker, company_name, asset_type)
                    VALUES (%s,%s,%s)
                    ON DUPLICATE KEY UPDATE
                        company_name=VALUES(company_name),
                        asset_type=VALUES(asset_type),
                        active=1
                    """,
                    (ticker, company_name, asset_type),
                )


def list_tables():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SHOW TABLES")
            return [next(iter(row.values())) for row in cur.fetchall()]


def init_database():
    create_database()
    apply_schema()
    apply_migrations()
    seed_assets()
    tables = list_tables()
    print(f"Base '{DB_NAME}' lista. Tablas: {', '.join(tables)}")


if __name__ == "__main__":
    init_database()
