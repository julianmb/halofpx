# HaloFPX — High-Throughput Unified Model Server for AMD Strix Halo (iGPU + NPU)

[![Hardware](https://img.shields.io/badge/Hardware-AMD_Strix_Halo_%26_Radeon_GPUs-ED1C24?logo=amd)](https://www.amd.com)
[![Vulkan](https://img.shields.io/badge/Driver-Mesa_RADV_Wave64-FF5722?logo=vulkan)](https://mesa3d.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI_%26_OpenAI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

`HaloFPX` is a unified, high-performance model serving daemon, model zoo manager, and CLI engineered specifically for **AMD Strix Halo (Ryzen AI Max APUs / 64GB–128GB UMA)** and **AMD Radeon GPUs**.

Inspired by Lemonade Server, it provides a seamless single-endpoint architecture that manages downloading quantized ROCmFPX/ROCmFP4 models from Hugging Face, dynamically hot-swapping models in unified memory or dedicated VRAM, and serving high-throughput OpenAI-compatible endpoints powered by **Mesa RADV Wave64 cooperative matrices (`KHR_coopmat`)** and **MTP (Multi-Token Prediction) Speculative Decoding**.

---

## 🔗 Related Repositories
* **[julianmb/q38rocm](https://github.com/julianmb/q38rocm):** Dedicated single-model deep-dive and standalone deployment package specifically for **Qwen 3.8 27B** on AMD Strix Halo.
* **[charlie12345/ROCmFPX](https://github.com/charlie12345/ROCmFPX):** Upstream inference engine and RDNA cooperative matrix kernel toolchain.

---

## 🚀 Key Features

* **📦 Unified Model Zoo:** Download, verify, and serve pre-quantized models (Qwen 3.8 27B, Nemotron 3.5 30B, Ornith 35B, DeepSeek V4 Flash, Laguna S 2.1) directly from Hugging Face.
* **🎮 Dynamic AMD Hardware Detection:** Auto-detects compute targets (`gfx1151`, `gfx1201`, etc.) and applies hardware-specific execution flags.
* **🔄 Hot-Swappable Memory Management:** Dynamically load and unload models into available unified memory or dedicated VRAM with automatic GPU memory reclamation.
* **⚡ Dual-Backend Hardware Acceleration:**
  * **Vulkan0 (Mesa RADV Wave64):** Fastest token decode and MTP speculative tree verification (**up to 36 tok/s** on 27B).
  * **ROCm0 (HIP):** High-throughput prompt evaluation / prefill processing (**up to 390+ tok/s**).
* **🔒 Optional API Key Authentication:** Secure your endpoints via `HALOFPX_API_KEY` (disabled by default for local development).
* **🌐 Standard OpenAI API & Management API:** Standard `/v1/chat/completions` (with streaming SSE) plus `/api/v1/{pull, load, unload, status, system-info}` endpoints on a single port (`8010`).
* **🐳 Modular Docker Compose:** Run lightweight standalone or pair with **Open WebUI** via `--profile webui`.

---

## 📦 Model Zoo Catalog

| Model ID | Display Name | Category | Available Quants | Min VRAM | HF Repository |
|---|---|---|---|---|---|
| **`qwen38-27b`** | Qwen 3.8 / 27B UltraQuality | Dense / Reasoning | `ROCmFP4_FAST` (13.5G), `ROCmFP8` (26.2G), `Q3_K_S` | **16 GB** (Fits 16GB+ GPUs) | [julianmb/Qwen-3.8-27B-ROCmFP4-FAST-GGUF](https://huggingface.co/julianmb/Qwen-3.8-27B-ROCmFP4-FAST-GGUF) |
| **`nemotron-3.5-30b`** | NVIDIA Nemotron 3.5 Lightning 30B | High-Speed MoE | `ROCmFP4_FAST` (14.8G), `ROCmFP4_STRIX_LEAN` (15.2G) | **16 GB** (Fits 16GB+ GPUs) | [julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF](https://huggingface.co/julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF) |
| **`ornith-35b`** | Ornith 1.0 35B ROCmFPX | Multi-Slot Agent | `ROCmFPX_Speed` (19.2G), `ROCmFPX_Quality` (31.4G) | **22 GB** (Strix / 24GB+ GPUs) | [julianmb/Ornith-1.0-35B-ROCmFPX-StrixHalo](https://huggingface.co/julianmb/Ornith-1.0-35B-ROCmFPX-StrixHalo) |
| **`deepseek-v4-flash`**| DeepSeek V4 Flash 284B MoE | Ultra-Scale MoE | `IQ2_XXS` (86.7G) | **90 GB** (128GB Strix Halo) | [julianmb/DeepSeek-V4-Flash-0731-IQ2XXS-STRIX](https://huggingface.co/julianmb/DeepSeek-V4-Flash-0731-IQ2XXS-STRIX) |
| **`laguna-s21`** | Laguna S 2.1 StrixKVSpine v4 | General Chat | `ROCmFP4_StrixKVSpine` (61.2G) | **64 GB** (64GB+ Strix Halo) | [julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4](https://huggingface.co/julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4) |

👉 **See [Hardware Support & VRAM Sizing Guide (docs/HARDWARE_SUPPORT.md)](docs/HARDWARE_SUPPORT.md)** for memory sizing tables across AMD APUs and discrete GPUs.

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

### 2. List Models & Check Cache Status
```bash
halofpx list
```

### 3. Pull Model from Hugging Face
```bash
# Download Qwen 3.8 27B ROCmFP4_FAST (13.55 GiB) with SHA256 verification
halofpx pull qwen38-27b --variant ROCmFP4_FAST
```

### 4. Start Server
```bash
# Start unified router on port 8010
halofpx serve

# Or auto-load an initial model on startup:
halofpx serve -m qwen38-27b
```

### 5. Load & Switch Models with Workload Tuning
```bash
# Single-User Interactive Chat (Fastest single-stream TPS: n5 / p0.50)
halofpx load qwen38-27b --draft-n 5 --draft-p 0.50

# Parallel Multi-Agent Concurrency (4 Slots: n6 / p0.60 -> 40.5 TPS aggregate)
halofpx load qwen38-27b --slots 4 --draft-n 6 --draft-p 0.60

# Check active model status and APU telemetry
halofpx status

# Switch to Nemotron 3.5 30B (High-speed MoE @ 95 tok/s)
halofpx load nemotron-3.5-30b

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
  --device=/dev/kfd --device=/dev/dri \
  --group-add video --group-add render \
  --ipc=host \
  -v $(pwd)/models:/app/models \
  -v ~/.cache/huggingface/hub:/root/.cache/huggingface/hub \
  --name halofpx-server \
  ghcr.io/julianmb/halofpx:latest
```

👉 **See the complete [Docker Deployment Guide (docs/DOCKER_GUIDE.md)](docs/DOCKER_GUIDE.md)** for GPU passthrough prerequisites, container CLI commands, and local builds.

---

## 🤝 Upstream Integration & Engine Core

`HaloFPX` wraps and orchestrates the **[charlie12345/ROCmFPX](https://github.com/charlie12345/ROCmFPX)** engine, compiling directly against pinned builds (`e87d53e (213)`) or downloading pre-compiled Strix Halo binaries via `./scripts/build_engine.sh --prebuilt`.

---

## 📄 License
Apache 2.0 License.
