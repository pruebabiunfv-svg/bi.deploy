from database.db import get_connection
from ml.decision_engine import calculate_decision

MODEL_VERSION = "decision-engine-v2"


def get_latest_assets():
    sql = """
    SELECT
        p.ticker,
        p.probability_favorable,
        COALESCE(s.sentiment_score, 0) AS sentiment_score,
        COALESCE(r.final_score, p.probability_favorable, 0.5) AS ranking_score,
        COALESCE(r.ranking_position, 0) AS ranking_position,
        COALESCE(b.total_return, 0) AS backtesting_return,
        COALESCE(b.max_drawdown, 0.30) AS max_drawdown,
        COALESCE(m.roc_auc, 0.50) AS model_confidence,
        COALESCE(m.f1_score, 0.00) AS model_f1
    FROM predictions p
    INNER JOIN (
        SELECT ticker, MAX(id) AS max_id
        FROM predictions
        GROUP BY ticker
    ) lp ON lp.max_id = p.id
    LEFT JOIN (
        SELECT ticker, AVG(sentiment_score) AS sentiment_score
        FROM sentiment
        WHERE created_at >= NOW() - INTERVAL 30 DAY
        GROUP BY ticker
    ) s ON s.ticker = p.ticker
    LEFT JOIN asset_ranking r
        ON r.id = (
            SELECT MAX(r2.id)
            FROM asset_ranking r2
            WHERE r2.ticker = p.ticker
        )
    LEFT JOIN backtesting b
        ON b.id = (
            SELECT MAX(b2.id)
            FROM backtesting b2
            WHERE b2.ticker = p.ticker
        )
    LEFT JOIN model_metrics m
        ON m.id = (
            SELECT MAX(m2.id)
            FROM model_metrics m2
            WHERE m2.ticker = p.ticker
        )
    ORDER BY COALESCE(r.final_score, p.probability_favorable) DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def save_decision(asset, result):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO decision_log
                (
                    ticker,
                    ranking_position,
                    prediction_probability,
                    sentiment_score,
                    ranking_score,
                    backtesting_return,
                    backtesting_score,
                    model_confidence,
                    model_f1,
                    risk_score,
                    final_score,
                    decision_label,
                    explanation,
                    model_version
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    asset["ticker"],
                    int(asset.get("ranking_position") or 0),
                    float(asset.get("probability_favorable") or 0.0),
                    float(asset.get("sentiment_score") or 0.0),
                    float(asset.get("ranking_score") or 0.5),
                    float(asset.get("backtesting_return") or 0.0),
                    result["backtesting_score"],
                    float(asset.get("model_confidence") or 0.5),
                    float(asset.get("model_f1") or 0.0),
                    abs(float(asset.get("max_drawdown") or 0.0)),
                    result["final_score"],
                    result["decision"],
                    result["explanation"],
                    MODEL_VERSION,
                ),
            )


def main():
    assets = get_latest_assets()
    print(f"Decision Engine: {len(assets)} activos")

    for asset in assets:
        result = calculate_decision(
            ranking_score=asset.get("ranking_score"),
            backtesting_return=asset.get("backtesting_return"),
            confidence=asset.get("model_confidence"),
            risk=asset.get("max_drawdown"),
        )
        save_decision(asset, result)
        print(
            f"Decision {asset['ticker']}: "
            f"{result['decision']} score={result['final_score']:.4f}"
        )


if __name__ == "__main__":
    main()
