"""
halofpx.ollama — Ollama-Compatible API Surface

Maps Ollama's /api/* endpoints onto the ROCmFPX engine's OpenAI-compatible
surface so Ollama clients work drop-in against halofpx.

Design notes:
- The router is created via create_router(...) so it receives the live
  singletons without circular imports.
- Streaming responses are translated from OpenAI SSE to Ollama NDJSON.
- Token stats are counted client-side (llama.cpp does not reliably include
  usage in every streamed chunk).
"""

import json
import time
import asyncio
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from halofpx import __version__


def create_router(engine_mgr, registry) -> APIRouter:
    router = APIRouter()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _active_model_id() -> Optional[str]:
        return engine_mgr.active_model_id if engine_mgr.is_running() else None

    def _require_engine() -> str:
        if not engine_mgr.is_running():
            raise HTTPException(
                status_code=503,
                detail="No model currently loaded. Use 'POST /api/v1/load' or 'halofpx load <model_id>' first.",
            )
        return f"http://127.0.0.1:{engine_mgr.engine_port}"

    def _check_requested_model(requested: Optional[str]) -> None:
        """Ollama clients echo back names from /api/tags; anything else that
        is not the active model gets an explicit error rather than silently
        answering with the wrong weights."""
        active = _active_model_id()
        if not requested:
            return
        base = requested.split(":")[0]
        if base != active:
            raise HTTPException(
                status_code=409,
                detail=f"Model '{requested}' is not loaded (active: '{active}'). Load it first via /api/v1/load.",
            )

    def _now_iso() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"

    @router.get("/api/version")
    async def api_version():
        return {"version": __version__}

    # ------------------------------------------------------------------
    # /api/tags — list models (active first, then registered zoo)
    # ------------------------------------------------------------------

    @router.get("/api/tags")
    async def api_tags():
        models_out = []
        active = _active_model_id()
        seen = set()

        def _entry(model_id: str, is_active: bool) -> Dict[str, Any]:
            entry: Dict[str, Any] = {
                "name": f"{model_id}:latest",
                "model": f"{model_id}:latest",
                "modified_at": _now_iso(),
                "size": 0,
                "digest": "",
                "details": {
                    "parent_model": "",
                    "format": "gguf",
                    "family": "rocmfpx",
                    "families": ["rocmfpx"],
                    "parameter_size": "",
                    "quantization_level": "",
                },
            }
            info = registry.get_model(model_id)
            if info:
                default = info.get("default_variant")
                vdata = (info.get("variants") or {}).get(default) or {}
                entry["size"] = int(vdata.get("size_gib", 0.0) * (1024 ** 3))
                sha = vdata.get("sha256") or ""
                entry["digest"] = sha[:12] if sha else ""
                entry["details"]["quantization_level"] = default or ""
            return entry

        if active:
            models_out.append(_entry(active, True))
            seen.add(active)

        for m in registry.list_models():
            mid = m["model_id"]
            if mid not in seen:
                models_out.append(_entry(mid, False))
                seen.add(mid)

        return {"models": models_out}

    # ------------------------------------------------------------------
    # OpenAI SSE -> Ollama NDJSON translation
    # ------------------------------------------------------------------

    async def _iter_openai_sse(payload: Dict[str, Any], url: str):
        """Yield parsed JSON objects from the engine's OpenAI streaming API."""
        async with httpx.AsyncClient(timeout=600.0) as client:
            async with client.stream("POST", url, json=payload) as resp:
                if resp.status_code != 200:
                    body = await resp.aread()
                    raise HTTPException(
                        status_code=resp.status_code,
                        detail=f"Engine error: {body.decode(errors='replace')[:300]}",
                    )
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if not data or data == "[DONE]":
                        continue
                    yield json.loads(data)

    def _options_to_sampling(options: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Map the subset of Ollama options we support onto OpenAI params."""
        out: Dict[str, Any] = {}
        if not options:
            return out
        if "num_predict" in options:
            out["max_tokens"] = options["num_predict"]
        if "temperature" in options:
            out["temperature"] = options["temperature"]
        if "top_p" in options:
            out["top_p"] = options["top_p"]
        if "seed" in options:
            out["seed"] = options["seed"]
        if "stop" in options:
            out["stop"] = options["stop"]
        return out

    def _stats_fields(start: float, prompt_tokens: int, eval_tokens: int) -> Dict[str, Any]:
        elapsed = max(time.time() - start, 1e-9)
        return {
            "total_duration": int(elapsed * 1e9),
            "load_duration": 0,
            "prompt_eval_count": prompt_tokens,
            "prompt_eval_duration": 0,
            "eval_count": eval_tokens,
            "eval_duration": int(elapsed * 1e9),
        }

    async def _chat_stream_response(model: str, payload: Dict[str, Any]):
        start = time.time()
        prompt_tokens = 0
        eval_tokens = 0

        async def ndjson():
            nonlocal prompt_tokens, eval_tokens
            try:
                async for chunk in _iter_openai_sse(
                    payload, f"http://127.0.0.1:{engine_mgr.engine_port}/v1/chat/completions"
                ):
                    usage = chunk.get("usage") or {}
                    if usage.get("prompt_tokens"):
                        prompt_tokens = usage["prompt_tokens"]
                    delta = ((chunk.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
                    if delta:
                        eval_tokens += 1
                    yield json.dumps({
                        "model": model,
                        "created_at": _now_iso(),
                        "message": {"role": "assistant", "content": delta},
                        "done": False,
                    }) + "\n"
                yield json.dumps({
                    "model": model,
                    "created_at": _now_iso(),
                    "message": {"role": "assistant", "content": ""},
                    "done_reason": "stop",
                    "done": True,
                    **_stats_fields(start, prompt_tokens, eval_tokens),
                }) + "\n"
            except HTTPException as e:
                yield json.dumps({"error": e.detail}) + "\n"

        return StreamingResponse(ndjson(), media_type="application/x-ndjson")

    async def _gen_stream_response(model: str, payload: Dict[str, Any]):
        start = time.time()
        prompt_tokens = 0
        eval_tokens = 0

        async def ndjson():
            nonlocal prompt_tokens, eval_tokens
            try:
                async for chunk in _iter_openai_sse(
                    payload, f"http://127.0.0.1:{engine_mgr.engine_port}/v1/completions"
                ):
                    usage = chunk.get("usage") or {}
                    if usage.get("prompt_tokens"):
                        prompt_tokens = usage["prompt_tokens"]
                    choice = (chunk.get("choices") or [{}])[0]
                    text = choice.get("text") or ""
                    if text:
                        eval_tokens += 1
                    yield json.dumps({
                        "model": model,
                        "created_at": _now_iso(),
                        "response": text,
                        "done": False,
                    }) + "\n"
                yield json.dumps({
                    "model": model,
                    "created_at": _now_iso(),
                    "response": "",
                    "done_reason": "stop",
                    "done": True,
                    **_stats_fields(start, prompt_tokens, eval_tokens),
                }) + "\n"
            except HTTPException as e:
                yield json.dumps({"error": e.detail}) + "\n"

        return StreamingResponse(ndjson(), media_type="application/x-ndjson")

    # ------------------------------------------------------------------
    # /api/chat
    # ------------------------------------------------------------------

    @router.post("/api/chat")
    async def api_chat(request: Request):
        _require_engine()
        body = await request.json()
        requested = body.get("model")
        _check_requested_model(requested)
        model = _active_model_id()

        messages = body.get("messages") or []
        if not messages:
            raise HTTPException(status_code=400, detail="'messages' is required")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            **_options_to_sampling(body.get("options")),
        }

        if body.get("stream", True):
            return await _chat_stream_response(model, payload)

        # Non-streaming: collect the full answer
        start = time.time()
        content_parts = []
        prompt_tokens = eval_tokens = 0
        async for chunk in _iter_openai_sse(
            payload, f"http://127.0.0.1:{engine_mgr.engine_port}/v1/chat/completions"
        ):
            usage = chunk.get("usage") or {}
            if usage.get("prompt_tokens"):
                prompt_tokens = usage["prompt_tokens"]
            delta = ((chunk.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
            if delta:
                content_parts.append(delta)
                eval_tokens += 1
        return JSONResponse({
            "model": model,
            "created_at": _now_iso(),
            "message": {"role": "assistant", "content": "".join(content_parts)},
            "done_reason": "stop",
            "done": True,
            **_stats_fields(start, prompt_tokens, eval_tokens),
        })

    # ------------------------------------------------------------------
    # /api/generate
    # ------------------------------------------------------------------

    @router.post("/api/generate")
    async def api_generate(request: Request):
        _require_engine()
        body = await request.json()
        requested = body.get("model")
        _check_requested_model(requested)
        model = _active_model_id()

        prompt = body.get("prompt")
        if prompt is None:
            raise HTTPException(status_code=400, detail="'prompt' is required")

        system = body.get("system")
        if system and not body.get("raw"):
            prompt = f"{system}\n\n{prompt}"

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            **_options_to_sampling(body.get("options")),
        }

        if body.get("stream", True):
            return await _gen_stream_response(model, payload)

        start = time.time()
        parts = []
        prompt_tokens = eval_tokens = 0
        async for chunk in _iter_openai_sse(
            payload, f"http://127.0.0.1:{engine_mgr.engine_port}/v1/completions"
        ):
            usage = chunk.get("usage") or {}
            if usage.get("prompt_tokens"):
                prompt_tokens = usage["prompt_tokens"]
            text = ((chunk.get("choices") or [{}])[0]).get("text") or ""
            if text:
                parts.append(text)
                eval_tokens += 1
        return JSONResponse({
            "model": model,
            "created_at": _now_iso(),
            "response": "".join(parts),
            "done_reason": "stop",
            "done": True,
            **_stats_fields(start, prompt_tokens, eval_tokens),
        })

    return router
