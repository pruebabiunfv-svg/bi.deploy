# Railway - despliegue completo

## Servicios

- `MySQL`: persistencia.
- `bi.deploy`: API Flask/Gunicorn.
- `inversion-worker`: ETL, FinBERT, XGBoost, Walk-Forward, Backtesting, Decision Engine y Gemini.

## MySQL

Variables referenciadas recomendadas:

```env
APP_DATABASE=inversion_bi
MYSQLHOST=${{MySQL.RAILWAY_PRIVATE_DOMAIN}}
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=${{MySQL.MYSQL_ROOT_PASSWORD}}
```

La base `inversion_bi` persiste entre redeploys mientras no se elimine el servicio/volumen MySQL ni se ejecuten DROP/TRUNCATE.

## bi.deploy

- Source: mismo repositorio GitHub.
- Dockerfile: `Dockerfile`.
- Pre-deploy: `python -m database.init_db`.
- Custom Start Command: vacío.
- Healthcheck: `/api/health`.
- Public Networking: habilitado.

Variables:

```env
APP_NAME=Business Analytics - Inversiones a Largo Plazo
APP_DATABASE=inversion_bi
MYSQLHOST=${{MySQL.RAILWAY_PRIVATE_DOMAIN}}
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=${{MySQL.MYSQL_ROOT_PASSWORD}}
PUBLIC_ANALYTICS=true
PBI_API_KEY=
```

Cuando `PUBLIC_ANALYTICS=true`, los endpoints analíticos son públicos y solo lectura. No se expone MySQL.

## inversion-worker

- Source: mismo repositorio.
- Variable: `RAILWAY_DOCKERFILE_PATH=Dockerfile.worker`.
- Pre-deploy: vacío.
- Custom Start: vacío.
- No necesita dominio público.

Variables:

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
FRED_API_KEY=...
SEC_USER_AGENT=ProyectoUniversitario/1.0 correo@example.com
HF_TOKEN=...
HF_MODEL=ProsusAI/finbert
HF_API_BASE=https://router.huggingface.co/hf-inference/models
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-3.8-flash
```

El contenedor ejecuta `python -m jobs.run_pipeline`.

## Orden del pipeline

1. Inicialización/migración de BD.
2. Yahoo Finance.
3. FRED.
4. SEC EDGAR.
5. GDELT + FinBERT.
6. XGBoost + prediction_history.
7. Walk-Forward + model_metrics.
8. Backtesting + Maximum Drawdown.
9. Ranking.
10. Decision Engine.
11. Gemini Agent.

Gemini falla de forma aislada: si la API no está disponible, el worker conserva los resultados cuantitativos.

## Power BI

Con `PUBLIC_ANALYTICS=true`, elegir autenticación `Anónimo` y usar los archivos `powerbi/PowerQuery_*.m`.
