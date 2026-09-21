from database.db import get_connection


def build_snapshot(run_id):
    """Consolida una sola fila por empresa y ejecución para Power BI."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM asset_kpi_snapshot WHERE run_id=%s", (run_id,))
            cur.execute(
                """
                SELECT
                    a.ticker,
                    a.company_name,
                    p.probability_favorable,
                    p.predicted_class,
                    COALESCE(s.sentiment_score, 0) AS sentiment_score,
                    COALESCE(s.positive_score, 0) AS positive_score,
                    COALESCE(s.neutral_score, 0) AS neutral_score,
                    COALESCE(s.negative_score, 0) AS negative_score,
                    COALESCE(s.news_count, 0) AS news_count,
                    b.total_return,
                    b.benchmark_return,
                    b.max_drawdown,
                    b.hit_rate,
                    b.trades_count,
                    m.accuracy,
                    m.precision_score,
                    m.recall_score,
                    m.f1_score,
                    m.roc_auc,
                    r.final_score AS ranking_score,
                    d.final_score,
                    d.decision_label,
                    md.market_date,
                    md.close_price
                FROM assets a
                LEFT JOIN prediction_history p
                    ON p.id = (
                        SELECT MAX(p2.id) FROM prediction_history p2
                        WHERE p2.run_id=%s AND p2.ticker=a.ticker
                    )
                LEFT JOIN (
                    SELECT ticker,
                           AVG(sentiment_score) AS sentiment_score,
                           AVG(positive_score) AS positive_score,
                           AVG(neutral_score) AS neutral_score,
                           AVG(negative_score) AS negative_score,
                           COUNT(*) AS news_count
                    FROM sentiment
                    WHERE created_at >= NOW() - INTERVAL 30 DAY
                    GROUP BY ticker
                ) s ON s.ticker=a.ticker
                LEFT JOIN backtesting b
                    ON b.id = (
                        SELECT MAX(b2.id) FROM backtesting b2
                        WHERE b2.run_id=%s AND b2.ticker=a.ticker
                    )
                LEFT JOIN model_metrics m
                    ON m.id = (
                        SELECT MAX(m2.id) FROM model_metrics m2
                        WHERE m2.run_id=%s AND m2.ticker=a.ticker
                    )
                LEFT JOIN asset_ranking r
                    ON r.id = (
                        SELECT MAX(r2.id) FROM asset_ranking r2
                        WHERE r2.run_id=%s AND r2.ticker=a.ticker
                    )
                LEFT JOIN decision_log d
                    ON d.id = (
                        SELECT MAX(d2.id) FROM decision_log d2
                        WHERE d2.run_id=%s AND d2.ticker=a.ticker
                    )
                LEFT JOIN (
                    SELECT md1.ticker, md1.price_date AS market_date, md1.close_price
                    FROM market_data md1
                    INNER JOIN (
                        SELECT ticker, MAX(price_date) AS max_date
                        FROM market_data GROUP BY ticker
                    ) x ON x.ticker=md1.ticker AND x.max_date=md1.price_date
                ) md ON md.ticker=a.ticker
                WHERE a.active=1
                """,
                (run_id, run_id, run_id, run_id, run_id),
            )
            rows = cur.fetchall()

            for row in rows:
                if row.get("final_score") is None:
                    # Si un activo no terminó el modelo, no se mezcla con otra ejecución.
                    continue
                label = "NEUTRAL"
                s = float(row.get("sentiment_score") or 0.0)
                if s > 0.15:
                    label = "POSITIVE"
                elif s < -0.15:
                    label = "NEGATIVE"

                cur.execute(
                    """
                    INSERT INTO asset_kpi_snapshot
                    (run_id,ticker,company_name,market_date,close_price,
                     probability_favorable,predicted_class,sentiment_score,sentiment_label,
                     positive_score,neutral_score,negative_score,news_count,
                     backtesting_return,benchmark_return,max_drawdown,hit_rate,trades_count,
                     accuracy,precision_score,recall_score,f1_score,roc_auc,
                     ranking_score,final_score,decision_label)
                    VALUES
                    (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                     %s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        run_id,row["ticker"],row["company_name"],row["market_date"],row["close_price"],
                        row["probability_favorable"],row["predicted_class"],row["sentiment_score"],label,
                        row["positive_score"],row["neutral_score"],row["negative_score"],row["news_count"],
                        row["total_return"],row["benchmark_return"],row["max_drawdown"],row["hit_rate"],row["trades_count"],
                        row["accuracy"],row["precision_score"],row["recall_score"],row["f1_score"],row["roc_auc"],
                        row["ranking_score"],row["final_score"],row["decision_label"],
                    ),
                )

    calculate_ranking(run_id)


def calculate_ranking(run_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ticker, final_score
                FROM asset_kpi_snapshot
                WHERE run_id=%s
                ORDER BY final_score DESC, ticker ASC
                """,
                (run_id,),
            )
            rows = cur.fetchall()
            for position, row in enumerate(rows, start=1):
                is_best = 1 if position == 1 else 0
                cur.execute(
                    """
                    UPDATE asset_kpi_snapshot
                    SET ranking_position=%s, is_best=%s
                    WHERE run_id=%s AND ticker=%s
                    """,
                    (position, is_best, run_id, row["ticker"]),
                )
                cur.execute(
                    """
                    UPDATE decision_log
                    SET ranking_position=%s
                    WHERE run_id=%s AND ticker=%s
                    """,
                    (position, run_id, row["ticker"]),
                )
    print(f"Snapshot KPI run={run_id}: {len(rows)} activos")
