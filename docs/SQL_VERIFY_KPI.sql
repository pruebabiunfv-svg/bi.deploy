USE inversion_bi;

-- Últimas ejecuciones
SELECT id, started_at, completed_at, status, market_period, horizon_days, total_assets, notes
FROM analysis_runs
ORDER BY id DESC
LIMIT 10;

-- Snapshot semántico usado por Power BI: debe tener una fila por ticker.
SET @last_run := (
    SELECT MAX(id)
    FROM analysis_runs
    WHERE status IN ('COMPLETED','COMPLETED_WITH_WARNINGS')
);

SELECT @last_run AS latest_dashboard_run;

SELECT
    run_id, ticker, company_name,
    probability_favorable, sentiment_score,
    backtesting_return, max_drawdown,
    roc_auc, f1_score,
    final_score, ranking_position,
    decision_label, is_best
FROM asset_kpi_snapshot
WHERE run_id=@last_run
ORDER BY ranking_position;

-- Debe haber exactamente un mejor activo.
SELECT COUNT(*) AS best_count
FROM asset_kpi_snapshot
WHERE run_id=@last_run AND is_best=1;

-- Gemini debe explicar ese mismo activo.
SELECT run_id,ticker,final_score,decision_label,main_reason,comparison_comment,model_comment,model_name
FROM ai_recommendation
WHERE run_id=@last_run;

-- Verificar que mejor activo y Gemini coinciden.
SELECT
    s.ticker AS best_ticker,
    s.final_score AS best_score,
    a.ticker AS gemini_ticker,
    a.final_score AS gemini_score
FROM asset_kpi_snapshot s
LEFT JOIN ai_recommendation a ON a.run_id=s.run_id
WHERE s.run_id=@last_run AND s.is_best=1;

-- Volumen de datos por fuente / histórico.
SELECT 'market_data' tabla, COUNT(*) registros FROM market_data
UNION ALL SELECT 'sec_company_facts', COUNT(*) FROM sec_company_facts
UNION ALL SELECT 'financial_news', COUNT(*) FROM financial_news
UNION ALL SELECT 'sentiment', COUNT(*) FROM sentiment
UNION ALL SELECT 'prediction_history', COUNT(*) FROM prediction_history
UNION ALL SELECT 'backtesting', COUNT(*) FROM backtesting
UNION ALL SELECT 'model_metrics', COUNT(*) FROM model_metrics
UNION ALL SELECT 'decision_log', COUNT(*) FROM decision_log
UNION ALL SELECT 'api_raw_payload', COUNT(*) FROM api_raw_payload
UNION ALL SELECT 'asset_kpi_snapshot', COUNT(*) FROM asset_kpi_snapshot;
