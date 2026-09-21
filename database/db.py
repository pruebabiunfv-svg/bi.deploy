import os
import pymysql


def _base_config(include_database=True):
    host = os.getenv("MYSQLHOST")
    password = os.getenv("MYSQLPASSWORD")
    allow_local = os.getenv("ALLOW_LOCAL_MYSQL", "false").strip().lower() in {"1","true","yes","on"}

    if not host:
        if allow_local:
            host = "127.0.0.1"
        else:
            raise RuntimeError(
                "MYSQLHOST no está configurado. En Railway use "
                "${{MySQL.RAILWAY_PRIVATE_DOMAIN}}. Para MySQL local use ALLOW_LOCAL_MYSQL=true."
            )
    if password is None:
        if allow_local:
            password = ""
        else:
            raise RuntimeError("MYSQLPASSWORD no está configurado.")

    cfg = {
        "host": host,
        "port": int(os.getenv("MYSQLPORT") or "3306"),
        "user": os.getenv("MYSQLUSER") or "root",
        "password": password,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
        "connect_timeout": 15,
        "read_timeout": 60,
        "write_timeout": 60,
    }
    if include_database:
        cfg["database"] = os.getenv("APP_DATABASE") or "inversion_bi"
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
