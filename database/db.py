import os
import pymysql


def _base_config(include_database=True):
    cfg = {
        "host": os.getenv("MYSQLHOST", "127.0.0.1"),
        "port": int(os.getenv("MYSQLPORT", "3306")),
        "user": os.getenv("MYSQLUSER", "root"),
        "password": os.getenv("MYSQLPASSWORD", ""),
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }
    if include_database:
        cfg["database"] = os.getenv("APP_DATABASE", "inversion_bi")
    return cfg


def get_connection(include_database=True):
    return pymysql.connect(**_base_config(include_database=include_database))


def fetch_all(sql, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()


def fetch_one(sql, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.fetchone()


def execute(sql, params=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            return cur.rowcount
