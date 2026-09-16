import os
from flask import Flask, jsonify, request

from database.db import fetch_all, fetch_one
from database.init_db import init_database

app = Flask(__name__)
APP_NAME = os.getenv("APP_NAME", "Business Analytics - Inversiones a Largo Plazo")
API_KEY = os.getenv("PBI_API_KEY", "")


def _authorized():
    if not API_KEY:
        return True
    supplied = request.headers.get("X-API-Key") or request.args.get("api_key")
    return supplied == API_KEY


def _guard():
    if _authorized():
        return None
    return jsonify({"error": "unauthorized"}), 401

from datetime import date, datetime
from decimal import Decimal


def serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Decimal):
        return float(value)

    return value


def serialize_rows(rows):
    return [
        {
            key: serialize_value(value)
            for key, value in row.items()
        }
        for row in rows
    ]


@app.get("/")
def root():
    return jsonify({
        "service": APP_NAME,
        "status": "ok",
        "endpoints": [
            "/api/health",
            "/api/database/health",
            "/api/ranking",
            "/api/predictions",
            "/api/sentiment"
        ]
    })


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": APP_NAME})


@app.get("/api/database/health")
def db_health():
    denied = _guard()
    if denied:
        return denied
    try:
        row = fetch_one("SELECT DATABASE() AS db, VERSION() AS version")
        return jsonify({"status": "ok", "database": row["db"], "mysql_version": row["version"]})
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.get("/api/ranking")
def ranking():
    denied = _guard()
    if denied:
        return denied
    rows = fetch_all("""
        SELECT r.ticker, r.probability_score, r.sentiment_score, r.final_score,
               r.ranking_position, r.calculated_at
        FROM asset_ranking r
        JOIN (
            SELECT ticker, MAX(id) AS max_id
            FROM asset_ranking
            GROUP BY ticker
        ) x ON x.max_id = r.id
        ORDER BY r.final_score DESC
    """)
    return jsonify(rows)


@app.get("/api/predictions")
def predictions():
    denied = _guard()

    if denied:
        return denied

    rows = fetch_all("""
        SELECT
            id,
            ticker,
            prediction_date,
            prediction_horizon_days AS horizon_days,
            probability_favorable,
            predicted_class,
            model,
            created_at
        FROM predictions
        ORDER BY prediction_date DESC, ticker
    """)

    return jsonify(serialize_rows(rows))

@app.get("/api/sentiment")
def sentiment():
    denied = _guard()
    if denied:
        return denied
    rows = fetch_all("""
        SELECT ticker,
               AVG(sentiment_score) AS sentiment_score,
               AVG(positive_score) AS positive_score,
               AVG(neutral_score) AS neutral_score,
               AVG(negative_score) AS negative_score,
               COUNT(*) AS news_count
        FROM sentiment
        WHERE created_at >= NOW() - INTERVAL 30 DAY
        GROUP BY ticker
        ORDER BY sentiment_score DESC
    """)
    return jsonify(rows)


@app.cli.command("init-db")
def init_db_command():
    init_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))
