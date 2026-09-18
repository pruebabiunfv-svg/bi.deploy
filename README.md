# Sistema BI de Inversión + XGBoost + FinBERT + Walk-Forward + Gemini

Versión integrada para Railway, MySQL y Power BI.

## Flujo

1. Yahoo Finance -> histórico de mercado (10 años por defecto).
2. FRED -> indicadores macroeconómicos.
3. SEC EDGAR -> fundamentales.
4. GDELT -> noticias financieras.
5. FinBERT (Hugging Face Inference) -> sentimiento.
6. XGBoost -> probabilidad de rendimiento favorable.
7. Walk-Forward Validation -> Accuracy, Precision, Recall, F1 y ROC-AUC.
8. Backtesting -> rentabilidad, benchmark, hit rate y Maximum Drawdown.
9. Decision Engine -> score final y clasificación académica.
10. Gemini Agent -> explica por qué el motor eligió esa clasificación.
11. Flask REST API -> endpoints para Power BI.

## KPI incluidos

- Mejor activo del modelo: `decision_log.final_score`.
- Probabilidad favorable: `predictions.probability_favorable`.
- Sentimiento: `sentiment.sentiment_score`.
- Rentabilidad de backtesting: `backtesting.total_return`.
- Maximum Drawdown: `backtesting.max_drawdown`.
- Ranking: `decision_log.final_score` / `asset_ranking`.
- Rendimiento histórico: `market_data.close_price` por fecha.
- Confianza del modelo: `model_metrics.roc_auc` (Walk-Forward).
- Comentario IA: `ai_decision_comment.model_comment`.

## Históricos adicionales

Cada ejecución del worker conserva nuevos registros en:

- `prediction_history`
- `asset_ranking`
- `backtesting`
- `model_metrics`
- `decision_log`
- `ai_decision_comment` (una explicación por decisión)

`market_data`, FRED y fundamentales usan actualización por clave para evitar duplicados. GDELT comprueba URL/título antes de insertar una noticia.

## Railway

### API (`bi.deploy`)

Usa `Dockerfile`.

Pre-deploy:

```bash
python -m database.init_db
```

Custom Start Command: vacío.

Variables mínimas:

```env
APP_DATABASE=inversion_bi
MYSQLHOST=${{MySQL.RAILWAY_PRIVATE_DOMAIN}}
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=${{MySQL.MYSQL_ROOT_PASSWORD}}
PUBLIC_ANALYTICS=true
```

### Worker (`inversion-worker`)

Usa:

```env
RAILWAY_DOCKERFILE_PATH=Dockerfile.worker
```

Variables sugeridas:

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

El `Dockerfile.worker` ejecuta:

```bash
python -m jobs.run_pipeline
```

## API para Power BI

Con `PUBLIC_ANALYTICS=true`, estos endpoints son de lectura anónima:

- `/api/ranking`
- `/api/predictions`
- `/api/prediction-history`
- `/api/sentiment`
- `/api/backtesting`
- `/api/model-metrics`
- `/api/market-history`
- `/api/decisions`
- `/api/ai-comment`

`/api/database/health` sigue protegido por `PBI_API_KEY` si se configura.

En `powerbi/` hay consultas M para cada tabla y `Measures.dax` con los KPI.
Reemplaza `https://TU-API.up.railway.app` por tu dominio Railway.

## Seguridad

No subas claves reales a GitHub. Configura FRED, Hugging Face, Gemini y MySQL únicamente como Railway Variables. Si una clave fue expuesta en una captura o chat, rótala antes del despliegue.

## Nota académica

El `Decision Engine` y Gemini se plantean como apoyo analítico y explicación del modelo. Gemini no recalcula las métricas ni modifica el score cuantitativo.
