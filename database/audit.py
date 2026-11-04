import json
import hashlib
import os
from functools import wraps
from database.db import get_connection


def single_flight_pipeline(func):
    """Bloqueo de sesión MySQL, liberado al terminar o cerrarse la conexión."""
    @wraps(func)
    def wrapped(*args, **kwargs):
        from database.init_db import init_database

        init_database()
        with get_connection() as lock_connection:
            with lock_connection.cursor() as cur:
                cur.execute("SELECT GET_LOCK(%s, 0) AS acquired", ("inversia_pipeline",))
                lock = cur.fetchone()
                if int(lock["acquired"] or 0) != 1:
                    raise RuntimeError("Otra ejecución de InversIA ya está activa; no se inicia otra")
            try:
                return func(*args, **kwargs)
            finally:
                with lock_connection.cursor() as cur:
                    cur.execute("SELECT RELEASE_LOCK(%s)", ("inversia_pipeline",))
    return wrapped


def start_analysis_run(market_period, horizon_days, model_version, total_assets):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO analysis_runs
                (status, market_period, horizon_days, model_version, total_assets)
                VALUES ('RUNNING', %s, %s, %s, %s)
                """,
                (market_period, horizon_days, model_version, total_assets),
            )
            return int(cur.lastrowid)


def finish_analysis_run(run_id, status='COMPLETED', notes=None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE analysis_runs
                SET status=%s, notes=%s, completed_at=NOW()
                WHERE id=%s
                """,
                (status, notes, run_id),
            )


def save_raw_payload(run_id, source_name, ticker, endpoint, request_parameters, payload, http_status):
    """Auditoría acotada: evita guardar SEC/GDELT gigantes en MySQL (500 MB).

    RAW_AUDIT_MODE=bounded (por defecto) conserva cargas pequeñas y reemplaza
    las grandes por metadatos verificables. ``full`` es opt-in; ``none`` omite.
    Nunca elimina automáticamente registros existentes.
    """
    mode = os.getenv("RAW_AUDIT_MODE", "bounded").lower().strip()
    if mode == "none":
        return
    try:
        params_json = json.dumps(request_parameters or {}, ensure_ascii=False, default=str)
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        max_bytes = max(1024, int(os.getenv("RAW_PAYLOAD_MAX_BYTES", "65536")))
        size = len(payload_json.encode("utf-8"))
        if mode != "full" and size > max_bytes:
            payload_json = json.dumps({
                "_audit_mode": "bounded",
                "truncated": True,
                "original_size_bytes": size,
                "sha256": hashlib.sha256(payload_json.encode("utf-8")).hexdigest(),
                "top_level_keys": list(payload)[:30] if isinstance(payload, dict) else [],
                "note": "Datos detallados normalizados en tablas del pipeline",
            }, ensure_ascii=False)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO api_raw_payload
                    (run_id, source_name, ticker, endpoint, request_parameters,
                     response_payload, http_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (run_id, source_name, ticker, endpoint, params_json, payload_json, http_status),
                )
    except Exception as exc:
        print(f"RAW {source_name} {ticker or ''} omitido: {exc}")
