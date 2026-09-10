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

## 🏁 Flagship: Ornith-1.5-35B-A3B — Optimized

The zoo's current headliner, validated end-to-end on Ryzen AI Max+ 395 (Radeon 8060S):

| Metric | Result |
|---|---|
| Decode throughput | **76.9 tok/s** (+7.5% vs stock `Q4_K_M`, −16.7% size) |
| Context window | **262,144 tokens — full training capacity, validated clean load** |
| Long-context speed | 58.5 tok/s decode / 140 tok/s prefill @ 262K |
| Quality | Perplexity **within 5.5%** of `Q4_K_M` (5.95 vs 5.64, wikitext-2) |
| Vision | ✅ Multimodal — BF16 projector pulled & served automatically |
| Tuning | MTP measured as a net loss on this arch → **shipped disabled**, cache mode enabled |

One command gets all of it — weights, vision projector, checksums:

```bash
halofpx pull ornith-1.5-35b
halofpx serve -m ornith-1.5-35b
```

---

## 🔗 Related Repositories
* **[julianmb/q38rocm](https://github.com/julianmb/q38rocm):** Dedicated single-model deep-dive and standalone deployment package specifically for **Qwen 3.8 27B** on AMD Strix Halo.
* **[charlie12345/ROCmFPX](https://github.com/charlie12345/ROCmFPX):** Upstream inference engine and RDNA cooperative matrix kernel toolchain.

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

## 📦 Model Zoo Catalog

All models ship pre-optimized. Measured decode on Ryzen AI Max+ 395 (`gfx1151`):

| Model Name | Model ID | Category | Default Quant | Measured Decode *(bare / MTP)* | Min VRAM | HF Repository / Origin |
|---|---|---|---|---|---|---|
| **Ling 3.0 Flash 124B MoE** ⚡ | `ling3-flash` | Frontier 124B MoE / Reasoning | `Q4_K_M` (71.7G) | **32.0+ tok/s** | **80 GB** | [inclusionAI/Ling-3.0-flash-GGUF](https://huggingface.co/inclusionAI/Ling-3.0-flash-GGUF) |
| **Ornith 1.5 35B-A3B MoE** ⭐ | `ornith-1.5-35b` | Agentic Coding / Vision MoE | `ROCmFP4` (18.2G) | **76.9** / 🔥 **105.6 tok/s** *(MTP n4/p0.6)* | **22 GB** | [julianmb/Ornith-1.5-35B-A3B-ROCmFP4-GGUF](https://huggingface.co/julianmb/Ornith-1.5-35B-A3B-ROCmFP4-GGUF) |
| **Qwen 3.8 Flash Next 125B MoE** ⚡ | `qwen38-flash-next` | Next-Gen MoE / Hybrid Attention | `ROCmFP4_FAST_ple16` (87.1G) | **27.3+ tok/s** | **68 GB** | [unsloth/Qwen3.8-Flash-Next-GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF) |
| **Qwen 3.8 / 27B UltraQuality** | `qwen38-27b` | Dense / Reasoning | `ROCmFP4_FAST` (13.5G) | **14.0** / 🔥 **30.6–36.0 tok/s** | **16 GB** | [julianmb/Qwen-3.8-27B-ROCmFP4-FAST-GGUF](https://huggingface.co/julianmb/Qwen-3.8-27B-ROCmFP4-FAST-GGUF) |
| **Nex N2.5 Mini 35B-A3B MoE** ⭐ | `nex-n2.5-mini` | Agentic Reasoning / Vision | `ROCmFP4_STRIX_LEAN` (17.3G) | **76.9 tok/s** *(Vulkan)* | **22 GB** | [julianmb/Nex-N2.5-mini-ROCmFP4-GGUF](https://huggingface.co/julianmb/Nex-N2.5-mini-ROCmFP4-GGUF) |
| **NVIDIA Nemotron 3.5 Lightning 30B** | `nemotron-3.5-30b` | High-Speed MoE | `ROCmFP4_FAST` (14.8G) | **52.4** / 🔥 **84.5–95.2 tok/s** | **16 GB** | [julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF](https://huggingface.co/julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF) |
| **DeepSeek V4 Flash 284B MoE** | `deepseek-v4-flash` | Ultra-Scale MoE | `IQ2_XXS` (86.7G) | **22.5** / **32.0 tok/s** | **90 GB** | [julianmb/DeepSeek-V4-Flash-0731-IQ2XXS-STRIX](https://huggingface.co/julianmb/DeepSeek-V4-Flash-0731-IQ2XXS-STRIX) |
| **Laguna S 2.1 StrixKVSpine v4** | `laguna-s21` | General Chat | `ROCmFP4_StrixKVSpine` (61.2G) | — | **64 GB** | [julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4](https://huggingface.co/julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4) |
| **Ornith 1.0 35B ROCmFPX** | `ornith-35b` | Multi-Slot Agent | `ROCmFPX_Speed` (19.2G) | **11.2** / **115+ tok/s** *(16 slots)* | **22 GB** | [julianmb/Ornith-1.0-35B-ROCmFPX-StrixHalo](https://huggingface.co/julianmb/Ornith-1.0-35B-ROCmFPX-StrixHalo) |

⭐ = flagship, vision-capable (`mmproj` included). ⚡ = cutting-edge large MoE architecture. Full methodology: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

👉 **See [Hardware Support & VRAM Sizing Guide (docs/HARDWARE_SUPPORT.md)](docs/HARDWARE_SUPPORT.md)** for memory sizing tables across AMD APUs and discrete GPUs.

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

## 🛠️ Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/julianmb/halofpx.git
cd halofpx

# Install Python requirements and CLI
pip install -r requirements.txt
pip install -e .

# Set up environment variables
source ./scripts/setup_env.sh
```

### 2. Lemonade-Compatible CLI & Interactive Workflows

HaloFPX provides drop-in command parity with Lemonade:

```bash
# List all models with human-recognized names, download state, and VRAM sizing
halofpx list
halofpx list --downloaded

# Interactive chat directly from terminal (auto-loads model with tuned silicon config)
halofpx chat ling3-flash
halofpx run Ling-3.0-Flash

# Check available hardware acceleration backends (ROCm, Vulkan RADV Wave64)
halofpx backends

# Inspect or sync configuration with Lemonade daemon
halofpx config show
halofpx config sync-lemonade
```

### 3. Server Deployment (OpenAI-Compatible Single Endpoint)

```bash
# Pull weights + vision projector, SHA256-verified
halofpx pull ornith-1.5-35b

# Serve with tuned profile applied automatically (ROCmFP4 quant, q8_0 KV, cache mode on):
halofpx serve -m ornith-1.5-35b

# Point any OpenAI client at http://localhost:8010/v1
curl http://localhost:8010/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Ling-3.0-Flash",
    "messages": [{"role": "user", "content": "Explain quantum teleportation concisely."}]
  }'
```

### 4. Dynamic Model Switching & Workload Tuning
```bash
# Qwen 3.8 27B — single-user interactive chat (n5 / p0.50 burst MTP)
halofpx load qwen38-27b --draft-n 5 --draft-p 0.50

# Parallel multi-agent concurrency (4 slots -> ~40.5 tok/s aggregate)
halofpx load qwen38-27b --slots 4 --draft-n 6 --draft-p 0.60

# High-speed MoE @ up to 95 tok/s
halofpx load nemotron-3.5-30b

# Check active model status and APU telemetry
halofpx status

# Unload model from memory
halofpx unload
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
