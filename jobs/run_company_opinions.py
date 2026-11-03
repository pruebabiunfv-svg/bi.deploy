import json

from database.db import fetch_all, get_connection
from ml.gemini_agent import GEMINI_MODEL, enabled, _client


OPINION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "strengths": {"type": "string"},
        "risks": {"type": "string"},
        "model_comment": {"type": "string"}
    },
    "required": [
        "summary",
        "strengths",
        "risks",
        "model_comment"
    ],
    "additionalProperties": False
}


def obtener_empresas(run_id):
    return fetch_all(
        """
        SELECT
            ticker,
            company_name,
            probability_favorable,
            sentiment_score,
            backtesting_return,
            benchmark_return,
            max_drawdown,
            hit_rate,
            roc_auc,
            f1_score,
            final_score,
            ranking_position,
            news_count,
            market_date
        FROM asset_kpi_snapshot
        WHERE run_id = %s
        ORDER BY ranking_position ASC
        """,
        (run_id,)
    )


def crear_opinion(client, empresa):

    datos = json.dumps(
        empresa,
        ensure_ascii=False,
        default=str
    )

    prompt = f"""
Actúa como analista financiero especializado
en inversiones de largo plazo.

Analiza exclusivamente la empresa proporcionada.

DATOS CUANTITATIVOS:
{datos}

INSTRUCCIONES:

1. Explica el resultado del modelo predictivo.
2. Evalúa el sentimiento financiero de las noticias.
3. Interpreta el rendimiento histórico del backtesting.
4. Evalúa el riesgo usando el máximo drawdown.
5. Considera la calidad del modelo mediante ROC-AUC y F1.
6. Explica la posición de la empresa en el ranking.
7. Identifica fortalezas y riesgos verificables.

REGLAS OBLIGATORIAS:

- No inventes indicadores ni noticias.
- Un valor nulo significa información no disponible.
- No garantices rendimientos futuros.
- No cambies la clasificación calculada por el sistema.
- Diferencia resultados históricos de predicciones.
- Usa lenguaje técnico, claro y profesional.
- La opinión es informativa, no asesoría personalizada.

CAMPOS DE RESPUESTA:

summary:
Resumen del resultado de la empresa.

strengths:
Principales fortalezas y fundamentos cuantitativos.

risks:
Riesgos y limitaciones identificados.

model_comment:
Opinión final de 2 a 4 oraciones,
adecuada para visualizar en Power BI.

Devuelve solamente JSON válido.
"""

    respuesta = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": OPINION_SCHEMA,
            "temperature": 0.2
        }
    )

    if not respuesta.text:
        raise RuntimeError("Gemini no devolvió contenido")

    resultado = json.loads(respuesta.text)

    for campo in OPINION_SCHEMA["required"]:
        if not isinstance(resultado.get(campo), str):
            raise ValueError(
                f"Respuesta IA incompleta: {campo}"
            )

    return resultado


def guardar_opinion(run_id, ticker, resultado):

    sql = """
        INSERT INTO ai_asset_opinion
        (
            run_id,
            ticker,
            summary,
            strengths,
            risks,
            model_comment,
            model_name
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)

        ON DUPLICATE KEY UPDATE
            summary = VALUES(summary),
            strengths = VALUES(strengths),
            risks = VALUES(risks),
            model_comment = VALUES(model_comment),
            model_name = VALUES(model_name),
            created_at = CURRENT_TIMESTAMP
    """

    parametros = (
        run_id,
        ticker,
        resultado["summary"],
        resultado["strengths"],
        resultado["risks"],
        resultado["model_comment"],
        GEMINI_MODEL
    )

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, parametros)


def main(run_id):

    empresas = obtener_empresas(run_id)
    total = len(empresas)

    if not empresas:
        print("No hay empresas para analizar")
        return 0, 0

    if not enabled():
        print("Gemini no está configurado")
        return 0, total

    generadas = 0

    with _client() as client:

        for empresa in empresas:

            ticker = empresa["ticker"]

            try:
                opinion = crear_opinion(
                    client,
                    empresa
                )

                guardar_opinion(
                    run_id,
                    ticker,
                    opinion
                )

                generadas += 1

                print(
                    f"Opinión IA generada: {ticker}"
                )

            except Exception as error:
                print(
                    f"Error analizando {ticker}: {error}"
                )

    return generadas, total