# AGENT HANDOVER PROMPT — ROCmFPX Server

> **To the Next Agent / Developer:**  
> This file contains the complete mission context, technical architecture, repository layout, hardware constraints, and operational runbook for `rocmfpx-server`. Read this file to immediately continue development and maintenance without losing context.

---

## 1. Project Mission & Identity

* **Repository:** `julianmb/rocmfpx-server` (https://github.com/julianmb/rocmfpx-server)
* **Purpose:** A Lemonade-style unified model server, model zoo manager, and CLI for **ROCmFPX / ROCmFP4** quantized GGUF models on **AMD Strix Halo**.
* **Target Hardware:** AMD Ryzen AI Max+ 395 (40 CU Radeon 8060S @ 2.9 GHz, 16 Zen 5 CPU cores, 128 GB/64 GB unified LPDDR5X-8000/8533 memory, AMD XDNA 2 50 TOPS NPU at `/dev/accel/accel0`, Linux kernel 7.0+).

---

## 2. Directory & Architecture Map

```
rocmfpx-server/
├── rocmfpx/                       # Core Python package
│   ├── __init__.py                # Package init & version (1.0.0)
│   ├── config.py                  # Global paths, ports (8010/8800), HF cache paths & env variables
│   ├── registry.py                # Model registry catalog loader & cache file resolver
│   ├── model_manager.py           # HF weight downloader (hf CLI / huggingface_hub) + SHA256 verifier
│   ├── engine_manager.py          # Subprocess lifecycle manager for llama-server (load, unload, hot-swap)
│   ├── telemetry.py               # APU hardware census, RAM, TTM limit, GPU DPM, NPU state
│   ├── server.py                  # FastAPI router exposing /v1/* (OpenAI) & /api/v1/* (Management)
│   └── cli.py                     # Unified CLI entrypoint (rocmfpx serve/list/pull/load/status)
│
├── registry/                      # Model Zoo Catalog & Presets
│   ├── models.json                # Registry of all 6 model families & 15 quantization variants
│   └── presets.json               # Quantization presets (ROCmFP4_FAST, ROCmFP8, etc.) & hardware profiles
│
├── scripts/                       # Diagnostics, benchmarking & build utilities
│   ├── setup_env.sh               # Exports Strix Halo environment variables (ROCm 7.x + Mesa RADV)
│   ├── build_engine.sh            # ROCmFPX engine compilation + --prebuilt binary fetcher
│   ├── apply_hardware_tweaks.sh   # Auto-configures TTM memory ceiling (64GB vs 128GB) & GPU clocks
│   ├── strix_doctor.py            # Complete hardware health check & triage diagnostic
│   ├── chat_tui.py                # Interactive terminal streaming chat with live speedometer
│   ├── benchmark.py               # Multi-prompt automated benchmark runner & report exporter
│   ├── quality_eval.py            # Deterministic quality & smoke test suite
│   ├── context_scaling_benchmark.py # Context depth benchmark (512 to 32K context)
│   ├── npu_sidecar_drafter.py     # AMD XDNA 2 NPU (/dev/accel/accel0) orchestrator & simulation tool
│   ├── pflash_prefill.py          # Speculative prompt compression & prefill optimizer
│   └── convert_and_quant.sh       # Quantization pipeline from BF16 GGUF to ROCmFP4 / ROCmFP8
│
├── docs/                          # Comprehensive technical documentation
│   ├── ARCHITECTURE.md            # Detailed system design & request flow
│   ├── API_REFERENCE.md           # OpenAPI / REST endpoint specification & curl examples
│   ├── CLIENT_INTEGRATION.md      # Open WebUI, Continue.dev, Cursor, LiteLLM connection guides
│   ├── HARDWARE_GUIDE.md          # Strix Halo 256-bit bus math, Mesa RADV Wave64, TTM limits
│   ├── BENCHMARKS.md              # Full benchmark matrix across all 6 model families
│   └── QUANTIZATION_RECIPES.md    # Quantization math, block size 32 alignment, dequant scale packing
│
├── benchmarks/                    # Live benchmark output artifacts (.md and .json reports)
├── models/                        # Local model weights directory (with canonical symlinks)
├── engine/                        # Local engine binary symlink / build destination
├── Dockerfile                     # Production container with Mesa RADV & ROCm runtime
├── docker-compose.yml             # 1-command stack with Open WebUI integration
├── pyproject.toml                 # Pip package definition
├── requirements.txt               # Minimal Python dependencies (fastapi, uvicorn, pydantic, httpx, requests)
├── README.md                      # Publication-ready master GitHub README
├── LICENSE                        # Apache 2.0 License
└── AGENT_PROMPT.md                # This file
```

---

## 3. Published Hugging Face Model Repositories

The registry (`registry/models.json`) links to the following published Hugging Face repositories:

| Model ID | Hugging Face Repository | Available Quantization Variants |
|---|---|---|
| **`qwen38-27b`** | `julianmb/Qwen-3.8-27B-ROCmFP4-FAST-GGUF` | `ROCmFP4_FAST` (13.55G), `ROCmFP8` (26.25G), `ROCmFP4_STRIX_LEAN` (13.82G), `Q3_K_M`, `Q3_K_S`, `ROCmFP2` |
| **`nemotron-3.5-30b`** | `julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF` | `ROCmFP4_FAST` (14.8G), `ROCmFP4_STRIX_LEAN` (15.2G), `UD_Q4_K_XL` (17.1G) |
| **`ornith-35b`** | `julianmb/Ornith-1.0-35B-ROCmFPX-StrixHalo` | `ROCmFPX_Speed` (19.2G), `ROCmFPX_Quality` (31.4G) |
| **`deepseek-v4-flash`** | `julianmb/DeepSeek-V4-Flash-0731-IQ2XXS-STRIX` | `IQ2_XXS` (86.7G) |
| **`laguna-s21`** | `laguna/laguna-s-2.1` | `ROCmFP4_StrixKVSpine` (61.2G) |

---

## 4. Key Architectural Insights & Technical Rules

1. **Dual Backend Crossover Rule:**
   - **`Vulkan0` (Mesa RADV Wave64):** Fastest token decode and MTP speculative verification (**30.56 – 36.04 tok/s** on 27B via `KHR_coopmat`).
   - **`ROCm0` (HIP):** Fastest prompt evaluation / prefill processing (**390+ tok/s**).
   - If a host lacks `glslc`, the server automatically falls back to `ROCm0` with a clear informational notice.

2. **Memory Bandwidth & 8-Bit Reality:**
   - Strix Halo has a **256-bit memory controller** (273 GB/s peak theoretical at LPDDR5X-8533, ~190–200 GB/s sustained).
   - LLM generation is strictly memory-bandwidth bound ($T = \text{Size} / \text{Bandwidth}$).
   - `ROCmFP8` (26.25 GB) streams across the bus at **18.96 tok/s** (<0.003 PPL loss vs FP16).
   - `ROCmFP4` (13.55 GB) streams across the bus at **36.04 tok/s** (~99% benchmark retention).

3. **Attention Rotation & Long Context in TurboQuant:**
   - Quantized KV caches (`-ctk q8_0 -ctv turbo4`) disable attention rotation in `llama-server`.
   - Always allocate adequate context (`-c 32768` or `65536`) to prevent context shifting overflow errors.

4. **Reasoning Tag Handling for Tool-Calling Agents:**
   - When connecting CLI coding agents (like `opencode` or Claude Code), use `--reasoning-format deepseek` and cap `--reasoning-budget 1024` or `--reasoning off` to prevent infinite reasoning re-prompting loops.

5. **TTM Memory Ceiling:**
   - Default Linux kernel allocates 50% RAM to GPU.
   - Run `./scripts/apply_hardware_tweaks.sh` to set `14680064` pages (~56 GiB) on 64GB systems or `31457280` pages (~120 GiB) on 128GB systems.

---

## 5. Standard Operational Commands

```bash
# 1. Environment setup
source ./scripts/setup_env.sh

# 2. List registered models and download readiness
python3 -m rocmfpx.cli list

# 3. Start unified router on port 8010
python3 -m rocmfpx.cli serve --port 8010

# 4. Load a model
python3 -m rocmfpx.cli load qwen38-27b --variant ROCmFP4_FAST

# 5. Check server & hardware telemetry
python3 -m rocmfpx.cli status

# 6. Run benchmark suite
python3 -m rocmfpx.cli bench --port 8010

# 7. Run deterministic quality tests
python3 scripts/quality_eval.py --port 8010

# 8. Run system hardware triage
python3 -m rocmfpx.cli doctor
```

---

## 6. Future Roadmap Tasks (Next Steps for Agent)

If you are continuing development on `rocmfpx-server`, here are the top high-impact roadmap items:

- [ ] **Task A (Multi-Model Concurrency):** Support loading multiple models simultaneously on independent backend ports when unified RAM permits.
- [ ] **Task B (NPU Socket Drafter Bridge):** Implement an asynchronous IPC / Unix Domain Socket bridge connecting the 50 TOPS AMD XDNA 2 NPU (`/dev/accel/accel0`) running FastFlowLM to the target model's speculative candidate queue.
- [ ] **Task C (Embedded Web UI):** Add an embedded static HTML/JS chat interface served directly at `GET http://localhost:8010/` for instant browser chat without requiring Docker Open WebUI.
- [ ] **Task D (REST Quantization Endpoint):** Add `POST /api/v1/quantize` to allow uploading an unquantized GGUF or HF repo ID and quantizing it to ROCmFP4/ROCmFP8 asynchronously via REST API.
- [ ] **Task E (Ollama API Emulation):** Add `/api/tags`, `/api/generate`, and `/api/chat` endpoints to make `rocmfpx-server` a 100% drop-in replacement for Ollama clients on port `11434`.
