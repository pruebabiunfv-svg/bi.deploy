# Railway — despliegue de InversIA V4

## Componentes

1. **MySQL:** persistencia en volumen. Haga backup desde `Backups`.
2. **bi.deploy:** API Flask (`Dockerfile`). Healthcheck `/api/health`.
3. **inversion_worker:** trabajo pesado (`Dockerfile.worker`); sin dominio público.

En ambos servicios use las variables de MySQL de Railway, por ejemplo:

```env
APP_DATABASE=inversion_bi
MYSQLHOST=${{MySQL.RAILWAY_PRIVATE_DOMAIN}}
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=${{MySQL.MYSQL_ROOT_PASSWORD}}
```

No use `ALLOW_LOCAL_MYSQL=true` en Railway. No copie claves a GitHub.

## API

- Dockerfile: `Dockerfile` (en el repositorio raíz).
- Pre-deploy: `python -m database.init_db` (migraciones idempotentes).
- Start: predeterminado (`start.sh`).
- `PUBLIC_ANALYTICS=true` para lectura pública de los endpoints del tablero;
  si el informe es privado, establezca `PUBLIC_ANALYTICS=false`, configure
  `PBI_API_KEY` y envíe la clave en cabecera X-API-Key desde Power BI.

## Worker

- Variable `RAILWAY_DOCKERFILE_PATH=Dockerfile.worker`.
- No programar varios workers simultáneos. El código usa `GET_LOCK()` y
  rechaza una segunda ejecución mientras la primera esté activa.
- Ejecute por demanda o mediante programación externa, considerando el tiempo
  y la cuota de 10 empresas. No lance continuamente en cada reinicio si no
  desea repetir solicitudes/cargos.

```env
TICKERS=AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,NFLX,AMD,ORCL
BENCHMARK_TICKER=SPY
MARKET_PERIOD=10y
YAHOO_ENRICHMENT_ENABLED=true
RAW_AUDIT_MODE=bounded
RAW_PAYLOAD_MAX_BYTES=65536
PREDICTION_HORIZON_DAYS=126
NEWS_PER_TICKER=15
FINBERT_MAX_NEW_PER_TICKER=6
HF_MAX_ATTEMPTS=3
WALK_FORWARD_FOLDS=4
GDELT_DELAY_SECONDS=3
GEMINI_MAX_ATTEMPTS=3
GEMINI_RETRY_BASE_SECONDS=4
GEMINI_BETWEEN_CALLS_SECONDS=1.5
GEMINI_MODEL=gemini-2.5-flash
```

Adicionalmente, configure `GEMINI_API_KEY`, `HF_TOKEN`, `FRED_API_KEY` si
dispone de ellos y un `SEC_USER_AGENT` propio con contacto real. No se incluyen
claves en el ZIP.

Si Railway tiene todavía `TICKERS=...SPY,QQQ`, **cámbielo** por el listado de
diez empresas. Las variables existentes tienen prioridad sobre el default.

## Comprobación tras el despliegue

1. Cree/actualice tablas con `python -m database.init_db`.
2. Ejecute **una sola vez** el worker para las diez empresas.
3. Consulte `/api/dashboard/runs` y `/api/dashboard/status`.
4. El estado `dashboard_ready=true` y `latest_expected_assets=10` con
   `latest_company_opinions=10` confirma un snapshot íntegro reciente.
5. Si hubo cuota Gemini, el último publicado puede ser más antiguo;
   `published_is_older=true` lo señala. No significa que se hayan perdido datos.
6. Revise los endpoints `/api/dashboard/assets`, `.../company-opinions` y
   `.../recommendation`; todos deberán contener **el mismo** `run_id`.
7. Actualice Power BI Desktop / servicio según su política de actualización.

## Volumen MySQL y datos existentes

- MySQL Volume → `Metrics`: ver uso real; `Settings` → `Live resize`: ampliar
  capacidad si se acerca al máximo (con backup previo).
- `RAW_AUDIT_MODE=bounded` evita nuevo crecimiento excesivo de JSON raw, sin
  borrar los históricos. Normalización Yahoo/SEC se conserva.
- **No ejecutar TRUNCATE, DROP ni Wipe Volume** sin exportación, validación y
  autorización expresa. SQL de verificación solo lectura en `SQL_VERIFY_V4.sql`.

## Recuperación de opiniones

Para un run incompleto por cuota Gemini y ya registrado en MySQL:

```bash
python -m jobs.run_company_opinions --run-id 31
python -m jobs.run_best_asset_agent --run-id 31
```

El comando solo genera tickers faltantes, usando la clave del worker. La
recomendación general puede reintentarse por separado con el segundo comando.
Ambos usan los datos históricos ya guardados para el `run_id` especificado.
