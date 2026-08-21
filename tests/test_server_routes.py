import unittest
from unittest import mock

try:
    from fastapi.testclient import TestClient
    HAVE_TESTCLIENT = True
except ImportError:  # pragma: no cover - httpx missing in minimal envs
    HAVE_TESTCLIENT = False

from halofpx import __version__
from halofpx.server import app, verify_api_key
from halofpx.config import HALOFPX_API_KEY


class ServerRouteTests(unittest.TestCase):
    def test_method_and_path_pairs_are_unique(self):
        pairs = []
        for route in app.routes:
            for method in getattr(route, "methods", set()):
                pairs.append((method, route.path))
        self.assertEqual(len(pairs), len(set(pairs)))


@unittest.skipUnless(HAVE_TESTCLIENT, "fastapi TestClient (httpx) not available")
class ServerEndpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_reports_engine_state(self):
        for path in ("/health", "/api/v1/health"):
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["status"], "ok")
            self.assertFalse(body["engine_active"])
            self.assertIsNone(body["active_model"])

    def test_status_reports_centralized_version(self):
        res = self.client.get("/api/v1/status")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body["version"], __version__)
        self.assertIn("engine", body)
        self.assertIn("telemetry", body)

    def test_openai_models_list_includes_vision_readiness(self):
        res = self.client.get("/v1/models")
        self.assertEqual(res.status_code, 200)
        data = res.json()["data"]
        ids = {m["id"] for m in data}
        self.assertIn("ornith-1.5-35b", ids)
        ornith = next(m for m in data if m["id"] == "ornith-1.5-35b")
        self.assertIn("ROCmFP4", ornith["variants"])

    def test_registered_models_report_vision_fields(self):
        res = self.client.get("/api/v1/models")
        self.assertEqual(res.status_code, 200)
        ornith = next(
            m for m in res.json()["models"] if m["model_id"] == "ornith-1.5-35b"
        )
        self.assertTrue(ornith["vision_capable"])
        self.assertIn("vision_ready", ornith)

    def test_chat_completions_without_model_returns_503(self):
        res = self.client.post("/v1/chat/completions", json={"messages": []})
        self.assertEqual(res.status_code, 503)
        self.assertIn("load", res.json()["detail"].lower())

    def test_completions_without_model_returns_503(self):
        res = self.client.post("/v1/completions", json={})
        self.assertEqual(res.status_code, 503)


class ApiKeyAuthTests(unittest.TestCase):
    def test_auth_disabled_when_no_key_configured(self):
        with mock.patch("halofpx.server.HALOFPX_API_KEY", ""):
            self.assertTrue(verify_api_key(request=mock.Mock(), creds=None))

    def test_rejects_missing_and_wrong_credentials(self):
        request = mock.Mock(headers={})
        with mock.patch("halofpx.server.HALOFPX_API_KEY", "sekrit"):
            with self.assertRaises(Exception):
                verify_api_key(request=request, creds=None)
            bad = mock.Mock(credentials="wrong")
            with self.assertRaises(Exception):
                verify_api_key(request=request, creds=bad)

    def test_accepts_bearer_and_header_key(self):
        request = mock.Mock(headers={"x-api-key": "sekrit"})
        with mock.patch("halofpx.server.HALOFPX_API_KEY", "sekrit"):
            self.assertTrue(verify_api_key(request=request, creds=None))


if __name__ == "__main__":
    unittest.main()
