import json
import os
from google import genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

RECOMMENDATION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "main_reason": {"type": "string"},
        "positive_factors": {"type": "string"},
        "risk_factors": {"type": "string"},
        "comparison_comment": {"type": "string"},
        "model_comment": {"type": "string"},
    },
    "required": ["summary","main_reason","positive_factors","risk_factors","comparison_comment","model_comment"],
    "additionalProperties": False,
}


def enabled():
    return bool(GEMINI_API_KEY)


def _client():
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY no configurada")
    return genai.Client(api_key=GEMINI_API_KEY)


def explain_best_asset(best, all_assets):
    comparison = "\n".join(
        f"{a['ranking_position']}. {a['ticker']} | final={float(a['final_score'] or 0):.4f} | "
        f"prob={float(a['probability_favorable'] or 0):.4f} | sent={float(a['sentiment_score'] or 0):.4f} | "
        f"backtest={float(a['backtesting_return'] or 0):.4f} | mdd={float(a['max_drawdown'] or 0):.4f} | "
        f"auc={float(a['roc_auc'] or 0):.4f}"
        for a in all_assets
    )
    prompt = f"""
Eres un agente explicativo de un proyecto académico de análisis predictivo de mercados financieros.
El motor cuantitativo YA eligió el activo número 1. No cambies esa elección y no inventes datos.
Explica por qué el activo ganador obtuvo el mayor final_score frente a los demás usando exclusivamente los indicadores suministrados.
No presentes el resultado como garantía de rendimiento ni como asesoría financiera personalizada.

MEJOR ACTIVO DEL MOTOR
Ticker: {best['ticker']}
Empresa: {best.get('company_name') or best['ticker']}
Final score: {float(best['final_score'] or 0):.4f}
Decisión: {best.get('decision_label') or ''}

COMPARACIÓN COMPLETA
{comparison}

REQUISITOS
- main_reason: razón cuantitativa principal.
- positive_factors: factores favorables del ganador.
- risk_factors: riesgos observados, especialmente drawdown y calidad del modelo.
- comparison_comment: por qué quedó por encima de los siguientes activos.
- model_comment: máximo tres frases aptas para una tarjeta de Power BI.
- Devuelve únicamente JSON según el esquema.
""".strip()

    # Mantener vivo el cliente durante toda la petición evita el error client has been closed.
    with _client() as client:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_json_schema": RECOMMENDATION_SCHEMA,
                "temperature": 0.2,
            },
        )
        text = response.text
    if not text:
        raise RuntimeError("Gemini devolvió una respuesta vacía")
    return json.loads(text)
