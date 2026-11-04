-- Diagnóstico no destructivo de InversIA V4 (Railway/MySQL).
-- Ejecutar por bloques en MySQL -> Database -> Query.

SELECT id,status,total_assets,started_at,completed_at,notes
FROM analysis_runs ORDER BY id DESC LIMIT 12;

-- Cobertura por run: se esperan 10 snapshots y 10 opiniones en una ejecución nueva.
SELECT r.id AS run_id, r.status, r.total_assets,
       (SELECT COUNT(DISTINCT s.ticker) FROM asset_kpi_snapshot s WHERE s.run_id=r.id) AS snapshots,
       (SELECT COUNT(DISTINCT o.ticker) FROM ai_asset_opinion o WHERE o.run_id=r.id) AS opinions,
       (SELECT COUNT(*) FROM ai_recommendation a WHERE a.run_id=r.id) AS general_ia
FROM analysis_runs r ORDER BY r.id DESC LIMIT 12;

-- Consulta del run que debe publicar Power BI sin mezclar resultados parciales.
SELECT r.id AS published_run_id
FROM analysis_runs r
WHERE r.status IN ('COMPLETED','COMPLETED_WITH_WARNINGS')
  AND r.total_assets > 0
  AND (SELECT COUNT(DISTINCT s.ticker) FROM asset_kpi_snapshot s WHERE s.run_id=r.id)=r.total_assets
  AND (SELECT COUNT(DISTINCT o.ticker) FROM ai_asset_opinion o WHERE o.run_id=r.id)=r.total_assets
  AND EXISTS (SELECT 1 FROM ai_recommendation a WHERE a.run_id=r.id)
ORDER BY r.id DESC LIMIT 1;

-- Tablas Yahoo ampliadas: perfiles por ejecución y eventos históricos.
SELECT run_id,COUNT(*) AS yahoo_profiles FROM yahoo_company_profile GROUP BY run_id ORDER BY run_id DESC;
SELECT ticker,event_type,COUNT(*) AS eventos FROM yahoo_corporate_actions
GROUP BY ticker,event_type ORDER BY ticker,event_type;

-- Diagnóstico de almacenamiento; NO borrar tablas ni registros sin respaldo.
SELECT table_name,engine,table_rows,
       ROUND((data_length+index_length)/1024/1024,2) AS total_mb
FROM information_schema.tables WHERE table_schema=DATABASE()
ORDER BY (data_length+index_length) DESC;
