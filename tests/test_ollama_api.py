import json
import unittest
from unittest import mock

try:
    from fastapi.testclient import TestClient
    HAVE_TESTCLIENT = True
except ImportError:  # pragma: no cover
    HAVE_TESTCLIENT = False

from halofpx import __version__
from halofpx.ollama import create_router


def _make_client(engine_running=False, active_model=None):
    engine_mgr = mock.Mock()
    engine_mgr.is_running.return_value = engine_running
    engine_mgr.active_model_id = active_model
    engine_mgr.engine_port = 8800

    registry = mock.Mock()
    registry.get_model.return_value = {
        "default_variant": "ROCmFP4",
        "variants": {
            "ROCmFP4": {"size_gib": 18.16, "sha256": "a" * 64},
        },
    }
    registry.list_models.return_value = [
        {"model_id": "ornith-1.5-35b", "default_variant": "ROCmFP4",
         "variants_status": {"ROCmFP4": {"size_gib": 18.16, "sha256": "a" * 64}}},
    ]

    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(create_router(engine_mgr, registry))
    return TestClient(app), engine_mgr


@unittest.skipUnless(HAVE_TESTCLIENT, "fastapi TestClient (httpx) not available")
class OllamaTagsTests(unittest.TestCase):
    def test_version(self):
        client, _ = _make_client()
        res = client.get("/api/version")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"version": __version__})

    def test_tags_lists_active_first_with_details(self):
        client, _ = _make_client(engine_running=True, active_model="ornith-1.5-35b")
        res = client.get("/api/tags")
        self.assertEqual(res.status_code, 200)
        models = res.json()["models"]
        self.assertEqual(models[0]["name"], "ornith-1.5-35b:latest")
        self.assertEqual(models[0]["details"]["format"], "gguf")
        self.assertEqual(models[0]["digest"], "a" * 12)
        self.assertGreater(models[0]["size"], 0)

    def test_tags_empty_when_nothing_loaded_still_lists_zoo(self):
        client, _ = _make_client(engine_running=False)
        models = client.get("/api/tags").json()["models"]
        self.assertEqual([m["name"] for m in models], ["ornith-1.5-35b:latest"])


@unittest.skipUnless(HAVE_TESTCLIENT, "fastapi TestClient (httpx) not available")
class OllamaGuardsTests(unittest.TestCase):
    def test_chat_503_without_engine(self):
        client, _ = _make_client(engine_running=False)
        res = client.post("/api/chat", json={"model": "x", "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(res.status_code, 503)

    def test_generate_503_without_engine(self):
        client, _ = _make_client(engine_running=False)
        res = client.post("/api/generate", json={"model": "x", "prompt": "hi"})
        self.assertEqual(res.status_code, 503)

    def test_chat_409_for_unloaded_model(self):
        client, _ = _make_client(engine_running=True, active_model="ornith-1.5-35b")
        res = client.post("/api/chat", json={"model": "qwen38-27b:latest", "messages": []})
        self.assertEqual(res.status_code, 409)

    def test_generate_400_without_prompt(self):
        client, _ = _make_client(engine_running=True, active_model="ornith-1.5-35b")
        res = client.post("/api/generate", json={"model": "ornith-1.5-35b"})
        self.assertEqual(res.status_code, 400)


def _fake_sse(chunks):
    """Build an async iterator mimicking httpx aiter_lines output."""
    lines = []
    for c in chunks:
        lines.append("data: " + json.dumps(c))
    lines.append("data: [DONE]")

    class _Resp:
        status_code = 200

        async def aiter_lines(self_inner):
            for l in lines:
                yield l

        async def aread(self_inner):
            return b""

        async def __aenter__(self_inner):
            return self_inner

        async def __aexit__(self_inner, *a):
            return False

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        def stream(self_inner, method, url, json=None):
            return _Resp()

    import halofpx.ollama as o
    return mock.patch.object(o.httpx, "AsyncClient", _Client)


@unittest.skipUnless(HAVE_TESTCLIENT, "fastapi TestClient (httpx) not available")
class OllamaTranslationTests(unittest.TestCase):
    OPENAI_CHUNKS = [
        {"choices": [{"delta": {"content": "Hello"}}]},
        {"choices": [{"delta": {"content": " world"}}]},
        {"choices": [{"delta": {}}], "usage": {"prompt_tokens": 7, "completion_tokens": 2}},
    ]

    def test_chat_stream_translates_to_ndjson(self):
        client, _ = _make_client(engine_running=True, active_model="ornith-1.5-35b")
        with _fake_sse(self.OPENAI_CHUNKS):
            res = client.post("/api/chat", json={"model": "ornith-1.5-35b",
                                                 "messages": [{"role": "user", "content": "hi"}],
                                                 "stream": True})
        self.assertEqual(res.status_code, 200)
        events = [json.loads(l) for l in res.text.strip().splitlines()]
        self.assertFalse(events[0]["done"])
        self.assertEqual(events[0]["message"]["content"], "Hello")
        final = events[-1]
        self.assertTrue(final["done"])
        self.assertEqual(final["prompt_eval_count"], 7)
        self.assertEqual(final["eval_count"], 2)

    def test_chat_non_stream_returns_full_message(self):
        client, _ = _make_client(engine_running=True, active_model="ornith-1.5-35b")
        with _fake_sse(self.OPENAI_CHUNKS):
            res = client.post("/api/chat", json={"model": "ornith-1.5-35b",
                                                 "messages": [{"role": "user", "content": "hi"}],
                                                 "stream": False})
        body = res.json()
        self.assertTrue(body["done"])
        self.assertEqual(body["message"]["content"], "Hello world")
        self.assertEqual(body["eval_count"], 2)

    def test_generate_stream_uses_response_field(self):
        client, _ = _make_client(engine_running=True, active_model="ornith-1.5-35b")
        chunks = [
            {"choices": [{"text": "To"}]},
            {"choices": [{"text": "day"}]},
            {"choices": [{"text": ""}], "usage": {"prompt_tokens": 4, "completion_tokens": 2}},
        ]
        with _fake_sse(chunks):
            res = client.post("/api/generate", json={"model": "ornith-1.5-35b",
                                                     "prompt": "hi", "stream": True})
        events = [json.loads(l) for l in res.text.strip().splitlines()]
        self.assertIn("response", events[0])
        self.assertEqual(events[0]["response"], "To")
        self.assertTrue(events[-1]["done"])

    def test_options_map_to_sampling_params(self):
        client, engine_mgr = _make_client(engine_running=True, active_model="ornith-1.5-35b")
        captured = {}

        class _CapResp:
            status_code = 200

            async def aiter_lines(self_inner):
                yield 'data: {"choices":[{"delta":{"content":"x"}}]}'

            async def aread(self_inner):
                return b""

            async def __aenter__(self_inner):
                return self_inner

            async def __aexit__(self_inner, *a):
                return False

        class _CapClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            def stream(self_inner, method, url, json=None):
                captured.update(json or {})
                return _CapResp()

        import halofpx.ollama as o
        with mock.patch.object(o.httpx, "AsyncClient", _CapClient):
            client.post("/api/generate", json={
                "model": "ornith-1.5-35b", "prompt": "hi",
                "options": {"num_predict": 32, "temperature": 0.4, "seed": 9},
            })
        self.assertEqual(captured.get("max_tokens"), 32)
        self.assertEqual(captured.get("temperature"), 0.4)
        self.assertEqual(captured.get("seed"), 9)


if __name__ == "__main__":
    unittest.main()
