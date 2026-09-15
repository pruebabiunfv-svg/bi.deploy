import os
import pymysql


import os
import pymysql

import os

import pymysql
from pymysql.cursors import DictCursor


def _base_config(include_database=True):

    host = os.getenv("MYSQLHOST")
    port = os.getenv("MYSQLPORT") or "3306"
    user = os.getenv("MYSQLUSER")
    password = os.getenv("MYSQLPASSWORD")

    if not host:
        raise RuntimeError(
            "MYSQLHOST no está configurado. "
            "En Railway debe apuntar al servicio MySQL."
        )

    if not user:
        raise RuntimeError(
            "MYSQLUSER no está configurado."
        )

    if not password:
        raise RuntimeError(
            "MYSQLPASSWORD no está configurado."
        )

    config = {
        "host": host,
        "port": int(port),
        "user": user,
        "password": password,
        "charset": "utf8mb4",
        "autocommit": True,
        "cursorclass": DictCursor,
        "connect_timeout": 10,
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
