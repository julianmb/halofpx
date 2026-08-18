# ROCmFPX Server Architecture & System Design

`HaloFPX` is an asynchronous, high-throughput model serving framework and model zoo manager engineered specifically for **AMD Strix Halo (Ryzen AI Max+ 395 / Radeon 8060S / gfx1151)**. It combines a FastAPI management router with the native **ROCmFPX** (llama.cpp fork) inference engine, exposing both standard OpenAI-compatible endpoints and Lemonade-style lifecycle management.

---

## 1. System Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CLIENT APPLICATIONS                           │
│   (Open WebUI, Continue.dev, Cursor IDE, LiteLLM, curl, Python SDK)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Standard OpenAI API / Management API
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   ROCmFPX UNIFIED ROUTER (Port 8010)                   │
│                                                                        │
│   ┌──────────────────────────┐         ┌──────────────────────────┐    │
│   │   OpenAI Proxy Layer     │         │   Model & Engine Manager │    │
│   │  • /v1/chat/completions  │         │  • /api/v1/load, unload  │    │
│   │  • /v1/models            │         │  • /api/v1/pull, delete  │    │
│   │  • /v1/completions       │         │  • /api/v1/status        │    │
│   └─────────────┬────────────┘         └────────────┬─────────────┘    │
└─────────────────┼───────────────────────────────────┼──────────────────┘
                  │ Forward Stream (Port 8800)        │ Subprocess Control
                  ▼                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   ACTIVE ENGINE INSTANCE (Port 8800)                   │
│                 (ROCmFPX llama-server / gfx1151 build)                 │
│                                                                        │
│   • Vulkan0 Wave64 Matrix Acceleration (Mesa RADV KHR_coopmat)         │
│   • ROCm0 HIP Prefill Kernel Pipeline                                  │
│   • MTP (Multi-Token Prediction) Speculative Verification (36 tok/s)   │
│   • Asymmetric TurboQuant KV Cache (K=q8_0, V=turbo4)                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Hardware Passthrough
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        AMD STRIX HALO HARDWARE                         │
│   • 40 CU Radeon 8060S iGPU @ 2.9 GHz (RDNA 3.5 / gfx1151)             │
│   • 128 GB Unified LPDDR5X-8000 (256-bit Bus, 273 GB/s peak)           │
│   • 50 TOPS AMD XDNA 2 NPU (/dev/accel/accel0)                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems

### 2.1 Router & Proxy Layer (`rocmfpx.server`)
- **FastAPI Application:** Serves on default port `8010` (customizable via `ROCMFPX_PORT`).
- **Zero-Copy Streaming:** High-performance async proxy forwarding SSE (Server-Sent Events) chunks directly from the active engine to the client via `httpx.AsyncClient`.
- **CORS & Middleware:** Fully compliant with browser clients like Open WebUI, LibreChat, and custom web frontends.

### 2.2 Model Registry (`rocmfpx.registry`)
- **JSON Schema Catalog:** Loads model metadata, default presets, context windows, and variant dictionaries from `registry/models.json` and `registry/presets.json`.
- **Multi-Location Cache Resolver:** Searches for GGUF weights across:
  1. `/var/lib/lemonade/.cache/huggingface/hub/`
  2. `~/.cache/huggingface/hub/`
  3. `./models/<model_id>/`
  4. Local symlinks and direct filesystem paths.

### 2.3 Model Downloader (`rocmfpx.model_manager`)
- **Hugging Face Hub Integration:** Uses `hf download` or `huggingface_hub.hf_hub_download` to pull weights directly from Hugging Face into cache folders without creating duplicate file copies.
- **Integrity Verification:** Calculates SHA256 checksums on downloaded chunks to prevent corrupted weights from entering unified memory.

### 2.4 Engine Lifecycle Manager (`rocmfpx.engine_manager`)
- **Single-Loaded-Model Policy:** Automatically tracks active model PID, uptime, VRAM usage, and device backend.
- **Graceful Hot-Swapping:** When `POST /api/v1/load` is called for a new model, the manager sends `SIGTERM` to the active instance, verifies memory release, and spawns the new backend process with optimal Strix Halo flags.
- **Hardware Backend Auto-Detection:** Queries `llama-server --list-devices` on startup. If `Vulkan0` is available (Mesa RADV Wave64), it is prioritized for peak decode/MTP performance. If missing, it gracefully falls back to `ROCm0` (HIP) with informational notices.

### 2.5 Hardware Telemetry & Health (`rocmfpx.telemetry`)
- Reads `/proc/cpuinfo`, `/proc/meminfo`, `/sys/module/ttm/parameters/pages_limit`, and `/dev/accel/accel0` in real time.
- Exposes APU CPU model, kernel version, total visible RAM, TTM GPU memory ceiling ratio, GPU DPM performance state, and NPU driver status via `GET /api/v1/status` and `GET /api/v1/system-info`.

---

## 3. Request Lifecycle

```
Client Request (POST /v1/chat/completions)
  │
  ├── 1. HaloFPX validates active engine status
  │      └── If no model loaded: returns 503 with load instructions
  │
  ├── 2. Builds async proxy request to backend (http://127.0.0.1:8800)
  │
  ├── 3. Active Engine (llama-server Vulkan0) evaluates prompt
  │      ├── Keys cached in Q8_0, Values cached in Turbo4
  │      ├── MTP draft heads propose candidate token sequence (k=6)
  │      └── Radeon 8060S cooperative matrix verifies candidates in parallel
  │
  ├── 4. Token stream generated (30–36 tok/s)
  │
  └── 5. StreamingResponse forwards SSE chunks directly to client
```
