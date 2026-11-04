"""Genera y persiste una opinión Gemini por ticker para un run completo.

Integrar desde jobs/run_pipeline.py, dentro de main(), antes de finish_analysis_run.
"""

import json
import os
import time

from database.db import fetch_all, get_connection
from ml.gemini_agent import GEMINI_MODEL, _client, enabled
from ml.gemini_retry import generate_with_retry


OPINION_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "strengths": {"type": "string"},
        "risks": {"type": "string"},
        "model_comment": {"type": "string"},
    },
    "required": ["summary", "strengths", "risks", "model_comment"],
    "additionalProperties": False,
}


def _snapshot(run_id):
    return fetch_all(
        """
        SELECT ticker,company_name,market_date,probability_favorable,
               sentiment_score,news_count,backtesting_return,benchmark_return,
               max_drawdown,hit_rate,roc_auc,f1_score,final_score,
               ranking_position,decision_label
        FROM asset_kpi_snapshot
        WHERE run_id=%s
        ORDER BY ranking_position,ticker
        """,
        (run_id,),
    )


def _explain(client, asset):
    data = json.dumps(asset, ensure_ascii=False, default=str)
    prompt = (
        "Eres analista de un proyecto académico de mercados financieros. "
        "Explica exclusivamente la empresa y los indicadores proporcionados. "
        "No inventes datos, cotizaciones ni noticias; los NULL significan datos "
        "no disponibles, no valores cero. Distingue backtesting histórico de "
        "probabilidades predictivas. No cambies el ranking y no garantices "
        "rentabilidad ni presentes asesoría financiera personalizada. "
        "Redacta en español: summary (resultado de la empresa), strengths "
        "(fortalezas), risks (riesgos y limitaciones del modelo), model_comment "
        "(síntesis de 2 a 4 frases para Power BI). Devuelve JSON según el esquema. "
        f"\nINDICADORES:\n{data}"
    )
    response = generate_with_retry(client,
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json",
            "response_json_schema": OPINION_SCHEMA,
            "temperature": 0.2,
        },
    )
    if not response.text:
        raise RuntimeError("Gemini devolvió texto vacío")
    result = json.loads(response.text)
    for field in OPINION_SCHEMA["required"]:
        if not isinstance(result.get(field), str):
            raise ValueError(f"Campo ausente o inválido: {field}")
    return result


def _save(run_id, ticker, result):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO ai_asset_opinion
                    (run_id,ticker,summary,strengths,risks,model_comment,model_name)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE
                    summary=VALUES(summary),
                    strengths=VALUES(strengths),
                    risks=VALUES(risks),
                    model_comment=VALUES(model_comment),
                    model_name=VALUES(model_name),
                    created_at=CURRENT_TIMESTAMP
                """,
                (
                    run_id,
                    ticker,
                    result["summary"],
                    result["strengths"],
                    result["risks"],
                    result["model_comment"],
                    GEMINI_MODEL,
                ),
            )


def main(run_id):
    """Devuelve (opiniones_generadas, total_de_empresas_de_este_run)."""
    assets = _snapshot(run_id)
    total = len(assets)
    if not assets:
        print(f"Opiniones IA: sin activos en run={run_id}")
        return 0, 0
    # En ejecuciones reanudadas solamente se vuelven a pedir opiniones faltantes.
    present = {row["ticker"] for row in fetch_all(
        "SELECT ticker FROM ai_asset_opinion WHERE run_id=%s", (run_id,)
    )}
    present.intersection_update({row["ticker"] for row in assets})
    if len(present) >= total:
        return len(present), total
    if not enabled():
        print("Opiniones IA: GEMINI_API_KEY no configurada")
        return len(present), total

    generated = len(present)
    with _client() as client:
        for asset in assets:
            ticker = asset["ticker"]
            if ticker in present:
                continue
            try:
                result = _explain(client, asset)
                _save(run_id, ticker, result)
                generated += 1
                print(f"Opinión IA por empresa: {ticker} OK")
            except Exception as exc:
                print(f"Opinión IA por empresa: {ticker} ERROR: {exc}")
            if generated < total:
                time.sleep(max(0, float(os.getenv("GEMINI_BETWEEN_CALLS_SECONDS", "1.5"))))
    return generated, total


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Reintentar opiniones pendientes del mismo run")
    parser.add_argument("--run-id", type=int, required=True)
    run_id = parser.parse_args().run_id
    print("Opiniones pendientes:", main(run_id))
