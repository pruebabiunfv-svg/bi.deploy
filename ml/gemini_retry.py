"""Reintentos moderados ante cuotas temporales / indisponibilidad del proveedor IA."""

import os
import time


def _retryable(error):
    message = str(error).lower()
    return any(token in message for token in (
        "429", "503", "502", "504", "resource_exhausted", "unavailable",
        "rate limit", "quota exceeded", "deadline_exceeded", "temporarily",
    ))


def generate_with_retry(client, *, model, contents, config, sleep=time.sleep):
    retries = max(1, int(os.getenv("GEMINI_MAX_ATTEMPTS", "3")))
    base_seconds = max(0.0, float(os.getenv("GEMINI_RETRY_BASE_SECONDS", "4")))
    for attempt in range(retries):
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except Exception as exc:
            if attempt + 1 == retries or not _retryable(exc):
                raise
            delay = min(60.0, base_seconds * (2 ** attempt))
            print(f"Gemini respuesta transitoria, intento {attempt + 1}/{retries}, pausa {delay:.1f}s: {exc}")
            sleep(delay)
