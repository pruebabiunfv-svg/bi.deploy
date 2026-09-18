USE inversion_bi;

SELECT 'market_data' AS tabla, COUNT(*) AS registros FROM market_data
UNION ALL SELECT 'financial_news', COUNT(*) FROM financial_news
UNION ALL SELECT 'sentiment', COUNT(*) FROM sentiment
UNION ALL SELECT 'predictions', COUNT(*) FROM predictions
UNION ALL SELECT 'prediction_history', COUNT(*) FROM prediction_history
UNION ALL SELECT 'asset_ranking', COUNT(*) FROM asset_ranking
UNION ALL SELECT 'backtesting', COUNT(*) FROM backtesting
UNION ALL SELECT 'model_metrics', COUNT(*) FROM model_metrics
UNION ALL SELECT 'decision_log', COUNT(*) FROM decision_log
UNION ALL SELECT 'ai_decision_comment', COUNT(*) FROM ai_decision_comment;

SELECT ticker, probability_favorable, prediction_date, created_at
FROM predictions
ORDER BY probability_favorable DESC;

SELECT ticker, total_return, benchmark_return, max_drawdown, hit_rate, trades_count, created_at
FROM backtesting
ORDER BY id DESC
LIMIT 20;

SELECT ticker, accuracy, precision_score, recall_score, f1_score, roc_auc, samples, folds, created_at
FROM model_metrics
ORDER BY id DESC
LIMIT 20;

SELECT ticker, ranking_position, prediction_probability, sentiment_score,
       backtesting_return, model_confidence, risk_score, final_score,
       decision_label, created_at
FROM decision_log
ORDER BY id DESC
LIMIT 20;

SELECT ticker, decision_label, final_score, model_comment, model_name, created_at
FROM ai_decision_comment
ORDER BY id DESC
LIMIT 20;
