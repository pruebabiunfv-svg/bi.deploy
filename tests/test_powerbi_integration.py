"""Pruebas aisladas que no requieren MySQL, Google API ni Power BI Desktop.

Ejecutar con: python -m unittest discover -s tests -v
"""

import ast
import importlib.util
import json
from pathlib import Path
import re
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class IntegrationStructureTests(unittest.TestCase):
    def test_pipeline_opinions_inside_main_before_finish(self):
        code = ast.parse((ROOT / "jobs/run_pipeline.py").read_text(encoding="utf-8"))
        main = next(n for n in code.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = [n for n in ast.walk(main) if isinstance(n, ast.Call)]
        generate = [n for n in calls if isinstance(n.func, ast.Name) and n.func.id == "generate_company_opinions"]
        finish = [n for n in calls if isinstance(n.func, ast.Name) and n.func.id == "finish_analysis_run"]
        self.assertEqual(len(generate), 1)
        self.assertTrue(any(call.lineno > generate[0].lineno for call in finish))
        outside_calls = [n for n in code.body if isinstance(n, ast.Try)]
        self.assertFalse(outside_calls, "No debe haber try/except a nivel raíz después de main()")

    def test_schema_and_flask_endpoint(self):
        ddl = (ROOT / "database/schema.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS ai_asset_opinion", ddl)
        self.assertIn("UNIQUE KEY uq_asset_opinion_run_ticker (run_id, ticker)", ddl)
        api = (ROOT / "api/app.py").read_text(encoding="utf-8")
        self.assertIn('@app.get("/api/dashboard/company-opinions")', api)
        self.assertIn("FROM ai_asset_opinion o", api)

    def test_queries_and_measures_present(self):
        pbi = ROOT / "powerbi"
        expected = {
            "DashboardAssets": "PowerQuery_DashboardAssets.m",
            "AIRecommendation": "PowerQuery_AIRecommendation.m",
            "CompanyOpinions": "PowerQuery_CompanyOpinions.m",
            "MarketHistory": "PowerQuery_MarketHistory.m",
        }
        for name, filename in expected.items():
            source = (pbi / filename).read_text(encoding="utf-8")
            self.assertIn("Web.Contents(BaseUrl", source, name)
            self.assertNotIn("TU-API", source, name)

        dax = (pbi / "Measures.dax").read_text(encoding="utf-8")
        for measure in [
            "SelectorEmpresa =", "Periodos =", "Probabilidad Favorable =",
            "Rentabilidad Backtesting =", "Drawdown Maximo =", "Puntuacion Ranking =",
            "Indice Precio Normalizado =", "Opinion IA Empresa =",
            "Comentario IA Mejor Activo =", "Mejor Activo IA =",
        ]:
            self.assertIn(measure, dax)
        names = re.findall(r"^([A-Za-zÁÉÍÓÚáéíóúÑñ][^\n]*?)\s*=\s*$", dax, re.MULTILINE)
        self.assertEqual(len(names), len(set(names)), "Medidas DAX con nombres duplicados")

    def test_benchmark_not_required_in_ranking(self):
        source = (ROOT / "jobs/run_pipeline.py").read_text(encoding="utf-8")
        self.assertIn('BENCHMARK_TICKER = os.getenv("BENCHMARK_TICKER", "SPY")', source)
        self.assertIn('BENCHMARK_TICKER not in TICKERS', source)
        self.assertIn('load_yahoo(BENCHMARK_TICKER)', source)

    def test_publication_requires_complete_kpis_opinions_and_general_ia(self):
        api = (ROOT / "api/app.py").read_text(encoding="utf-8")
        self.assertIn('COUNT(DISTINCT s.ticker)', api)
        self.assertIn('COUNT(DISTINCT o.ticker)', api)
        self.assertIn('EXISTS (SELECT 1 FROM ai_recommendation', api)
        for endpoint in ["status", "yahoo-profiles", "corporate-actions", "companies"]:
            self.assertIn(f'/api/dashboard/{endpoint}', api)

    def test_yahoo_migration_and_ten_companies(self):
        ddl = (ROOT / "database/schema.sql").read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS yahoo_company_profile", ddl)
        self.assertIn("CREATE TABLE IF NOT EXISTS yahoo_corporate_actions", ddl)
        sys.path.insert(0, str(ROOT))
        try:
            from config.assets import DEFAULT_TICKERS, SEC_CIK
        finally:
            sys.path.remove(str(ROOT))
        self.assertEqual(len(DEFAULT_TICKERS), 10)
        self.assertNotIn("SPY", DEFAULT_TICKERS)
        self.assertNotIn("QQQ", DEFAULT_TICKERS)
        self.assertTrue(all(t in SEC_CIK for t in DEFAULT_TICKERS))
        docker = (ROOT / "Dockerfile.worker").read_text(encoding="utf-8")
        self.assertIn("COPY config ./config", docker)
        req = (ROOT / "requirements-worker.txt").read_text(encoding="utf-8")
        self.assertIn("yfinance", req)

    def test_raw_payload_bounded(self):
        source = (ROOT / "database/audit.py").read_text(encoding="utf-8")
        self.assertIn('RAW_AUDIT_MODE', source)
        self.assertIn('original_size_bytes', source)
        self.assertIn('single_flight_pipeline', source)


class CompanyOpinionTests(unittest.TestCase):
    def test_generates_and_saves_company_specific_opinion(self):
        sample = {
            "ticker": "AMZN", "company_name": "Amazon.com, Inc.",
            "probability_favorable": 0.55, "final_score": 0.61,
            "ranking_position": 2,
        }
        saved = []

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def execute(self, sql, values):
                saved.append((sql, values))

        class FakeConnection:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def cursor(self):
                return FakeCursor()

        class FakeModels:
            @staticmethod
            def generate_content(model, contents, config):
                assert "AMZN" in contents
                assert config["response_mime_type"] == "application/json"
                return types.SimpleNamespace(text=json.dumps({
                    "summary": "Resumen", "strengths": "Fortalezas",
                    "risks": "Riesgos", "model_comment": "Comentario",
                }))

        class FakeClient:
            models = FakeModels()

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

        db = types.ModuleType("database.db")
        db.fetch_all = lambda sql, args: ([] if "SELECT ticker FROM ai_asset_opinion" in sql else [sample])
        db.get_connection = FakeConnection

        gemini = types.ModuleType("ml.gemini_agent")
        gemini.GEMINI_MODEL = "fake-test-model"
        gemini.enabled = lambda: True
        gemini._client = FakeClient

        with patch.dict(sys.modules, {"database.db": db, "ml.gemini_agent": gemini}):
            location = ROOT / "jobs/run_company_opinions.py"
            spec = importlib.util.spec_from_file_location("isolated_opinions", location)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            generated, total = module.main(123)

        self.assertEqual((generated, total), (1, 1))
        self.assertEqual(len(saved), 1)
        self.assertIn("INSERT INTO ai_asset_opinion", saved[0][0])
        self.assertEqual(saved[0][1][0:2], (123, "AMZN"))


if __name__ == "__main__":
    unittest.main()
