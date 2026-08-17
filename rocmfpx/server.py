"""
rocmfpx.server — Unified FastAPI Router & OpenAI-Compatible Proxy
"""

import httpx
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from rocmfpx.config import DEFAULT_ENGINE_PORT
from rocmfpx.registry import ModelRegistry
from rocmfpx.model_manager import ModelManager
from rocmfpx.engine_manager import EngineManager
from rocmfpx.telemetry import get_system_telemetry

registry = ModelRegistry()
model_mgr = ModelManager(registry)
engine_mgr = EngineManager(registry, engine_port=DEFAULT_ENGINE_PORT)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    registry.reload()
    yield
    # Shutdown
    engine_mgr.unload_model()

app = FastAPI(
    title="ROCmFPX Model Server",
    description="Unified OpenAI-Compatible LLM Server for ROCmFP4 / ROCmFPX on AMD Strix Halo",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Schemas
class LoadRequest(BaseModel):
    model_id: str
    variant: Optional[str] = None
    ctx_size: Optional[int] = None
    reasoning_budget: Optional[int] = 4096
    reasoning_mode: Optional[str] = "auto"
    device: Optional[str] = None

class PullRequest(BaseModel):
    model_id: str
    variant: Optional[str] = None

# ==============================================================================
# OpenAI-Compatible API Surface
# ==============================================================================

@app.get("/v1/models")
async def list_openai_models():
    models_list = registry.list_models()
    active_status = engine_mgr.get_status()
    
    data = []
    for m in models_list:
        data.append({
            "id": m["model_id"],
            "object": "model",
            "created": 1723789200,
            "owned_by": "rocmfpx",
            "is_active": (m["model_id"] == active_status.get("model_id")),
            "variants": list(m.get("variants", {}).keys())
        })
    return {"object": "list", "data": data}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    if not engine_mgr.is_running():
        raise HTTPException(
            status_code=503,
            detail="No model currently loaded. Use 'POST /api/v1/load' or 'rocmfpx load <model_id>' first."
        )

    body = await request.body()
    client = httpx.AsyncClient(timeout=300.0)
    target_url = f"http://127.0.0.1:{engine_mgr.engine_port}/v1/chat/completions"

    # Forward headers
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)

    req = client.build_request("POST", target_url, content=body, headers=headers)
    resp = await client.send(req, stream=True)

    if resp.headers.get("content-type", "").startswith("text/event-stream"):
        async def stream_generator():
            async for chunk in resp.aiter_raw():
                yield chunk
            await client.aclose()
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    else:
        content = await resp.aread()
        await client.aclose()
        return Response(content=content, status_code=resp.status_code, headers=dict(resp.headers))

@app.post("/v1/completions")
async def completions(request: Request):
    if not engine_mgr.is_running():
        raise HTTPException(status_code=503, detail="No model loaded.")
    
    body = await request.body()
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"http://127.0.0.1:{engine_mgr.engine_port}/v1/completions",
            content=body,
            headers={"Content-Type": "application/json"}
        )
        return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

# ==============================================================================
# Lemonade-Style Management API
# ==============================================================================

@app.get("/health")
@app.get("/api/v1/health")
async def health():
    return {
        "status": "ok",
        "service": "rocmfpx-server",
        "engine_active": engine_mgr.is_running(),
        "active_model": engine_mgr.active_model_id
    }

@app.get("/api/v1/status")
async def status():
    return {
        "server": "rocmfpx-server",
        "version": "1.0.0",
        "engine": engine_mgr.get_status(),
        "telemetry": get_system_telemetry()
    }

@app.get("/api/v1/models")
async def list_registered_models():
    registry.reload()
    return {"models": registry.list_models()}

@app.post("/api/v1/load")
async def load_model(req: LoadRequest):
    res = engine_mgr.load_model(
        model_id=req.model_id,
        variant=req.variant,
        ctx_size=req.ctx_size,
        reasoning_budget=req.reasoning_budget,
        reasoning_mode=req.reasoning_mode or "auto",
        device=req.device
    )
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.post("/api/v1/unload")
async def unload_model():
    return engine_mgr.unload_model()

@app.post("/api/v1/pull")
async def pull_model(req: PullRequest):
    res = model_mgr.pull_model(req.model_id, req.variant)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

@app.get("/api/v1/system-info")
async def system_info():
    return {
        "telemetry": get_system_telemetry(),
        "engine_status": engine_mgr.get_status()
    }
