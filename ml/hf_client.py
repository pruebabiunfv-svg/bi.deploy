import os
import requests

HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_MODEL = os.getenv("HF_MODEL", "ProsusAI/finbert")
HF_API_BASE = os.getenv("HF_API_BASE", "https://api-inference.huggingface.co/models").rstrip("/")


def analyze_sentiment(text):
    if not HF_TOKEN:
        raise RuntimeError("HF_TOKEN no configurado")
    url = f"{HF_API_BASE}/{HF_MODEL}"
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {HF_TOKEN}"},
        json={"inputs": text[:4000]},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list) and data and isinstance(data[0], list):
        data = data[0]
    scores = {str(x["label"]).lower(): float(x["score"]) for x in data}
    pos = scores.get("positive", 0.0)
    neu = scores.get("neutral", 0.0)
    neg = scores.get("negative", 0.0)
    label = max({"positive": pos, "neutral": neu, "negative": neg}, key=lambda k: {"positive": pos, "neutral": neu, "negative": neg}[k])
    return {
        "positive": pos,
        "neutral": neu,
        "negative": neg,
        "label": label,
        "score": pos - neg,
    }
