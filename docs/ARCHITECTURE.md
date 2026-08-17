# ROCmFPX Model Server Architecture

`rocmfpx-server` is a unified, high-performance model serving daemon and CLI engineered specifically for **AMD Strix Halo (Ryzen AI Max+ 395 / Radeon 8060S / gfx1151)**. It provides a Lemonade-style model management system for ROCmFPX/ROCmFP4 quantized GGUF models.

---

## 1. System Topology & Request Flow

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
│   │   OpenAI Proxy Handler   │         │   Model & Engine Manager │    │
│   │  /v1/chat/completions    │         │   /api/v1/load, unload   │    │
│   │  /v1/models, completions │         │   /api/v1/pull, status   │    │
│   └─────────────┬────────────┘         └────────────┬─────────────┘    │
└─────────────────┼───────────────────────────────────┼──────────────────┘
                  │ Forward Stream (Port 8800)        │ Subprocess Control
                  ▼                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   ACTIVE BACKEND ENGINE (Port 8800)                    │
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
│   • 40 CU Radeon 8060S iGPU @ 2.9 GHz                                  │
│   • 128 GB Unified LPDDR5X-8000 (256-bit Bus, 273 GB/s peak)           │
│   • 50 TOPS AMD XDNA 2 NPU (/dev/accel/accel0)                         │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Key Modules & Subsystems

1. **`rocmfpx.registry` (Model Zoo Catalog):**
   - Loads model definitions, Hugging Face repository mappings, and quantization variants from `registry/models.json` and `registry/presets.json`.
   - Checks local filesystem (`/var/lib/lemonade/.cache/huggingface/hub`, `~/.cache/huggingface/hub`, and `./models/`) to determine if weights are already present on disk.

2. **`rocmfpx.model_manager` (Weight Downloader):**
   - Automatically pulls model variants from Hugging Face into the standard cache directory using `hf download` or `huggingface_hub`.
   - Validates SHA256 integrity checksums to ensure uncorrupted downloads.

3. **`rocmfpx.engine_manager` (Subprocess Lifecycle):**
   - Auto-detects compute backend (`Vulkan0` vs `ROCm0`).
   - Configures runtime arguments (MTP draft depth, FlashAttention, TurboQuant KV cache, slot allocation, and reasoning budget limits).
   - Manages single-loaded-model policy with graceful hot-swapping and memory reclamation.

4. **`rocmfpx.server` (FastAPI Application):**
   - Exposes `/v1/chat/completions` with streaming Server-Sent Events (SSE) support.
   - Exposes REST management endpoints: `/api/v1/load`, `/api/v1/unload`, `/api/v1/pull`, `/api/v1/status`, `/api/v1/system-info`.

5. **`rocmfpx.cli` (Unified CLI):**
   - Provides clean commands: `rocmfpx serve`, `rocmfpx list`, `rocmfpx pull`, `rocmfpx load`, `rocmfpx unload`, `rocmfpx status`, `rocmfpx doctor`, `rocmfpx bench`.
