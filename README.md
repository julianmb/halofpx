# HaloFPX — High-Performance Model Server & Zoo for AMD Strix Halo

[![Hardware](https://img.shields.io/badge/Hardware-AMD_Strix_Halo_%26_Radeon_GPUs-ED1C24?logo=amd)](https://www.amd.com)
[![Vulkan](https://img.shields.io/badge/Driver-Mesa_RADV_Wave64-FF5722?logo=vulkan)](https://mesa3d.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI_%26_OpenAI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **The high-performance, cutting-edge Lemonade alternative engineered for AMD Strix Halo (Ryzen AI Max APUs / 64GB–128GB UMA) and AMD Radeon GPUs.**
> 
> *HaloFPX delivers the familiar developer experience and single-endpoint architecture of Lemonade, but supercharged with the latest frontier models, bleeding-edge RDNA 3.5 matrix kernels, and silicon-tuned profiles not available in standard Lemonade.*

---

## 🍋 HaloFPX vs. Standard Lemonade — Why HaloFPX?

HaloFPX is engineered from the silicon up for AMD Strix Halo (`gfx1151`) and high-end Radeon GPUs. While maintaining complete CLI and model-cache interoperability with Lemonade, it unlocks performance and architectures standard Lemonade cannot reach:

| Capability | Standard Lemonade | **HaloFPX** 🚀 |
|---|---|---|
| **Next-Gen MoE Models** | Generic catalog; misses latest large MoE quants | **Day-0 support**: Ling-3.0-Flash (124B), Qwen 3.8 Flash Next (125B), DeepSeek V4 Flash (284B), Ornith 1.5 (35B) |
| **Compute Kernels** | Generic upstream llama.cpp / stock ROCm kernels | **Mesa RADV Wave64 cooperative matrices (`KHR_coopmat`)** on RDNA 3.5 + Dual-Backend ROCm/Vulkan |
| **Quantization Formats** | Stock GGUF (`Q4_K_M`, standard quants) | **Custom ROCmFP4 / ROCmFP4_FAST** (direct hardware block mapping, −16.7% size, +13.5% decode speed) |
| **Silicon-Tuned Profiles** | One-size-fits-all server flags | **Hardware-benchmarked `run_config`**: tuned MTP speculation, TurboQuant KV (`q8_0`), `-ctxcp`, `-cram`, zero flag guessing |
| **Long Context Scaling** | Standard context limits; risks OOM on unified APUs | **Validated 262K context** (524K tokens across 4 slots) with TurboQuant KV in unified memory |
| **CLI & Workflow Parity** | `lemonade {run, list, chat, backends, delete}` | **100% command parity**: `halofpx run/chat/list/backends/delete`, native drop-in, zero retraining |
| **Lemonade Cache Sharing** | Standalone cache (`/var/lib/lemonade/models`) | **Bi-directional cache sharing**: reads Lemonade user models, shares weights, resolves aliases seamlessly |
| **Multimodal Vision** | Manual projector configuration | **Automatic vision discovery & loading** (`mmproj`) verified over standard OpenAI `/v1/chat/completions` |

---

## ⚡ Quick Instructions — How to Run a Model

Run any model in seconds using familiar Lemonade-compatible commands or launch the OpenAI-compatible single-endpoint server. Silicon-tuned configurations (`run_config`, TurboQuant KV, Wave64 cooperative matrices) are applied automatically with zero flag guessing.

### 1. Interactive Terminal Chat (`halofpx run`)
```bash
# List available models and check download status
halofpx list

# Launch an interactive chat session with any model (auto-loads tuned config):
halofpx run Ling-3.0-Flash

# Or run Qwen 3.8 Flash Next or Ornith 1.5:
halofpx run qwen38-flash-next
halofpx run ornith-1.5-35b
```

### 2. Start OpenAI-Compatible Server (`halofpx serve`)
```bash
# Start server with an auto-loaded model on http://localhost:8010
halofpx serve -m Ling-3.0-Flash

# Query via standard OpenAI /v1/chat/completions:
curl http://localhost:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Ling-3.0-Flash",
    "messages": [{"role": "user", "content": "Explain quantum computing concisely."}]
  }'
```

### 3. Dynamic Model Switching & Telemetry
```bash
# Hot-swap to a different model dynamically without restarting the server:
halofpx load qwen38-flash-next

# Check APU memory residency and real-time status:
halofpx status

# Unload from memory when finished:
halofpx unload
```

---

## 🔗 Related Projects

* **[julianmb/q38rocm](https://github.com/julianmb/q38rocm):** Dedicated single-model deep-dive and standalone deployment package specifically for **Qwen 3.8 27B** on AMD Strix Halo (up to 36 tok/s via MTP Speculation, TurboQuant & Mesa RADV Wave64).
* **[julianmb/haloq38flash](https://github.com/julianmb/haloq38flash):** Dedicated optimization deep-dive for **Qwen 3.8 Flash Next 125B MoE** on AMD Strix Halo (split-PLE quant, up to 56 tok/s, 262K context).

---

## 🚀 Key Features

* **📦 Unified Model Zoo:** Download, verify, and serve pre-quantized models (Ornith 1.5 35B, Qwen 3.8 27B, Nemotron 3.5 30B, DeepSeek V4 Flash, Laguna S 2.1) directly from Hugging Face.
* **🎯 Per-Model Optimization Profiles:** Each model carries a benchmarked `run_config` — quant preset, KV-cache types, backend preference, MTP on/off — applied automatically on load. No flag archaeology.
* **👁️ Automatic Vision (Multimodal):** Models with a projector (`ornith-1.5-35b`) pull and verify their `mmproj` alongside the weights; image prompts work over the standard OpenAI API.
* **📏 Validated Long Context:** Ornith validated at the full 262K training context; TurboQuant KV enables 4-slot × 131K contexts (524K total tokens) in unified memory with zero OOM.
* **🎮 Dynamic AMD Hardware Detection:** Auto-detects compute targets (`gfx1151`, `gfx1201`, etc.) and applies hardware-specific execution flags.
* **🔄 Hot-Swappable Memory Management:** Dynamically load and unload models into available unified memory or dedicated VRAM with automatic GPU memory reclamation.
* **⚡ Dual-Backend Hardware Acceleration:**
  * **Vulkan0 (Mesa RADV Wave64):** Fastest token decode and MTP speculative tree verification (**up to 36 tok/s** on 27B).
  * **ROCm0 (HIP):** High-throughput prompt evaluation / prefill processing (**up to 390+ tok/s**).
* **🚀 Measured Speed Increase Over Standard GGUF:** ROCmFP4/ROCmFP4_FAST quants beat stock `Q4_K_M` in **decode throughput and size** on Strix Halo (`gfx1151`). See the [benchmark table](#-speed-increase-over-standard-gguf) below.
* **🔒 Optional API Key Authentication:** Secure your endpoints via `HALOFPX_API_KEY` (disabled by default for local development).
* **🦙 Ollama-Compatible API:** `/api/tags`, `/api/chat`, `/api/generate` and `/api/version` let existing Ollama clients and tools work against halofpx drop-in.
* **🌐 Standard OpenAI API & Management API:** Standard `/v1/chat/completions` (with streaming SSE) plus `/api/v1/{pull, load, unload, status, system-info}` endpoints on a single port (`8010`).
* **🐳 Modular Docker Compose:** Run lightweight standalone or pair with **Open WebUI** via `--profile webui`.

---

## 📦 Model Zoo & Verified Hardware Benchmarks

All models ship pre-quantized with silicon-tuned execution profiles. Measurements taken directly on **AMD Ryzen AI Max+ 395 (40 CU Radeon 8060S @ 2.9 GHz, 128 GB 256-bit LPDDR5X, Linux 7.0, Mesa 26.0 RADV Wave64 / Vulkan0)**:

| Model Name & CLI ID | Category | Quant & Size | Min VRAM | Prefill (`pp512`) | Decode *(Bare / MTP)* | Verified Date | HF Repository & Quick Command |
|---|---|---|---|---|---|---|---|
| **Qwen 3.8 Flash Next 125B MoE** ⚡<br>`qwen38-flash-next` | Next-Gen MoE / Hybrid Attention | `ROCmFP4_ple16`<br>(87.1 GiB) | 68 GB | **413.09 tok/s** *(CM1)* | **28.96** / 🔥 **34.60 tok/s** | `2026-09-10` | [unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF)<br>`halofpx run qwen38-flash-next` |
| **Ling 3.0 Flash 124B MoE** ⚡<br>`ling3-flash` | Frontier 124B MoE / Reasoning | `Q4_K_M`<br>(71.7 GiB) | 80 GB | **340.50 tok/s** | **45.23** / 🔥 **55.10 tok/s** | `2026-09-02` | [inclusionAI/Ling-3.0-flash-GGUF](https://huggingface.co/inclusionAI/Ling-3.0-flash-GGUF)<br>`halofpx run Ling-3.0-Flash` |
| **Nex N2.5 Mini 35B-A3B MoE** ⭐<br>`nex-n2.5-mini` | Agentic Reasoning / Vision | `ROCmFP4_LEAN`<br>(17.3 GiB) | 22 GB | **1180.20 tok/s** | **76.92 tok/s** | `2026-08-30` | [julianmb/Nex-N2.5-mini-ROCmFP4-GGUF](https://huggingface.co/julianmb/Nex-N2.5-mini-ROCmFP4-GGUF)<br>`halofpx run nex-n2.5-mini` |
| **Ornith 1.5 35B-A3B MoE** ⭐<br>`ornith-1.5-35b` | Agentic Coding / Vision MoE | `ROCmFP4`<br>(18.2 GiB) | 22 GB | **1190.40 tok/s** | **76.90** / 🔥 **105.60 tok/s** | `2026-08-28` | [julianmb/Ornith-1.5-35B-A3B-ROCmFP4-GGUF](https://huggingface.co/julianmb/Ornith-1.5-35B-A3B-ROCmFP4-GGUF)<br>`halofpx run ornith-1.5-35b` |
| **Qwen 3.8 / 27B UltraQuality**<br>`qwen38-27b` | Dense / Reasoning | `ROCmFP4_FAST`<br>(13.5 GiB) | 16 GB | **385.65 tok/s** | **14.02** / 🔥 **33.80 tok/s** | `2026-08-25` | [julianmb/Qwen-3.8-27B-ROCmFP4-FAST-GGUF](https://huggingface.co/julianmb/Qwen-3.8-27B-ROCmFP4-FAST-GGUF)<br>`halofpx run qwen38-27b` |
| **NVIDIA Nemotron 3.5 Lightning 30B**<br>`nemotron-3.5-30b` | High-Speed MoE | `ROCmFP4_FAST`<br>(14.8 GiB) | 16 GB | **1286.24 tok/s** | **52.40** / 🔥 **95.20 tok/s** | `2026-08-22` | [julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF](https://huggingface.co/julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF)<br>`halofpx pull nemotron-3.5-30b` |
| **DeepSeek V4 Flash 284B MoE**<br>`deepseek-v4-flash` | Ultra-Scale MoE | `IQ2_XXS`<br>(86.7 GiB) | 90 GB | **195.40 tok/s** | **22.50** / **32.00 tok/s** | `2026-08-20` | [julianmb/DeepSeek-V4-Flash-0731-IQ2XXS-STRIX](https://huggingface.co/julianmb/DeepSeek-V4-Flash-0731-IQ2XXS-STRIX)<br>`halofpx pull deepseek-v4-flash` |
| **Laguna S 2.1 StrixKVSpine v4**<br>`laguna-s21` | General Chat | `ROCmFP4_Spine`<br>(60.9 GiB) | 64 GB | **390.13 tok/s** | **34.05 tok/s** | `2026-08-15` | [julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4](https://huggingface.co/julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4)<br>`halofpx pull laguna-s21` |
| **Ornith 1.0 35B ROCmFPX**<br>`ornith-35b` | Multi-Slot Agent | `ROCmFPX_Speed`<br>(18.4 GiB) | 22 GB | **1194.19 tok/s** | **11.20** / **115.0+ tok/s** *(16s)* | `2026-08-15` | [julianmb/Ornith-1.0-35B-ROCmFPX-StrixHalo](https://huggingface.co/julianmb/Ornith-1.0-35B-ROCmFPX-StrixHalo)<br>`halofpx pull ornith-35b` |

⭐ = vision-capable (`mmproj` included). ⚡ = cutting-edge large MoE architecture. Full methodology: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

👉 **See [Hardware Support & VRAM Sizing Guide (docs/HARDWARE_SUPPORT.md)](docs/HARDWARE_SUPPORT.md)** for memory sizing tables across AMD APUs and discrete GPUs.

### 🔬 How to Run & Record Benchmarks

HaloFPX provides automated benchmarking runners to measure prompt prefill throughput, token decode speed, TTFT, and MTP draft acceptance rates:

```bash
# 1. Automated performance benchmark (auto-exports timestamped Markdown & JSON reports)
python3 scripts/benchmark.py --model qwen38-27b --device Vulkan0

# 2. Context scaling benchmark up to 262K tokens
python3 scripts/context_scaling_benchmark.py --model ornith-1.5-35b

# 3. Low-level engine benchmark using llama-bench
llama-bench -m models/qwen38-flash-next/Qwen3.8-Flash-Next-ROCmFP4-FAST-v2-ple16.gguf -p 512 -n 128 -ngl 99
```

Benchmark outputs are stored with timestamps under `benchmarks/benchmark_YYYYMMDD_HHMMSS.md` and `benchmarks/benchmark_YYYYMMDD_HHMMSS.json`.

---

## 🚀 Speed Increase Over Standard GGUF

Measured on **AMD Ryzen AI Max+ 395 (Radeon 8060S, `gfx1151`, Mesa RADV Wave64)** with identical prompts — ROCmFP4-family quants beat stock `Q4_K_M` on decode speed **and** model size:

| Model | Stock `Q4_K_M` | ROCmFP4 / ROCmFP4_FAST | Decode Speedup | Size Savings |
|---|---|---|---|---|
| **Qwen 3.8 27B** | 15.92 GiB — **12.35 tok/s** | 13.55 GiB — **14.02 tok/s** | **+13.5%** | **−14.9%** |
| **Ornith 1.5 35B-A3B** | 21.80 GiB — **71.5–71.7 tok/s** | 18.16 GiB — **76.9 tok/s** | **+7.5%** | **−16.7%** |
| **Nex N2.5 Mini 35B-A3B** | 19.71 GiB — **72.76 tok/s** | 17.32 GiB — **76.92 tok/s** | **+5.7%** | **−12.1%** |

Additional gains over stock GGUF on Strix Halo:

* **Prefill:** ROCmFP4 quant blocks map directly to RDNA 3.5 cooperative-matrix (`KHR_coopmat`) operands — faster prompt evaluation at equal context, without the multi-scale dequantization overhead of `Q4_K` blocks.
* **Combined with MTP speculative decoding** (Qwen 3.8 27B, `n4/p0.0`): **33.8 tok/s sustained = 2.40× over stock baseline** (12.35 tok/s).
* **KV cache:** TurboQuant KV (`q8_0`) shrinks memory footprint, enabling 4-slot × 131K contexts (524K total tokens) in unified memory with zero OOM.

Full methodology and raw numbers: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

---

## 🛠️ Installation & Advanced Setup

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/julianmb/halofpx.git
cd halofpx

# Install Python requirements and CLI
pip install -r requirements.txt
pip install -e .

# Set up environment variables for AMD Strix Halo
source ./scripts/setup_env.sh
```

### 2. Backend Inspection & Lemonade Cache Sync
```bash
# Check available hardware acceleration backends (ROCm HIP, Vulkan RADV Wave64)
halofpx backends

# Inspect configuration or synchronize cache with Lemonade daemon
halofpx config show
halofpx config sync-lemonade
```

### 3. Advanced Workload Tuning & Concurrency
```bash
# Parallel multi-agent concurrency (4 slots -> ~40.5 tok/s aggregate)
halofpx load qwen38-27b --slots 4 --draft-n 6 --draft-p 0.60

# Single-user interactive chat with burst MTP
halofpx load qwen38-27b --draft-n 5 --draft-p 0.50

# Long context scaling up to 262K tokens with TurboQuant KV in unified memory
halofpx load ornith-1.5-35b --ctx 262144
```

---

## 🔌 Client & IDE Integration

Connect your local tools to `http://localhost:8010/v1`:

* **Open WebUI:** Set Base URL to `http://localhost:8010/v1` and API Key to `sk-no-key`.
* **Continue.dev:** Add `halofpx` as provider in `~/.continue/config.json`.
* **Cursor IDE:** Override OpenAI Base URL to `http://localhost:8010/v1`.

👉 **See the complete [Client Integration Guide (docs/CLIENT_INTEGRATION.md)](docs/CLIENT_INTEGRATION.md)**.

---

## 🐳 Docker Deployment Options

### Option A: Lightweight Standalone Server (Default)
Runs only the high-performance HaloFPX server (zero extra RAM overhead for web frontends):
```bash
docker compose up -d
```
* **API Endpoint:** `http://localhost:8010/v1`

### Option B: Server + Open WebUI Chat Interface
Runs both the backend server and Open WebUI in a unified stack:
```bash
docker compose --profile webui up -d
```
* **HaloFPX API:** `http://localhost:8010/v1`
* **Open WebUI:** `http://localhost:3000`

### Option C: Direct `docker run`
```bash
docker run -d -p 8010:8010 \
  --device=/dev/dri \
  --group-add video --group-add render \
  --ipc=host \
  -v $(pwd)/models:/app/models \
  -v ~/.cache/huggingface/hub:/root/.cache/huggingface/hub \
  --name halofpx-server \
  ghcr.io/julianmb/halofpx:latest
# Note: For optional ROCm prefill acceleration, also add --device=/dev/kfd and use ghcr.io/julianmb/halofpx:rocm
```

👉 **See the complete [Docker Deployment Guide (docs/DOCKER_GUIDE.md)](docs/DOCKER_GUIDE.md)** for GPU passthrough prerequisites, container CLI commands, and local builds.

---

## 🤝 Upstream Integration & Engine Core

`HaloFPX` wraps and orchestrates the **[charlie12345/ROCmFPX](https://github.com/charlie12345/ROCmFPX)** engine, compiling directly against pinned builds (`e87d53e (213)`) or downloading pre-compiled Strix Halo binaries via `./scripts/build_engine.sh --prebuilt`.

---

## 📄 License
Apache 2.0 License.
