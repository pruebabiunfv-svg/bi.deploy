# Railway — versión V2

Servicios actuales recomendados:

- `MySQL`: persistencia.
- `bi.deploy`: API Flask/Gunicorn.
- `inversion_worker`: ETL, modelos, snapshot KPI y Gemini.

## MySQL / red privada

```env
APP_DATABASE=inversion_bi
MYSQLHOST=${{MySQL.RAILWAY_PRIVATE_DOMAIN}}
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=${{MySQL.MYSQL_ROOT_PASSWORD}}
```

No configure `ALLOW_LOCAL_MYSQL=true` en Railway. La V2 falla explícitamente si falta `MYSQLHOST`, evitando conectarse por error a `127.0.0.1`.

## bi.deploy

- Dockerfile: `Dockerfile`
- Pre-deploy: `python -m database.init_db`
- Custom Start Command: vacío
- Healthcheck: `/api/health`

```env
APP_NAME=Business Analytics - Inversiones a Largo Plazo
APP_DATABASE=inversion_bi
MYSQLHOST=${{MySQL.RAILWAY_PRIVATE_DOMAIN}}
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=${{MySQL.MYSQL_ROOT_PASSWORD}}
PUBLIC_ANALYTICS=true
```

## inversion_worker

- Mismo repo GitHub.
- `RAILWAY_DOCKERFILE_PATH=Dockerfile.worker`
- Sin dominio público.
- Pre-deploy y Custom Start vacíos.

```env
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

## Pipeline V2

1. Crea `analysis_runs.run_id`.
2. Guarda datos raw/normalizados de APIs.
3. XGBoost y `prediction_history` con `run_id`.
4. Walk-Forward y `model_metrics` con `run_id`.
5. Backtesting y drawdown con `run_id`.
6. Decision Engine con `run_id`.
7. Construye `asset_kpi_snapshot`, una fila por empresa.
8. Recalcula ranking por `final_score`.
9. Gemini explica solamente `is_best=1` comparándolo con los demás.
10. Cierra el run como `COMPLETED` o `COMPLETED_WITH_WARNINGS`.

## Power BI

Usar:

- `/api/dashboard/assets`
- `/api/dashboard/recommendation`
- `/api/market-history`
- `/api/dashboard/runs` (opcional)

Con `PUBLIC_ANALYTICS=true`: autenticación **Anónimo**.
