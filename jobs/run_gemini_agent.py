"""Compatibilidad: ejecuta el agente del mejor activo sobre la última ejecución disponible."""
from database.db import get_connection
from jobs.run_best_asset_agent import main as run_best_asset_agent


def main():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(id) AS run_id FROM analysis_runs")
            row = cur.fetchone()
    run_id = (row or {}).get("run_id")
    if not run_id:
        print("Gemini Agent: no existen analysis_runs")
        return
    return run_best_asset_agent(int(run_id))


if __name__ == "__main__":
    main()
