# Despliegue en Railway — versión Lite corregida

## Servicios
- `bi.prueba`: API Flask + Gunicorn usando `Dockerfile`
- `MySQL`: base administrada de Railway
- `inversion-worker` (opcional): ETL/XGBoost usando `Dockerfile.worker`

## 1. Variables del servicio `bi.prueba`
Configúralas en Railway > `bi.prueba` > Variables. No subas `.env` a GitHub.

```env
FLASK_ENV=production
APP_NAME=Business Analytics - Inversiones a Largo Plazo
DEMO_MODE=false
PREDICTION_HORIZON_DAYS=126
TICKERS=AAPL,MSFT,NVDA,AMZN,GOOGL,SPY,QQQ
MARKET_PERIOD=5y
APP_DATABASE=inversion_bi
MYSQLHOST=${{MySQL.MYSQLHOST}}
MYSQLPORT=${{MySQL.MYSQLPORT}}
MYSQLUSER=${{MySQL.MYSQLUSER}}
MYSQLPASSWORD=${{MySQL.MYSQLPASSWORD}}
PBI_API_KEY=CAMBIAR_POR_UNA_CLAVE_SEGURA
```

No definas `PORT` manualmente en Railway. Railway lo inyecta al iniciar el servicio.

## 2. Settings de `bi.prueba`
- Builder: Dockerfile
- Dockerfile: `Dockerfile`
- Pre-deploy Command: `python -m database.init_db`
- Custom Start Command: **vacío**
  - Si Railway obliga a usar uno, usa solamente: `/app/start.sh`
- Healthcheck Path: `/api/health`
- Public Networking: habilitado

`start.sh` toma `PORT` de Railway y arranca Gunicorn. No uses expresiones `${PORT:-5000}` directamente en el Custom Start Command de un servicio Dockerfile.

## 3. Base de datos
El pre-deploy ejecuta:

```bash
python -m database.init_db
```

y crea/verifica `inversion_bi` y sus tablas mediante la red privada de Railway.

## 4. Worker
Crea un segundo servicio desde el mismo repositorio y usa:

```env
RAILWAY_DOCKERFILE_PATH=Dockerfile.worker
```

Copia las variables MySQL y agrega las credenciales externas necesarias (FRED/Hugging Face/etc.) solo en Variables de Railway.

## 5. Power BI
Usa `powerbi/PowerQuery_Ranking.m` y `powerbi/PowerQuery_Predictions.m`, sustituyendo `https://TU-API.up.railway.app` por el dominio de `bi.prueba`.
