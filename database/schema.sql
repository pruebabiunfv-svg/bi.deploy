CREATE TABLE IF NOT EXISTS assets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15) NOT NULL UNIQUE,
  company_name VARCHAR(150),
  asset_type VARCHAR(30) DEFAULT 'STOCK',
  active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_data (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15) NOT NULL,
  price_date DATE NOT NULL,
  open_price DECIMAL(18,6),
  high_price DECIMAL(18,6),
  low_price DECIMAL(18,6),
  close_price DECIMAL(18,6),
  volume BIGINT,
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

CREATE TABLE IF NOT EXISTS financial_news (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15),
  title VARCHAR(1000) NOT NULL,
  url VARCHAR(1500),
  published_at DATETIME,
  source VARCHAR(100),
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
  INDEX idx_sentiment_ticker_date (ticker, created_at)
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

CREATE TABLE IF NOT EXISTS backtesting (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15) NOT NULL,
  start_date DATE,
  end_date DATE,
  total_return DECIMAL(12,6),
  benchmark_return DECIMAL(12,6),
  hit_rate DECIMAL(10,6),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS asset_ranking (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ticker VARCHAR(15) NOT NULL,
  probability_score DECIMAL(10,6),
  sentiment_score DECIMAL(10,6),
  final_score DECIMAL(10,6),
  ranking_position INT,
  calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_rank_position_date (ranking_position, calculated_at)
);
