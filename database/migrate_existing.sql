USE inversion_bi;

-- Solo para una BD creada con una versión anterior.
-- Si una columna ya existe, omite manualmente ese ALTER.
ALTER TABLE backtesting
ADD COLUMN max_drawdown DECIMAL(12,6) NULL AFTER benchmark_return;

ALTER TABLE backtesting
ADD COLUMN trades_count INT NOT NULL DEFAULT 0 AFTER hit_rate;

-- Las tablas nuevas se crean automáticamente con: python -m database.init_db
