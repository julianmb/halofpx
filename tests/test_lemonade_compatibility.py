"""
Tests for Lemonade SDK compatibility layer in halofpx:
- Config detection and status helper
- Extra models and user models discovery
- Model ID prefix resolution (extra., user., builtin.)
- REST API schema compatibility (GET /api/v1/models, POST /api/v1/load with model alias, DELETE /api/v1/models)
- CLI subcommands (run, chat, backends, delete, config)
"""

import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from halofpx.config import (
    MODELS_DIR,
    get_lemonade_config_path,
    get_lemonade_user_models_path,
    get_lemonade_status,
    sync_lemonade_extra_models_dir,
)
from halofpx.registry import ModelRegistry
from halofpx.server import app


@pytest.fixture
def test_client():
    return TestClient(app)


def test_lemonade_config_paths():
    """Verify Lemonade configuration and user models paths are detected."""
    cfg_path = get_lemonade_config_path()
    # If Lemonade is installed on system, cfg_path should point to valid path or None
    if cfg_path:
        assert isinstance(cfg_path, Path)

    u_path = get_lemonade_user_models_path()
    if u_path:
        assert isinstance(u_path, Path)


def test_lemonade_status():
    """Verify get_lemonade_status returns properly structured dictionary."""
    status = get_lemonade_status()
    assert isinstance(status, dict)
    assert "running" in status
    assert "port" in status
    assert status["port"] == 13305
    if status["running"]:
        assert "health" in status


def test_lemonade_registry_prefix_resolution():
    """Verify ModelRegistry correctly resolves models with and without extra./user. prefixes."""
    registry = ModelRegistry()

    # If qwen38-flash-next is in registry
    model_direct = registry.get_model("qwen38-flash-next")
    assert model_direct is not None

    # Should resolve with extra. prefix
    model_extra = registry.get_model("extra.qwen38-flash-next")
    assert model_extra is not None
    assert model_extra["display_name"] == model_direct["display_name"]

    # File path resolution should work with extra. prefix
    fpath = registry.get_model_file_path("extra.qwen38-flash-next")
    if fpath:
        assert fpath.exists()
        assert fpath.suffix == ".gguf"


def test_api_v1_models_lemonade_format(test_client):
    """Verify /api/v1/models returns Lemonade-compatible 'data' list alongside 'models'."""
    resp = test_client.get("/api/v1/models")
    assert resp.status_code == 200
    data = resp.json()

    assert "object" in data
    assert data["object"] == "list"
    assert "models" in data
    assert "data" in data
    assert isinstance(data["data"], list)

    if len(data["data"]) > 0:
        item = data["data"][0]
        assert "id" in item
        assert "downloaded" in item
        assert "labels" in item
        assert "size" in item
        assert "recipe" in item
        assert item["recipe"] == "llamacpp"


def test_api_v1_load_lemonade_alias(monkeypatch, test_client):
    """Verify /api/v1/load accepts 'model' (Lemonade schema) as alias for 'model_id'."""
    from halofpx.server import engine_mgr

    called_with = {}

    def mock_load_model(model_id, **kwargs):
        called_with["model_id"] = model_id
        return {
            "status": "success",
            "model_id": model_id,
            "device": "Vulkan0",
            "context_size": 32768
        }

    monkeypatch.setattr(engine_mgr, "load_model", mock_load_model)

    # 1. Standard HaloFPX format
    resp1 = test_client.post("/api/v1/load", json={"model_id": "test-model-1"})
    assert resp1.status_code == 200
    assert called_with["model_id"] == "test-model-1"

    # 2. Lemonade format with "model"
    resp2 = test_client.post("/api/v1/load", json={"model": "test-model-2"})
    assert resp2.status_code == 200
    assert called_with["model_id"] == "test-model-2"

    # 3. Neither provided -> 400
    resp3 = test_client.post("/api/v1/load", json={})
    assert resp3.status_code == 400


def test_api_v1_delete_routes(monkeypatch, test_client):
    """Verify DELETE /api/v1/models/{model_id} and POST /api/v1/delete."""
    from halofpx.server import model_mgr

    deleted_models = []

    def mock_delete_model(model_id, variant=None):
        deleted_models.append((model_id, variant))
        return {"status": "success", "message": f"Deleted {model_id}"}

    monkeypatch.setattr(model_mgr, "delete_model", mock_delete_model)

    # DELETE /api/v1/models/{model_id}
    resp1 = test_client.delete("/api/v1/models/test-model-del")
    assert resp1.status_code == 200
    assert ("test-model-del", None) in deleted_models

    # POST /api/v1/delete with model
    resp2 = test_client.post("/api/v1/delete", json={"model": "test-model-del-2", "variant": "ROCmFP4"})
    assert resp2.status_code == 200
    assert ("test-model-del-2", "ROCmFP4") in deleted_models


def test_cli_subcommands_parsed():
    """Verify CLI parser parses all Lemonade parity commands."""
    from halofpx.cli import build_parser

    parser = build_parser()
    test_args = [
        ["run", "extra.qwen38-flash-next", "--no-chat"],
        ["chat", "qwen38-27b"],
        ["backends"],
        ["config", "show"],
        ["config", "sync-lemonade"],
        ["list", "--lemonade"],
        ["delete", "dummy-model", "-y"],
    ]

    for arg_list in test_args:
        args = parser.parse_args(arg_list)
        assert args.subcommand in ("run", "chat", "backends", "config", "list", "delete")


def test_recognized_model_names_resolution():
    """Verify user-friendly / recognized model names and aliases resolve accurately."""
    registry = ModelRegistry()

    # Ling 3.0 Flash variations
    for name in ("Ling-3.0-Flash", "ling-3.0-flash", "ling3-flash", "Ling 3.0 Flash 124B MoE"):
        m = registry.get_model(name)
        assert m is not None, f"Failed to resolve {name}"
        assert m["model_id"] == "ling3-flash"
        assert "Ling 3.0 Flash" in m["display_name"]

    # Qwen 3.8 Flash Next
    for name in ("Qwen3.8-Flash-Next", "qwen-3.8-flash-next", "qwen38-flash-next"):
        m = registry.get_model(name)
        assert m is not None, f"Failed to resolve {name}"
        assert m["model_id"] == "qwen38-flash-next"

    # Nex N2.5 Mini
    for name in ("Nex-N2.5-Mini", "nex-n2.5-mini"):
        m = registry.get_model(name)
        assert m is not None, f"Failed to resolve {name}"
        assert m["model_id"] == "nex-n2.5-mini"

    # Ornith 1.5 35B
    for name in ("Ornith-1.5-35B", "ornith-1.5-35b"):
        m = registry.get_model(name)
        assert m is not None, f"Failed to resolve {name}"
        assert m["model_id"] == "ornith-1.5-35b"


def test_api_models_includes_human_readable_name(test_client):
    """Verify API endpoints include friendly 'name' property so users don't see bare quants."""
    resp = test_client.get("/api/v1/models")
    assert resp.status_code == 200
    data = resp.json()
    for item in data["data"]:
        assert "name" in item
        assert item["name"]  # Must not be empty
        # Should not be a bare quantization format
        assert item["name"].upper() not in ("Q4_K_M", "Q8_0", "FP16", "BF16", "ROCMFP4")


