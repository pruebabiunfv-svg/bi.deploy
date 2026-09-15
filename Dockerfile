FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt

COPY api ./api
COPY database ./database
COPY ml ./ml
COPY start.sh ./start.sh
RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]
