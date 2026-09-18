import json
import os

from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "main_reason": {"type": "string"},
        "positive_factors": {"type": "string"},
        "risk_factors": {"type": "string"},
        "model_comment": {"type": "string"},
    },
    "required": [
        "summary",
        "main_reason",
        "positive_factors",
        "risk_factors",
        "model_comment",
    ],
    "additionalProperties": False,
}


def enabled():
    return bool(GEMINI_API_KEY)


def get_client():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY no configurada")
    return genai.Client(api_key=GEMINI_API_KEY)


def build_prompt(data):
    return f"""
Eres un agente explicativo de un proyecto académico de análisis predictivo de mercados.
No recalcules las métricas, no inventes datos y no cambies la clasificación del motor cuantitativo.
Tu función es explicar, en español y de forma concisa, por qué el sistema asignó la clasificación indicada.
No presentes el resultado como una garantía ni como asesoría financiera personalizada.

DATOS DEL SISTEMA
Ticker: {data['ticker']}
Clasificación: {data['decision_label']}
Score final: {data['final_score']:.4f}
Posición en ranking: {data['ranking_position']}
Probabilidad favorable XGBoost: {data['prediction_probability']:.4f}
Sentimiento FinBERT: {data['sentiment_score']:.4f}
Rentabilidad backtesting: {data['backtesting_return']:.4f}
Maximum Drawdown: {data['risk_score']:.4f}
ROC-AUC Walk-Forward: {data['model_confidence']:.4f}
F1 Walk-Forward: {data['model_f1']:.4f}

REQUISITOS
- Explica el factor principal que elevó o redujo el score.
- Resume factores favorables y riesgos.
- Distingue probabilidad de rendimiento de calidad predictiva del modelo.
- Máximo tres frases en model_comment.
- Devuelve únicamente JSON con el esquema solicitado.
""".strip()


def explain_decision(data):
    interaction = get_client().interactions.create(
        model=GEMINI_MODEL,
        input=build_prompt(data),
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": DECISION_SCHEMA,
        },
    )
    response_text = getattr(interaction, "output_text", None)
    if not response_text:
        raise RuntimeError("Gemini devolvió una respuesta vacía")
    return json.loads(response_text)
