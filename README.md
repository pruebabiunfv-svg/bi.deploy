# InversIA V4 — inversiones a largo plazo, 10 empresas y Power BI

Proyecto Python + Flask + MySQL para Railway. Integra precios de Yahoo Finance,
fundamentales SEC EDGAR, macro FRED, noticias GDELT, sentimiento FinBERT,
XGBoost, backtesting y explicaciones Gemini. Las visualizaciones se construyen
en Power BI Desktop utilizando los scripts `powerbi/`.

## Diez empresas del dashboard

| Ticker | Empresa |
|---|---|
| AAPL | Apple |
| MSFT | Microsoft |
| NVDA | NVIDIA |
| AMZN | Amazon |
| GOOGL | Alphabet/Google |
| META | Meta |
| TSLA | Tesla |
| NFLX | Netflix |
| AMD | Advanced Micro Devices |
| ORCL | Oracle |

`SPY` se guarda únicamente como benchmark del S&P 500 y **no** participa en el
ranking de las diez empresas. `QQQ` tampoco figura como empresa seleccionable.
El universo es configurable con `TICKERS`, pero debe contener exactamente diez
símbolos diferentes; actualizar la variable existente en **Railway Worker**.

## Cambios de V4

1. Los cuatro endpoints centrales de Power BI comparten el **mismo** `run_id`.
   Solo se publica un run `COMPLETED`/`COMPLETED_WITH_WARNINGS` que contenga
   todos los snapshots, todas las opiniones individuales **y** la recomendación
   general. Un run parcial, como el 31 con tres opiniones de siete, no sustituye
   al último run íntegro, como el 30.
2. `/api/dashboard/status` informa del último run, del publicado, recuentos,
   publicación atrasada o aún no disponible. Nunca inventa opiniones.
3. Reintentos limitados de Gemini ante HTTP 429/503; se puede recuperar
   manualmente un run con opiniones pendientes sin duplicar filas.
4. Bloqueo MySQL `GET_LOCK()` para impedir dos workers concurrentes.
5. Auditoría JSON **acotada por defecto**: grandes respuestas SEC/Yahoo se
   representan por tamaño/hash, mientras los datos normalizados se conservan
   completos. No se eliminan filas históricas automáticamente.
6. Yahoo Finance: además de OHLCV diario hasta 10 años, se obtienen perfiles
   empresariales, capitalización, múltiplos, beta, dividendos y splits mediante
   `yfinance`. Si falla su cuota, el pipeline continúa con advertencias. El
   histórico de precios mantiene respaldo `yfinance` si falla el chart HTTP.
7. Nuevos archivos M/DAX para perfiles y acciones corporativas.

## Tablas nuevas

- `yahoo_company_profile`: perfil y valoración **por `run_id` y ticker**.
- `yahoo_corporate_actions`: dividendos y splits históricos por ticker/fecha.

Todas las tablas anteriores, su histórico y claves permanecen intactos.
`database.init_db` crea solo lo que falte e incorpora las migraciones existentes.

## Arquitectura

```
Yahoo Finance (OHLCV, perfiles, dividendos, splits)   SEC EDGAR   FRED   GDELT
             |                                           |         |      |
             +-----------> MySQL (datos normalizados y auditoría acotada) <--+
                                       |
                             XGBoost + FinBERT
                                       |
                       Walk-Forward y motor de decisiones
                                       |
                            asset_kpi_snapshot
                                       |
                          +------------+-----------+
                          |                        |
                  Gemini por empresa        Gemini comparativo
                   ai_asset_opinion          ai_recommendation
                          |                        |
                          +------------+-----------+
                                       |
                        Publicación íntegra por run_id
                                       |
                              Flask API / Power BI
```

## Instalación local

Necesita Python 3.12, MySQL y conexión a Internet para las fuentes externas.

```bash
python -m venv .venv
# Activar el entorno para su sistema operativo.
pip install -r requirements-worker.txt
python -m database.init_db
python -m jobs.run_pipeline
```

Para servir la API:

```bash
pip install -r requirements-api.txt
python -m api.app
```

Copie las variables de `.env.example` a su entorno de manera segura. Python no
carga `.env` automáticamente: use el panel de Variables de Railway o exporte
las variables antes de ejecutar. Nunca publique credenciales reales.

## Railway

Lea [docs/RAILWAY.md](docs/RAILWAY.md). Asegúrese de establecer en el worker:

```env
TICKERS=AAPL,MSFT,NVDA,AMZN,GOOGL,META,TSLA,NFLX,AMD,ORCL
BENCHMARK_TICKER=SPY
MARKET_PERIOD=10y
YAHOO_ENRICHMENT_ENABLED=true
RAW_AUDIT_MODE=bounded
RAW_PAYLOAD_MAX_BYTES=65536
GEMINI_MODEL=gemini-2.5-flash
```

La variable `GEMINI_MODEL` acepta otro ID válido que su clave permita. La cuota,
errores 429 y acceso varían por modelo/proyecto; no se garantiza un resultado
en todas las llamadas. Los datos Yahoo/yfinance no constituyen un feed con SLA.

## Recuperación de opiniones parciales

Una vez corregidas las cuotas de Gemini, puede volver a solicitar solo las
opiniones faltantes de una ejecución anterior, con el mismo `run_id`:

```bash
python -m jobs.run_company_opinions --run-id 31
python -m jobs.run_best_asset_agent --run-id 31
```

Si esa ejecución representa solo siete activos, sigue siendo histórica; el
primer run de diez deberá generarse ejecutando nuevamente todo el pipeline.
No asigne `run_id` arbitrariamente a los ocho comentarios históricos `NULL`.

## Endpoints principales

| Endpoint | Uso |
|---|---|
| `/api/dashboard/status` | Run reciente y publicado, cobertura IA |
| `/api/dashboard/assets` | KPI y ranking, snapshot íntegro |
| `/api/dashboard/company-opinions` | Una opinión Gemini por empresa |
| `/api/dashboard/recommendation` | Opinión comparativa global |
| `/api/ai-comment` | Alias compatible de la recomendación global |
| `/api/dashboard/companies` | Lista de las empresas publicadas |
| `/api/dashboard/yahoo-profiles` | Datos bursátiles adicionales |
| `/api/dashboard/corporate-actions` | Dividendos y splits históricos |
| `/api/market-history` | Histórico de precios y benchmark |
| `/api/dashboard/runs` | Auditoría de ejecuciones |

Power BI importa las consultas M desde `powerbi/` y las medidas DAX de
`powerbi/Measures.dax`; vea [powerbi/README.txt](powerbi/README.txt).

## Diagnóstico del almacenamiento de Railway

El error MySQL 1114 (`decision_log is full`) puede significar que falta espacio
en el volumen **aunque la tabla `decision_log` ocupe unos pocos KB**.
En el despliegue reportado el volumen era 500 MB. Revise **MySQL Volume →
Metrics**; considere ampliarlo antes de reejecutar pipelines grandes.

El cambio de auditoría reduce el **crecimiento futuro**, pero **no libera** los
~116 MB que los registros `api_raw_payload` antiguos ya ocupaban. Antes de
archivar o eliminar información, haga un backup y evalúe una política formal de
retención; el proyecto no borra los datos existentes.

## Pruebas

```bash
python -m unittest discover -s tests -v
python -m compileall -q api config database jobs ml tests
```

Estas pruebas no requieren servicios externos; el funcionamiento end-to-end
requiere MySQL, cuotas activas de Yahoo/SEC/HF/Gemini, Railway y Power BI Desktop.

> Los resultados de modelos son estimaciones académicas e históricas, no
> recomendaciones financieras personalizadas ni garantías de rentabilidad.
