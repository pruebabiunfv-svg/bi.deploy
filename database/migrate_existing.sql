USE inversion_bi;

-- Este archivo documenta los cambios principales de la versión V2.
-- La forma recomendada es ejecutar `python -m database.init_db`, que aplica
-- estas migraciones de manera idempotente sin fallar si una columna ya existe.

-- Nuevos conceptos: analysis_runs, api_raw_payload, sec_company_facts,
-- asset_kpi_snapshot y ai_recommendation se crean automáticamente desde schema.sql.

-- Si se desea inspeccionar manualmente la estructura final:
SHOW TABLES;
DESCRIBE analysis_runs;
DESCRIBE asset_kpi_snapshot;
DESCRIBE ai_recommendation;
DESCRIBE api_raw_payload;
DESCRIBE sec_company_facts;
