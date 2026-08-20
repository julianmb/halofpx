# ROCmFPX Server API Reference

The `halofpx-server` exposes both a standard OpenAI-compatible inference API and a model management API on port `8010`.

---

## 1. OpenAI Inference Endpoints

### Chat Completions (`POST /v1/chat/completions`)
Generates chat completions for single-turn and multi-turn conversations. Supports streaming SSE (`"stream": true`).

```bash
curl -X POST http://localhost:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen38-27b",
    "messages": [
      {"role": "user", "content": "Explain Strix Halo unified memory architecture."}
    ],
    "temperature": 0.7,
    "max_tokens": 500
  }'
```

### Model Listing (`GET /v1/models`)
Returns list of all available registered models.

```bash
curl http://localhost:8010/v1/models
```

---

## 2. Model Management Endpoints (`/api/v1/*`)

### List Models with Download Status (`GET /api/v1/models`)
Returns all models in the zoo with local cache status, sizes, and variants.

```bash
curl http://localhost:8010/api/v1/models
```

### Load Model into Memory (`POST /api/v1/load`)
Loads a model variant into GPU VRAM / unified memory. Automatically unloads any previous model.

```bash
curl -X POST http://localhost:8010/api/v1/load \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "qwen38-27b",
    "variant": "ROCmFP4_FAST",
    "ctx_size": 131072,
    "cache_ram_mib": 32768,
    "ctx_checkpoints": 16,
    "cache_reuse": 256,
    "checkpoint_every": 4096,
    "mlock": false,
    "optimization_mode": "cache",
    "reasoning_budget": 4096
  }'
```

### Unload Model (`POST /api/v1/unload`)
Unloads active model from memory.

```bash
curl -X POST http://localhost:8010/api/v1/unload
```

### Pull Model from Hugging Face (`POST /api/v1/pull`)
Downloads model weights directly from Hugging Face into cache.

```bash
curl -X POST http://localhost:8010/api/v1/pull \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "nemotron-3.5-30b",
    "variant": "ROCmFP4_FAST"
  }'
```

### Server & Hardware Status (`GET /api/v1/status`)
Returns server uptime, active model info, and APU hardware telemetry.

```bash
curl http://localhost:8010/api/v1/status
```

### APU System Information (`GET /api/v1/system-info`)
Returns detailed APU hardware stats, TTM memory allocation limits, and NPU driver state.

```bash
curl http://localhost:8010/api/v1/system-info
```
