# Proyecto de Inversión - Railway Lite

Versión optimizada para ocupar poco espacio en Railway.

## Componentes

- Flask + Gunicorn: API REST
- MySQL + PyMySQL: persistencia
- Yahoo Finance / FRED / SEC EDGAR / GDELT: fuentes
- Hugging Face Inference API + FinBERT: sentimiento sin PyTorch local
- XGBoost: únicamente en worker separado
- Power BI / Power BI Service: dashboard

## Diseño para bajo consumo

La API instala solo 4 paquetes principales: Flask, Gunicorn, PyMySQL y requests.
No incluye Pandas, Scikit-learn, Transformers, Torch ni XGBoost.
El worker instala XGBoost/NumPy solo cuando realmente se necesita para ETL/modelado.
FinBERT corre fuera de Railway mediante Hugging Face Inference API.

## Despliegue rápido

1. Sube el repositorio a GitHub.
2. En Railway crea MySQL.
3. Crea `inversion-api` desde GitHub usando `Dockerfile`.
4. Añade las variables de `.env.example` en Railway.
5. Inicializa la BD: `python -m database.init_db`.
6. Crea `inversion-worker` usando `Dockerfile.worker`.
7. Ejecuta o programa `python jobs/run_pipeline.py`.
8. Usa los archivos M de `powerbi/` para conectarte desde Power BI.

Guía completa: `docs/RAILWAY.md`.

## Prueba local de la API

```bash
pip install -r requirements-api.txt
python -m database.init_db
python -m api.app
```

## Seguridad

Nunca subas `.env`, tokens o contraseñas. Usa Railway Variables.
Si una contraseña fue publicada anteriormente, rótala antes del despliegue.
