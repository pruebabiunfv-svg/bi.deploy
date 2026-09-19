import json
import os

from google import genai


GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    ""
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.8-flash"
)


DECISION_SCHEMA = {
    "type": "object",

    "properties": {

        "summary": {
            "type": "string"
        },

        "main_reason": {
            "type": "string"
        },

        "positive_factors": {
            "type": "string"
        },

        "risk_factors": {
            "type": "string"
        },

        "model_comment": {
            "type": "string"
        },
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
    return bool(
        GEMINI_API_KEY
    )


def get_client():

    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY no configurada"
        )

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


def build_prompt(data):

    return f"""
Eres un agente explicativo de un proyecto académico
de análisis predictivo de mercados financieros.

No debes recalcular las métricas.
No debes inventar valores.
No debes modificar la clasificación calculada
por el motor cuantitativo.

Debes explicar en español y de forma concisa por qué
el sistema asignó esta clasificación al activo.

DATOS CALCULADOS POR EL SISTEMA

Ticker:
{data['ticker']}

Clasificación:
{data['decision_label']}

Score final:
{data['final_score']:.4f}

Posición del ranking:
{data['ranking_position']}

Probabilidad favorable XGBoost:
{data['prediction_probability']:.4f}

Sentimiento FinBERT:
{data['sentiment_score']:.4f}

Rentabilidad del backtesting:
{data['backtesting_return']:.4f}

Maximum Drawdown:
{data['risk_score']:.4f}

ROC-AUC Walk-Forward:
{data['model_confidence']:.4f}

F1 Walk-Forward:
{data['model_f1']:.4f}

INSTRUCCIONES

Explica cuál fue el factor principal de la clasificación.

Describe brevemente los factores favorables.

Describe los riesgos principales.

Diferencia la probabilidad de rendimiento favorable
de la calidad predictiva del modelo.

No presentes el resultado como garantía
de rendimiento futuro.

El campo model_comment debe tener como máximo
tres frases y estar diseñado para mostrarse
directamente en un dashboard de Power BI.
""".strip()


def explain_decision(data):

    prompt = build_prompt(
        data
    )

    # El contexto mantiene vivo al cliente
    # durante toda la petición.
    with get_client() as client:

        response = (
            client.models.generate_content(
                model=GEMINI_MODEL,

                contents=prompt,

                config={
                    "response_mime_type":
                        "application/json",

                    "response_json_schema":
                        DECISION_SCHEMA,

                    "temperature": 0.2,
                },
            )
        )

        response_text = (
            response.text
        )

    if not response_text:

        raise RuntimeError(
            "Gemini devolvió "
            "una respuesta vacía"
        )

    try:

        return json.loads(
            response_text
        )

    except json.JSONDecodeError as exc:

        raise RuntimeError(
            "Gemini devolvió JSON inválido: "
            f"{response_text[:500]}"
        ) from exc