from database.db import get_connection
from ml.gemini_agent import GEMINI_MODEL, enabled, explain_decision


def get_latest_decisions():
    sql = """
    SELECT d.*
    FROM decision_log d
    INNER JOIN (
        SELECT ticker, MAX(id) AS max_id
        FROM decision_log
        GROUP BY ticker
    ) latest ON latest.max_id = d.id
    ORDER BY d.final_score DESC
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchall()


def comment_exists(decision_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM ai_decision_comment WHERE decision_id=%s LIMIT 1",
                (decision_id,),
            )
            return cur.fetchone() is not None


def prepare_data(row):
    return {
        "decision_id": int(row["id"]),
        "ticker": row["ticker"],
        "decision_label": row["decision_label"] or "SIN_CLASIFICACION",
        "final_score": float(row["final_score"] or 0.0),
        "ranking_position": int(row["ranking_position"] or 0),
        "prediction_probability": float(row["prediction_probability"] or 0.0),
        "sentiment_score": float(row["sentiment_score"] or 0.0),
        "backtesting_return": float(row["backtesting_return"] or 0.0),
        "risk_score": float(row["risk_score"] or 0.0),
        "model_confidence": float(row["model_confidence"] or 0.5),
        "model_f1": float(row["model_f1"] or 0.0),
    }


def save_comment(data, result):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_decision_comment
                (
                    ticker,
                    decision_id,
                    decision_label,
                    final_score,
                    summary,
                    main_reason,
                    positive_factors,
                    risk_factors,
                    model_comment,
                    model_name
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    data["ticker"],
                    data["decision_id"],
                    data["decision_label"],
                    data["final_score"],
                    result["summary"],
                    result["main_reason"],
                    result["positive_factors"],
                    result["risk_factors"],
                    result["model_comment"],
                    GEMINI_MODEL,
                ),
            )


def main():
    if not enabled():
        print("Gemini Agent omitido: GEMINI_API_KEY no configurada")
        return

    decisions = get_latest_decisions()
    print(f"Gemini Agent: {len(decisions)} decisiones")

    for row in decisions:
        data = prepare_data(row)
        if comment_exists(data["decision_id"]):
            print(f"Gemini {data['ticker']}: comentario ya existe")
            continue

        try:
            result = explain_decision(data)
            save_comment(data, result)
            print(f"Gemini {data['ticker']}: OK")
        except Exception as exc:
            print(f"Gemini {data['ticker']} ERROR: {exc}")


if __name__ == "__main__":
    main()
