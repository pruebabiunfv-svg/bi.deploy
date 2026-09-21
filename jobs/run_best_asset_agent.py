from database.db import get_connection
from ml.gemini_agent import GEMINI_MODEL, enabled, explain_best_asset


def get_snapshot(run_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT * FROM asset_kpi_snapshot
                WHERE run_id=%s
                ORDER BY ranking_position ASC
                """,
                (run_id,),
            )
            return cur.fetchall()


def save_recommendation(run_id, best, result):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_recommendation
                (run_id,ticker,final_score,decision_label,summary,main_reason,
                 positive_factors,risk_factors,comparison_comment,model_comment,model_name)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                  ticker=VALUES(ticker),final_score=VALUES(final_score),
                  decision_label=VALUES(decision_label),summary=VALUES(summary),
                  main_reason=VALUES(main_reason),positive_factors=VALUES(positive_factors),
                  risk_factors=VALUES(risk_factors),comparison_comment=VALUES(comparison_comment),
                  model_comment=VALUES(model_comment),model_name=VALUES(model_name),
                  created_at=CURRENT_TIMESTAMP
                """,
                (
                    run_id,best["ticker"],best["final_score"],best["decision_label"],
                    result["summary"],result["main_reason"],result["positive_factors"],
                    result["risk_factors"],result["comparison_comment"],
                    result["model_comment"],GEMINI_MODEL,
                ),
            )

            # Compatibilidad con /api/ai-comment de la versión anterior.
            cur.execute(
                "SELECT id FROM decision_log WHERE run_id=%s AND ticker=%s ORDER BY id DESC LIMIT 1",
                (run_id, best["ticker"]),
            )
            decision = cur.fetchone()
            cur.execute("DELETE FROM ai_decision_comment WHERE run_id=%s", (run_id,))
            cur.execute(
                """
                INSERT INTO ai_decision_comment
                (run_id,ticker,decision_id,decision_label,final_score,summary,main_reason,
                 positive_factors,risk_factors,model_comment,model_name)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    run_id,best["ticker"],(decision or {}).get("id"),best["decision_label"],best["final_score"],
                    result["summary"],result["main_reason"],result["positive_factors"],
                    result["risk_factors"],result["model_comment"],GEMINI_MODEL,
                ),
            )


def main(run_id):
    assets = get_snapshot(run_id)
    if not assets:
        print(f"Gemini Best Agent run={run_id}: snapshot vacío")
        return False
    if not enabled():
        print("Gemini Best Agent omitido: GEMINI_API_KEY no configurada")
        return False
    best = assets[0]
    result = explain_best_asset(best, assets)
    save_recommendation(run_id, best, result)
    print(f"Gemini Best Agent: {best['ticker']} OK")
    return True


if __name__ == "__main__":
    raise SystemExit("Ejecuta este módulo desde run_pipeline.py para conservar run_id")
