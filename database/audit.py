import json
from database.db import get_connection


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
    """Best-effort audit storage. It must never stop the analytical pipeline."""
    try:
        params_json = json.dumps(request_parameters or {}, ensure_ascii=False, default=str)
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
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
