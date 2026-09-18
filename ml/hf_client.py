import os
import requests

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "ProsusAI/finbert")
HF_API_BASE = os.getenv(
    "HF_API_BASE",
    "https://router.huggingface.co/hf-inference/models",
).rstrip("/")


def analyze_sentiment(text):
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN no configurado")

    url = f"{HF_API_BASE}/{HF_MODEL}"
    response = requests.post(
        url,
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={"inputs": text[:4000]},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(str(data["error"]))
    if isinstance(data, list) and data and isinstance(data[0], list):
        data = data[0]
    if not isinstance(data, list):
        raise RuntimeError(f"Respuesta FinBERT inesperada: {data}")

    scores = {str(x["label"]).lower(): float(x["score"]) for x in data}
    pos = scores.get("positive", 0.0)
    neu = scores.get("neutral", 0.0)
    neg = scores.get("negative", 0.0)
    candidates = {"positive": pos, "neutral": neu, "negative": neg}
    label = max(candidates, key=candidates.get)

    return {
        "positive": pos,
        "neutral": neu,
        "negative": neg,
        "label": label,
        "score": pos - neg,
    }
