CREATE TABLE IF NOT EXISTS assets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15) NOT NULL UNIQUE,
  company_name VARCHAR(150),
  asset_type VARCHAR(30) DEFAULT 'STOCK',
  active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_runs (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at DATETIME NULL,
  status VARCHAR(30) DEFAULT 'RUNNING',
  market_period VARCHAR(20),
  horizon_days INT,
  model_version VARCHAR(50),
  total_assets INT DEFAULT 0,
  notes TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_run_status (status, completed_at)
);

CREATE TABLE IF NOT EXISTS api_raw_payload (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NULL,
  source_name VARCHAR(30) NOT NULL,
  ticker VARCHAR(15),
  endpoint VARCHAR(500),
  request_parameters JSON,
  response_payload JSON,
  http_status INT,
  fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_raw_run_source (run_id, source_name),
  INDEX idx_raw_ticker (ticker, fetched_at)
);

CREATE TABLE IF NOT EXISTS market_data (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15) NOT NULL,
  price_date DATE NOT NULL,
  open_price DECIMAL(18,6),
  high_price DECIMAL(18,6),
  low_price DECIMAL(18,6),
  close_price DECIMAL(18,6),
  adj_close DECIMAL(18,6),
  volume BIGINT,
  currency VARCHAR(10),
  exchange_name VARCHAR(80),
  source VARCHAR(30),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_market (ticker, price_date),
  INDEX idx_market_ticker_date (ticker, price_date)
);

CREATE TABLE IF NOT EXISTS economic_indicators (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  series_id VARCHAR(50) NOT NULL,
  indicator_name VARCHAR(150),
  period_date DATE NOT NULL,
  value DECIMAL(24,8),
  realtime_start DATE,
  realtime_end DATE,
  units VARCHAR(80),
  frequency VARCHAR(80),
  source VARCHAR(30) DEFAULT 'FRED',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_macro (series_id, period_date)
);

CREATE TABLE IF NOT EXISTS fundamentals (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15) NOT NULL,
  report_date DATE NOT NULL,
  revenue DECIMAL(24,2),
  net_income DECIMAL(24,2),
  total_assets DECIMAL(24,2),
  total_liabilities DECIMAL(24,2),
  equity DECIMAL(24,2),
  eps DECIMAL(18,6),
  source VARCHAR(30) DEFAULT 'SEC',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_fundamental (ticker, report_date)
);

CREATE TABLE IF NOT EXISTS sec_company_facts (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  source_key CHAR(64) NOT NULL UNIQUE,
  ticker VARCHAR(15) NOT NULL,
  taxonomy VARCHAR(30),
  concept VARCHAR(180),
  label VARCHAR(500),
  unit VARCHAR(50),
  start_date DATE,
  end_date DATE,
  value DECIMAL(38,8),
  fiscal_year INT,
  fiscal_period VARCHAR(30),
  form_type VARCHAR(30),
  filed_date DATE,
  accession_number VARCHAR(80),
  frame VARCHAR(80),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_sec_ticker_concept (ticker, concept, end_date)
);

CREATE TABLE IF NOT EXISTS financial_news (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15),
  title VARCHAR(1000) NOT NULL,
  url VARCHAR(1500),
  published_at DATETIME,
  source VARCHAR(100),
  domain VARCHAR(255),
  language VARCHAR(50),
  source_country VARCHAR(100),
  social_image VARCHAR(1500),
  seen_at DATETIME,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_news_ticker_date (ticker, published_at)
);

CREATE TABLE IF NOT EXISTS sentiment (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  news_id BIGINT,
  ticker VARCHAR(15),
  positive_score DECIMAL(10,6),
  neutral_score DECIMAL(10,6),
  negative_score DECIMAL(10,6),
  sentiment_label VARCHAR(20),
  sentiment_score DECIMAL(10,6),
  model VARCHAR(100) DEFAULT 'ProsusAI/finbert',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_sentiment_ticker_date (ticker, created_at),
  INDEX idx_sentiment_news (news_id)
);

CREATE TABLE IF NOT EXISTS predictions (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15) NOT NULL,
  prediction_date DATE NOT NULL,
  horizon_days INT NOT NULL,
  probability_favorable DECIMAL(10,6),
  predicted_class TINYINT,
  model VARCHAR(80) DEFAULT 'XGBoost',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_prediction (ticker, prediction_date, horizon_days)
);

CREATE TABLE IF NOT EXISTS prediction_history (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NULL,
  ticker VARCHAR(15) NOT NULL,
  prediction_date DATE NOT NULL,
  horizon_days INT NOT NULL,
  probability_favorable DECIMAL(10,6),
  predicted_class TINYINT,
  model VARCHAR(80) DEFAULT 'XGBoost',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_prediction_history (ticker, prediction_date, created_at),
  INDEX idx_prediction_run (run_id, ticker)
);

CREATE TABLE IF NOT EXISTS backtesting (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NULL,
  ticker VARCHAR(15) NOT NULL,
  start_date DATE,
  end_date DATE,
  total_return DECIMAL(12,6),
  benchmark_return DECIMAL(12,6),
  max_drawdown DECIMAL(12,6),
  hit_rate DECIMAL(10,6),
  trades_count INT NOT NULL DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_backtesting_ticker (ticker, created_at),
  INDEX idx_backtesting_run (run_id, ticker)
);

CREATE TABLE IF NOT EXISTS model_metrics (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NULL,
  ticker VARCHAR(15) NOT NULL,
  metric_date DATE NOT NULL,
  accuracy DECIMAL(10,6),
  precision_score DECIMAL(10,6),
  recall_score DECIMAL(10,6),
  f1_score DECIMAL(10,6),
  roc_auc DECIMAL(10,6),
  samples INT DEFAULT 0,
  folds INT DEFAULT 0,
  validation_method VARCHAR(50) DEFAULT 'Walk-Forward',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_metrics_ticker_date (ticker, metric_date, created_at),
  INDEX idx_metrics_run (run_id, ticker)
);

CREATE TABLE IF NOT EXISTS asset_ranking (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NULL,
  ticker VARCHAR(15) NOT NULL,
  probability_score DECIMAL(10,6),
  sentiment_score DECIMAL(10,6),
  final_score DECIMAL(10,6),
  ranking_position INT,
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_rank_position_date (ranking_position, calculated_at),
  INDEX idx_rank_ticker_date (ticker, calculated_at),
  INDEX idx_rank_run (run_id, ticker)
);

CREATE TABLE IF NOT EXISTS decision_log (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NULL,
  ticker VARCHAR(15) NOT NULL,
  ranking_position INT,
  prediction_probability DECIMAL(10,6),
  sentiment_score DECIMAL(10,6),
  ranking_score DECIMAL(10,6),
  backtesting_return DECIMAL(12,6),
  backtesting_score DECIMAL(10,6),
  model_confidence DECIMAL(10,6),
  model_f1 DECIMAL(10,6),
  risk_score DECIMAL(10,6),
  final_score DECIMAL(10,6),
  decision_label VARCHAR(40),
  explanation TEXT,
  model_version VARCHAR(50),
  decision_date DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_decision_ticker_date (ticker, decision_date),
  INDEX idx_decision_score (final_score),
  INDEX idx_decision_run (run_id, ticker)
);

CREATE TABLE IF NOT EXISTS ai_decision_comment (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NULL,
  ticker VARCHAR(15) NOT NULL,
  decision_id BIGINT,
  decision_label VARCHAR(40),
  final_score DECIMAL(10,6),
  summary TEXT,
  main_reason TEXT,
  positive_factors TEXT,
  risk_factors TEXT,
  model_comment TEXT,
  model_name VARCHAR(80),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ai_comment_ticker (ticker, created_at),
  INDEX idx_ai_comment_decision (decision_id),
  INDEX idx_ai_comment_run (run_id, ticker)
);

CREATE TABLE IF NOT EXISTS asset_kpi_snapshot (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  ticker VARCHAR(15) NOT NULL,
  company_name VARCHAR(150),
  market_date DATE,
  close_price DECIMAL(18,6),
  probability_favorable DECIMAL(10,6),
  predicted_class TINYINT,
  sentiment_score DECIMAL(10,6),
  sentiment_label VARCHAR(20),
  positive_score DECIMAL(10,6),
  neutral_score DECIMAL(10,6),
  negative_score DECIMAL(10,6),
  news_count INT DEFAULT 0,
  backtesting_return DECIMAL(12,6),
  benchmark_return DECIMAL(12,6),
  max_drawdown DECIMAL(12,6),
  hit_rate DECIMAL(10,6),
  trades_count INT DEFAULT 0,
  accuracy DECIMAL(10,6),
  precision_score DECIMAL(10,6),
  recall_score DECIMAL(10,6),
  f1_score DECIMAL(10,6),
  roc_auc DECIMAL(10,6),
  ranking_score DECIMAL(10,6),
  final_score DECIMAL(10,6),
  ranking_position INT,
  decision_label VARCHAR(40),
  is_best TINYINT(1) DEFAULT 0,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_snapshot (run_id, ticker),
  INDEX idx_snapshot_ticker (ticker, run_id),
  INDEX idx_snapshot_ranking (run_id, ranking_position),
  INDEX idx_snapshot_best (run_id, is_best)
);

CREATE TABLE IF NOT EXISTS ai_recommendation (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  run_id BIGINT NOT NULL,
  ticker VARCHAR(15) NOT NULL,
  final_score DECIMAL(10,6),
  decision_label VARCHAR(40),
  summary TEXT,
  main_reason TEXT,
  positive_factors TEXT,
  risk_factors TEXT,
  comparison_comment TEXT,
  model_comment TEXT,
  model_name VARCHAR(80),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_ai_recommendation_run (run_id),
  INDEX idx_ai_best (ticker, created_at)
);
