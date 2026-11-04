# Sistema BI de Inversión V2 — KPI coherentes por empresa + Gemini 

## Actualización V3 — Power BI con opinión individual por empresa (04/11/2026)

- **Sí se mantiene Flask, MySQL, XGBoost, FinBERT y Gemini.** No cambia la arquitectura de despliegue.
- El pipeline ahora ejecuta `jobs.run_company_opinions` dentro de `main()`, después de la opinión global y antes de cerrar `run_id`. Se corrigió el error de alcance `notes is not defined`.
- Nueva tabla `ai_asset_opinion` (una fila por `run_id` y `ticker`) y endpoint `/api/dashboard/company-opinions`.
- Power BI importa cuatro consultas principales: `DashboardAssets`, `AIRecommendation`, `CompanyOpinions`, `MarketHistory`. El archivo `powerbi/Measures.dax` fue sustituido por fórmulas interactivas V3.
- Los filtros desconectados `SelectorEmpresa` y `Periodos` permiten actualizar tarjetas/histórico/opinión individual manteniendo el ranking global completo.
- `BENCHMARK_TICKER=SPY` carga por separado el histórico de referencia si SPY no compite en `TICKERS`, sin alterar el ganador ni el número de empresas del ranking.
- **El selector de período afecta a la curva histórica**, no al horizonte XGBoost. La opinión IA es una explicación ya generada para el run; seleccionar otra empresa no ejecuta Gemini de nuevo.
- Instrucciones de construcción de la página y formato exacto en `powerbi/README.txt`. Validación estática en `tests/test_powerbi_integration.py`; requiere pruebas adicionales con Railway y Power BI Desktop.


Esta versión corrige el problema de Power BI donde **Mejor activo**, **Ranking**, **Sentimiento**, **Backtesting** y otros KPI podían provenir de tickers o ejecuciones diferentes.

## Cambio principal

Cada ejecución del worker crea un `run_id` en `analysis_runs`. Al finalizar los modelos, se genera `asset_kpi_snapshot`, con **una fila consolidada por activo y por ejecución**. Esa tabla es la fuente principal del dashboard.

Flujo:

```text
APIs -> tablas RAW/normalizadas -> XGBoost/FinBERT -> Walk-Forward/Backtesting
     -> Decision Engine -> asset_kpi_snapshot -> Power BI
                                      |
                                      -> mejor final_score -> Gemini -> ai_recommendation
```

## Tablas nuevas / mejoradas

- `analysis_runs`: identifica cada ejecución completa.
- `api_raw_payload`: conserva JSON original de Yahoo, FRED, SEC y GDELT para auditoría.
- `sec_company_facts`: almacena conceptos XBRL de SEC con mayor granularidad.
- `asset_kpi_snapshot`: una fila por empresa con todos los KPI de la misma ejecución.
- `ai_recommendation`: comentario Gemini **solo del mejor activo** del mismo run.
- `market_data`: agrega `adj_close`, `currency`, `exchange_name`.
- `economic_indicators`: agrega metadatos FRED (`realtime_*`, `units`, `frequency`).
- `financial_news`: agrega metadatos GDELT (`domain`, `language`, `source_country`, `social_image`, `seen_at`).
- históricos ML (`prediction_history`, `backtesting`, `model_metrics`, `asset_ranking`, `decision_log`) incluyen `run_id`.

## Regla de consistencia

El orden final se calcula exclusivamente con:

```text
asset_kpi_snapshot.final_score DESC
```

Por tanto:

```text
ranking_position = 1 <=> is_best = 1 <=> Mejor Activo IA
```

Gemini **no vuelve a elegir** el activo. Lee todos los activos del mismo `run_id` y explica por qué el #1 quedó por encima del resto.

## Power BI recomendado

Use principalmente:

- `/api/dashboard/assets` -> consulta `DashboardAssets`
- `/api/dashboard/recommendation` -> `AIRecommendation`
- `/api/market-history` -> `MarketHistory`
- `/api/dashboard/runs` -> opcional, auditoría

Los endpoints anteriores se conservan para auditoría/compatibilidad, pero no deben mezclarse para construir las tarjetas actuales.

En `powerbi/`:

- `PowerQuery_DashboardAssets.m`
- `PowerQuery_AIRecommendation.m`
- `PowerQuery_MarketHistory.m`
- `PowerQuery_AnalysisRuns.m`
- `Measures.dax`

`Measures.dax` incluye `DimActivo`, medidas por empresa seleccionada y medidas globales del mejor activo.

### Modelo

```text
DimActivo[Ticker] 1 -> * DashboardAssets[ticker]
DimActivo[Ticker] 1 -> * MarketHistory[ticker]
```

Use `DimActivo[Empresa]` como slicer. Cuando seleccione Microsoft, todos los KPI de empresa mostrarán Microsoft. El panel global de IA seguirá mostrando el mejor activo del sistema.

## Railway

### API `bi.deploy`

```env
APP_DATABASE=inversion_bi
MYSQLHOST=${{MySQL.RAILWAY_PRIVATE_DOMAIN}}
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=${{MySQL.MYSQL_ROOT_PASSWORD}}
PUBLIC_ANALYTICS=true
```

Pre-deploy:

```bash
python -m database.init_db
```

### Worker `inversion_worker`

```env
RAILWAY_DOCKERFILE_PATH=Dockerfile.worker
APP_DATABASE=inversion_bi
MYSQLHOST=${{MySQL.RAILWAY_PRIVATE_DOMAIN}}
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=${{MySQL.MYSQL_ROOT_PASSWORD}}

TICKERS=AAPL,MSFT,NVDA,AMZN,GOOGL,SPY,QQQ
MARKET_PERIOD=10y
PREDICTION_HORIZON_DAYS=126
NEWS_PER_TICKER=25
WALK_FORWARD_FOLDS=4
GDELT_DELAY_SECONDS=3

FRED_API_KEY=...
SEC_USER_AGENT=ProyectoUniversitario/1.0 correo@example.com
HF_TOKEN=...
HF_MODEL=ProsusAI/finbert
HF_API_BASE=https://router.huggingface.co/hf-inference/models
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.8-flash
```

El pipeline ahora controla 429 de GDELT con reintentos y espera configurable.

## Validación

Después del deploy ejecute `docs/SQL_VERIFY_KPI.sql`. Debe existir exactamente un `is_best=1` en el último run y `ai_recommendation.ticker` debe coincidir con ese ticker.

## Seguridad

No incluya claves reales en GitHub. Mantenga las credenciales en Railway Variables y rote cualquier clave que se haya expuesto previamente.
