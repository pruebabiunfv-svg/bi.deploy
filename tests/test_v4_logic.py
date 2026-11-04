"""Pruebas unitarias sin necesidad de Railway, Yahoo ni Gemini reales."""

import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class DataMappingTests(unittest.TestCase):
    def test_gemini_429_retries_then_returns(self):
        from ml.gemini_retry import generate_with_retry

        class FakeModels:
            calls = 0

            def generate_content(self, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError("429 RESOURCE_EXHAUSTED")
                return types.SimpleNamespace(text='{"summary":"OK"}')

        models = FakeModels()
        times = []
        with patch.dict("os.environ", {"GEMINI_MAX_ATTEMPTS": "3", "GEMINI_RETRY_BASE_SECONDS": "2"}):
            result = generate_with_retry(types.SimpleNamespace(models=models),
                                         model="fake", contents="x", config={},
                                         sleep=times.append)
        self.assertEqual(models.calls, 2)
        self.assertEqual(times, [2.0])
        self.assertIn("OK", result.text)

    def test_yahoo_dividend_and_split_are_distinct(self):
        db = types.ModuleType("database.db")
        db.get_connection = lambda: None
        with patch.dict(sys.modules, {"database.db": db}):
            spec = importlib.util.spec_from_file_location("isolated_yahoo", ROOT / "jobs/yahoo_enrichment.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        class Frame:
            empty = False

            @staticmethod
            def iterrows():
                return iter([
                    ("2026-01-02", {"Dividends": 0.25, "Stock Splits": 0}),
                    ("2026-02-03", {"Dividends": 0, "Stock Splits": 4.0}),
                    ("2026-02-04", {"Dividends": float("nan"), "Stock Splits": None}),
                ])

        rows = module.corporate_actions_from_history("AAPL", Frame())
        self.assertEqual([(row[2], row[3]) for row in rows],
                         [("DIVIDEND", 0.25), ("SPLIT", 4.0)])

    def test_raw_payload_bounded_writes_summary_not_large_json(self):
        records = []

        class Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def execute(self, sql, params):
                records.append(params)

        class Conn:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def cursor(self):
                return Cursor()

        database = types.ModuleType("database.db")
        database.get_connection = Conn
        with patch.dict(sys.modules, {"database.db": database}):
            spec = importlib.util.spec_from_file_location("isolated_audit", ROOT / "database/audit.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        with patch.dict("os.environ", {"RAW_AUDIT_MODE": "bounded", "RAW_PAYLOAD_MAX_BYTES": "1024"}):
            module.save_raw_payload(40, "SEC EDGAR", "AAPL", "https://example.invalid", {},
                                    {"facts": "x" * 40000}, 200)
        self.assertEqual(len(records), 1)
        saved = json.loads(records[0][5])
        self.assertTrue(saved["truncated"])
        self.assertGreater(saved["original_size_bytes"], 39000)
        self.assertEqual(len(saved["sha256"]), 64)
        self.assertNotIn("x" * 200, records[0][5])


class ApiPublicationTests(unittest.TestCase):
    def test_all_dashboard_endpoints_use_the_same_published_run(self):
        flask = types.ModuleType("flask")

        class Flask:
            def __init__(self, *_):
                self.cli = types.SimpleNamespace(command=lambda _: lambda f: f)

            def get(self, _):
                return lambda f: f

        flask.Flask = Flask
        flask.jsonify = lambda value: value
        flask.request = types.SimpleNamespace(headers={}, args={})
        db = types.ModuleType("database.db")
        db.fetch_all = lambda *_: []
        db.fetch_one = lambda *_: None
        init_db = types.ModuleType("database.init_db")
        init_db.init_database = lambda: None
        with patch.dict(sys.modules, {
            "flask": flask, "database.db": db,
            "database.init_db": init_db,
        }):
            spec = importlib.util.spec_from_file_location("isolated_api", ROOT / "api/app.py")
            api = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api)

        queries = []
        api.fetch_one = lambda sql, params=None: ({"run_id": 30} if "COUNT(DISTINCT o.ticker)" in sql else None)

        def fetch_all(sql, params=None):
            queries.append((sql, params))
            return [{"run_id": 30, "ticker": "AAPL"}]

        api.fetch_all = fetch_all
        for endpoint in (api.dashboard_assets, api.dashboard_company_opinions,
                         api.dashboard_recommendation, api.ai_comment, api.dashboard_yahoo_profiles):
            result = endpoint()
            self.assertEqual(result[0]["run_id"], 30)
        self.assertEqual(len(queries), 5)
        self.assertTrue(all(values == (30,) for _, values in queries))


if __name__ == "__main__":
    unittest.main()
