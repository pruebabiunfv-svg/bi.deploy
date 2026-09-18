import os
from datetime import date, datetime
from decimal import Decimal

from flask import Flask, jsonify, request

from database.db import fetch_all, fetch_one
from database.init_db import init_database

app = Flask(__name__)
APP_NAME = os.getenv("APP_NAME", "Business Analytics - Inversiones a Largo Plazo")
API_KEY = os.getenv("PBI_API_KEY", "")
PUBLIC_ANALYTICS = os.getenv("PUBLIC_ANALYTICS", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _authorized():
    if not API_KEY:
        return True
    supplied = request.headers.get("X-API-Key") or request.args.get("api_key")
    return supplied == API_KEY


def _guard():
    if _authorized():
        return None
    return jsonify({"error": "unauthorized"}), 401


def _analytics_guard():
    if PUBLIC_ANALYTICS:
        return None
    return _guard()


def json_safe(rows):
    output = []
    for row in rows:
        clean = {}
        for key, value in row.items():
            if isinstance(value, Decimal):
                clean[key] = float(value)
            elif isinstance(value, datetime):
                clean[key] = value.isoformat(timespec="seconds")
            elif isinstance(value, date):
                clean[key] = value.isoformat()
            else:
                clean[key] = value
        output.append(clean)
    return output


def _json_rows(sql, params=None):
    return jsonify(json_safe(fetch_all(sql, params)))


@app.get("/")
def root():
    return jsonify(
        {
            "service": APP_NAME,
            "status": "ok",
            "public_analytics": PUBLIC_ANALYTICS,
            "endpoints": [
                "/api/health",
                "/api/database/health",
                "/api/ranking",
                "/api/predictions",
                "/api/prediction-history",
                "/api/sentiment",
                "/api/backtesting",
                "/api/model-metrics",
                "/api/market-history",
                "/api/decisions",
                "/api/ai-comment",
            ],
        }
    )


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
        return jsonify(
            {
                "status": "ok",
                "database": row["db"],
                "mysql_version": row["version"],
            }
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.get("/api/ranking")
def ranking():
    denied = _analytics_guard()
    if denied:
        return denied
    return _json_rows(
        """
        SELECT r.ticker, r.probability_score, r.sentiment_score, r.final_score,
               r.ranking_position, r.calculated_at
        FROM asset_ranking r
        JOIN (
            SELECT ticker, MAX(id) AS max_id
            FROM asset_ranking
            GROUP BY ticker
        ) x ON x.max_id = r.id
        ORDER BY r.ranking_position ASC, r.final_score DESC
        """
    )


@app.get("/api/predictions")
def predictions():
    denied = _analytics_guard()
    if denied:
        return denied
    try:
        return _json_rows(
            """
            SELECT p.id, p.ticker, p.prediction_date, p.horizon_days,
                   p.probability_favorable, p.predicted_class, p.model, p.created_at
            FROM predictions p
            JOIN (
                SELECT ticker, MAX(id) AS max_id
                FROM predictions
                GROUP BY ticker
            ) x ON x.max_id = p.id
            ORDER BY p.probability_favorable DESC
            """
        )
    except Exception as exc:
        app.logger.exception("ERROR /api/predictions")
        return jsonify(
            {"status": "error", "endpoint": "/api/predictions", "error": str(exc)}
        ), 500


@app.get("/api/prediction-history")
def prediction_history():
    denied = _analytics_guard()
    if denied:
        return denied
    limit = min(max(int(request.args.get("limit", "1000")), 1), 10000)
    ticker = (request.args.get("ticker") or "").strip().upper()
    if ticker:
        return _json_rows(
            """
            SELECT id,ticker,prediction_date,horizon_days,probability_favorable,
                   predicted_class,model,created_at
            FROM prediction_history
            WHERE ticker=%s
            ORDER BY id DESC
            LIMIT %s
            """,
            (ticker, limit),
        )
    return _json_rows(
        """
        SELECT id,ticker,prediction_date,horizon_days,probability_favorable,
               predicted_class,model,created_at
        FROM prediction_history
        ORDER BY id DESC
        LIMIT %s
        """,
        (limit,),
    )


@app.get("/api/sentiment")
def sentiment():
    denied = _analytics_guard()
    if denied:
        return denied
    return _json_rows(
        """
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
        """
    )


@app.get("/api/backtesting")
def backtesting():
    denied = _analytics_guard()
    if denied:
        return denied
    return _json_rows(
        """
        SELECT b.id,b.ticker,b.start_date,b.end_date,b.total_return,
               b.benchmark_return,b.max_drawdown,b.hit_rate,b.trades_count,b.created_at
        FROM backtesting b
        INNER JOIN (
            SELECT ticker, MAX(id) AS max_id
            FROM backtesting
            GROUP BY ticker
        ) latest ON latest.max_id=b.id
        ORDER BY b.total_return DESC
        """
    )


@app.get("/api/model-metrics")
def model_metrics():
    denied = _analytics_guard()
    if denied:
        return denied
    return _json_rows(
        """
        SELECT m.id,m.ticker,m.metric_date,m.accuracy,m.precision_score,
               m.recall_score,m.f1_score,m.roc_auc,m.samples,m.folds,
               m.validation_method,m.created_at
        FROM model_metrics m
        INNER JOIN (
            SELECT ticker, MAX(id) AS max_id
            FROM model_metrics
            GROUP BY ticker
        ) latest ON latest.max_id=m.id
        ORDER BY m.roc_auc DESC
        """
    )


@app.get("/api/market-history")
def market_history():
    denied = _analytics_guard()
    if denied:
        return denied
    ticker = (request.args.get("ticker") or "").strip().upper()
    if ticker:
        return _json_rows(
            """
            SELECT ticker,price_date,open_price,high_price,low_price,close_price,volume,source
            FROM market_data
            WHERE ticker=%s
            ORDER BY price_date
            """,
            (ticker,),
        )
    return _json_rows(
        """
        SELECT ticker,price_date,open_price,high_price,low_price,close_price,volume,source
        FROM market_data
        ORDER BY ticker,price_date
        """
    )


@app.get("/api/decisions")
def decisions():
    denied = _analytics_guard()
    if denied:
        return denied
    return _json_rows(
        """
        SELECT d.id,d.ticker,d.ranking_position,d.prediction_probability,
               d.sentiment_score,d.ranking_score,d.backtesting_return,
               d.backtesting_score,d.model_confidence,d.model_f1,d.risk_score,
               d.final_score,d.decision_label,d.explanation,d.model_version,
               d.decision_date,d.created_at
        FROM decision_log d
        INNER JOIN (
            SELECT ticker, MAX(id) AS max_id
            FROM decision_log
            GROUP BY ticker
        ) latest ON latest.max_id=d.id
        ORDER BY d.final_score DESC
        """
    )


@app.get("/api/ai-comment")
def ai_comment():
    denied = _analytics_guard()
    if denied:
        return denied
    return _json_rows(
        """
        SELECT c.id,c.ticker,c.decision_id,c.decision_label,c.final_score,
               c.summary,c.main_reason,c.positive_factors,c.risk_factors,
               c.model_comment,c.model_name,c.created_at
        FROM ai_decision_comment c
        INNER JOIN (
            SELECT ticker, MAX(id) AS max_id
            FROM ai_decision_comment
            GROUP BY ticker
        ) latest ON latest.max_id=c.id
        ORDER BY c.final_score DESC
        """
    )


@app.cli.command("init-db")
def init_db_command():
    init_database()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT") or "5000"))
