import os
import pymysql


import os
import pymysql


def _base_config(include_database=True):
    host = os.getenv("MYSQLHOST")
    port = os.getenv("MYSQLPORT")
    user = os.getenv("MYSQLUSER")
    password = os.getenv("MYSQLPASSWORD")

    if not host:
        raise RuntimeError(
            "MYSQLHOST no está configurado. "
            "En Railway debe apuntar al servicio MySQL."
        )

    config = {
        "host": host,
        "port": int(port or "3306"),
        "user": user or "root",
        "password": password or "",
        "charset": "utf8mb4",
        "autocommit": True,
    }

    if include_database:
        config["database"] = (
            os.getenv("APP_DATABASE")
            or "inversion_bi"
        )

    return config


def get_connection(include_database=True):
    return pymysql.connect(
        **_base_config(
            include_database=include_database
        )
    )

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
