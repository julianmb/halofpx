# Docker Deployment Guide for ROCmFPX Server

Run `halofpx` inside a container with full AMD GPU hardware acceleration (Mesa RADV Vulkan Wave64 and ROCm/HIP).

---

## 1. Prerequisites (Host Setup)

### 1.1 Add User to GPU Groups
Ensure your host user has permissions to access AMD GPU device nodes:
```bash
sudo usermod -aG video,render $USER
```
*(Log out and log back in for group changes to take effect).*

### 1.2 Verify Device Nodes
Ensure AMD GPU device nodes are visible on the host:
```bash
ls -la /dev/kfd /dev/dri
```
- `/dev/kfd`: Kernel Fusion Driver (ROCm compute).
- `/dev/dri/card*` & `/dev/dri/renderD128`: Direct Rendering Infrastructure (Vulkan & GPU graphics).

---

## 2. Docker Compose (Recommended)

### Option A: Standalone High-Performance Server (Default)
Runs only `halofpx` on port `8010` (consuming zero extra RAM for web servers):
```bash
# Clone the repository
git clone https://github.com/julianmb/halofpx.git
cd halofpx

# Start server in background
docker compose up -d
```
* **OpenAI API:** `http://localhost:8010/v1`
* **Health Endpoint:** `http://localhost:8010/health`

### Option B: Server + Open WebUI Chat Interface
Runs both `halofpx` and Open WebUI in a single integrated network:
```bash
docker compose --profile webui up -d
```
* **ROCmFPX API:** `http://localhost:8010/v1`
* **Open WebUI Browser Chat:** `http://localhost:3000`

---

## 3. Direct `docker run` Command

If you prefer launching without `docker-compose.yml`:

```bash
docker run -d \
  --name halofpx \
  -p 8010:8010 \
  --device=/dev/kfd \
  --device=/dev/dri \
  --group-add video \
  --group-add render \
  --ipc=host \
  -v $(pwd)/models:/app/models \
  -v ~/.cache/huggingface/hub:/root/.cache/huggingface/hub \
  --restart unless-stopped \
  ghcr.io/julianmb/halofpx:latest
```

---

## 4. Managing Models Inside the Container

You can execute `halofpx` CLI commands directly inside the running container:

```bash
# 1. List model zoo and download status
docker exec -it halofpx halofpx list

# 2. Pull Qwen 3.8 27B ROCmFP4 from Hugging Face
docker exec -it halofpx halofpx pull qwen38-27b

# 3. Load model into memory
docker exec -it halofpx halofpx load qwen38-27b

# 4. Check active model status and GPU telemetry
docker exec -it halofpx halofpx status

# 5. Switch to Nemotron 3.5 30B
docker exec -it halofpx halofpx load nemotron-3.5-30b
```

---

## 5. Building the Docker Image Locally

To build the container image from source:
```bash
docker build -t halofpx:latest .
```

---

## 6. Hardware Notes

* **AMD Strix Halo (APU):** Unified memory allocation is passed through automatically via `--ipc=host` and `/dev/kfd`.
* **AMD Discrete GPUs (dGPU):** Automatically executes on native ROCm targets with dedicated VRAM.
