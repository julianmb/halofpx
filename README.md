# ROCmFPX Server — Unified Model Serving Framework for AMD Strix Halo

[![Hardware](https://img.shields.io/badge/Hardware-AMD_Strix_Halo_(gfx1151)-ED1C24?logo=amd)](https://www.amd.com)
[![Vulkan](https://img.shields.io/badge/Driver-Mesa_RADV_Wave64-FF5722?logo=vulkan)](https://mesa3d.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI_%26_OpenAI-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

`rocmfpx-server` is a unified model serving daemon, model zoo manager, and CLI engineered specifically for **AMD Strix Halo (Ryzen AI Max+ 395 / Radeon 8060S / gfx1151)** APUs.

Inspired by Lemonade Server, it provides a seamless single-endpoint architecture that manages downloading quantized ROCmFPX/ROCmFP4 models from Hugging Face, hot-swapping models in unified memory, and serving high-throughput OpenAI-compatible endpoints powered by **Mesa RADV Wave64 cooperative matrices (`KHR_coopmat`)** and **MTP (Multi-Token Prediction) Speculative Decoding**.

---

## 🚀 Key Features

* **📦 Unified Model Zoo:** Download, verify, and serve pre-quantized models (Qwen 3.8 27B, Nemotron 3.5 30B, Ornith 35B, DeepSeek V4 Flash, Laguna S 2.1) directly from Hugging Face.
* **🔄 Hot-Swappable Memory Management:** Dynamically load and unload models into Strix Halo's 128 GB/64 GB unified memory with automatic GPU memory reclamation.
* **⚡ Dual-Backend Hardware Acceleration:**
  * **Vulkan0 (Mesa RADV Wave64):** Fastest token decode and MTP speculative tree verification (**up to 36 tok/s** on 27B).
  * **ROCm0 (HIP):** High-throughput prompt evaluation / prefill processing (**up to 390+ tok/s**).
* **🌐 Standard OpenAI API & Management API:** Standard `/v1/chat/completions` (with streaming SSE) plus `/api/v1/{pull, load, unload, status, system-info}` endpoints on a single port (`8010`).
* **🐳 1-Command Docker Compose:** Complete stack paired with **Open WebUI** for instant local browser chat.

---

## 📦 Model Zoo Catalog

| Model ID | Display Name | Category | Available Quants | HF Repository |
|---|---|---|---|---|
| **`qwen38-27b`** | Qwen 3.8 / 27B UltraQuality | Dense / Reasoning | `ROCmFP4_FAST` (13.5G), `ROCmFP8` (26.2G), `Q3_K_S` | [julianmb/Qwen-3.8-27B-ROCmFP4-FAST-GGUF](https://huggingface.co/julianmb/Qwen-3.8-27B-ROCmFP4-FAST-GGUF) |
| **`nemotron-3.5-30b`** | NVIDIA Nemotron 3.5 Lightning 30B | High-Speed MoE | `ROCmFP4_FAST` (14.8G), `UD_Q4_K_XL` (17.1G) | [julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF](https://huggingface.co/julianmb/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-ROCmFP4-GGUF) |
| **`ornith-35b`** | Ornith 1.0 35B ROCmFPX | Multi-Slot Agent | `ROCmFPX_Speed` (19.2G), `ROCmFPX_Quality` (31.4G) | [julianmb/Ornith-1.0-35B-ROCmFPX-StrixHalo](https://huggingface.co/julianmb/Ornith-1.0-35B-ROCmFPX-StrixHalo) |
| **`deepseek-v4-flash`**| DeepSeek V4 Flash 284B MoE | Ultra-Scale MoE | `IQ2_XXS` (86.7G) | [julianmb/DeepSeek-V4-Flash-0731-IQ2XXS-STRIX](https://huggingface.co/julianmb/DeepSeek-V4-Flash-0731-IQ2XXS-STRIX) |
| **`laguna-s21`** | Laguna S 2.1 StrixKVSpine v4 | General Chat | `ROCmFP4_StrixKVSpine` (61.2G) | [laguna/laguna-s-2.1](https://huggingface.co/laguna/laguna-s-2.1) |

---

## 🛠️ Quick Start

### 1. Installation
```bash
# Clone the repository
git clone https://github.com/julianmb/rocmfpx-server.git
cd rocmfpx-server

# Install Python requirements
pip install -r requirements.txt
pip install -e .

# Set up Strix Halo environment variables
source ./scripts/setup_env.sh
```

### 2. List Models & Check Cache Status
```bash
rocmfpx list
```

### 3. Pull Model from Hugging Face
```bash
# Download Qwen 3.8 27B ROCmFP4_FAST (13.55 GiB) with SHA256 verification
rocmfpx pull qwen38-27b --variant ROCmFP4_FAST
```

### 4. Start Server
```bash
# Start unified router on port 8010
rocmfpx serve

# Or auto-load an initial model on startup:
rocmfpx serve -m qwen38-27b
```

### 5. Load & Switch Models via CLI
```bash
# Load Qwen 3.8 27B
rocmfpx load qwen38-27b

# Check active model status and APU telemetry
rocmfpx status

# Switch to Nemotron 3.5 30B
rocmfpx load nemotron-3.5-30b

# Unload model from memory
rocmfpx unload
```

---

## 🔌 Client & IDE Integration

Connect your local tools to `http://localhost:8010/v1`:

* **Open WebUI:** Set Base URL to `http://localhost:8010/v1` and API Key to `sk-no-key`.
* **Continue.dev:** Add `rocmfpx-server` as provider in `~/.continue/config.json`.
* **Cursor IDE:** Override OpenAI Base URL to `http://localhost:8010/v1`.

👉 **See the complete [Client Integration Guide (docs/CLIENT_INTEGRATION.md)](docs/CLIENT_INTEGRATION.md)**.

---

## 🐳 Docker Deployment Options

### Option A: Lightweight Standalone Server (Default)
Runs only the high-performance ROCmFPX server (zero extra RAM overhead for web frontends):
```bash
docker compose up -d
```
* **API Endpoint:** `http://localhost:8010/v1`

### Option B: Server + Open WebUI Chat Interface
Runs both the backend server and Open WebUI in a unified stack:
```bash
docker compose --profile webui up -d
```
* **ROCmFPX API:** `http://localhost:8010/v1`
* **Open WebUI:** `http://localhost:3000`

---

## 🤝 Upstream Integration & Engine Core

`rocmfpx-server` wraps and orchestrates the **[charlie12345/ROCmFPX](https://github.com/charlie12345/ROCmFPX)** engine, compiling directly against pinned builds (`e87d53e (213)`) or downloading pre-compiled Strix Halo binaries via `./scripts/build_engine.sh --prebuilt`.

---

## 📄 License
Apache 2.0 License.
