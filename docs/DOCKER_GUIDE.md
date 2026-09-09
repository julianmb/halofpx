# Docker Deployment Guide for HaloFPX Server

Run `halofpx` inside a container with full AMD GPU hardware acceleration (Mesa RADV Vulkan Wave64 and optional ROCm/HIP).

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
ls -la /dev/dri /dev/kfd
```
- `/dev/dri/card*` & `/dev/dri/renderD128`: Direct Rendering Infrastructure (Vulkan & GPU compute — **required for default Vulkan runtime**).
- `/dev/kfd`: Kernel Fusion Driver (ROCm compute — **only required if using the optional ROCm profile**).

---

## 2. Docker Compose (Recommended)

### Option A: Standalone Vulkan Server (Default — Lightweight ~350 MB)
Runs `halofpx` on port `8010` using the high-performance **Mesa RADV Vulkan Wave64** engine. Requires zero ROCm packages on the host and only mounts `/dev/dri`:

```bash
# Clone the repository
git clone https://github.com/julianmb/halofpx.git
cd halofpx

# Start server in background
docker compose up -d
```
* **OpenAI API:** `http://localhost:8010/v1`
* **Health Endpoint:** `http://localhost:8010/health`

### Option B: Dual ROCm + Vulkan Server (Optional Profile)
If you require ROCm HIP kernels for high-concurrency prefill:

```bash
docker compose --profile rocm up -d
```

### Option C: Server + Open WebUI Chat Interface
Runs both `halofpx` and Open WebUI in a single integrated network:
```bash
docker compose --profile webui up -d
```
* **ROCmFPX API:** `http://localhost:8010/v1`
* **Open WebUI Browser Chat:** `http://localhost:3000`

---

## 3. Direct `docker run` Command

### Default (Vulkan Engine — Lightweight)
```bash
docker run -d   --name halofpx   -p 8010:8010   --device=/dev/dri   --group-add video   --group-add render   --ipc=host   -v $(pwd)/models:/app/models   -v ~/.cache/huggingface/hub:/root/.cache/huggingface/hub   --restart unless-stopped   ghcr.io/julianmb/halofpx:latest
```

### Dual ROCm + Vulkan (Optional)
```bash
docker run -d   --name halofpx-rocm   -p 8010:8010   --device=/dev/kfd   --device=/dev/dri   --group-add video   --group-add render   --ipc=host   -v $(pwd)/models:/app/models   -v ~/.cache/huggingface/hub:/root/.cache/huggingface/hub   --restart unless-stopped   ghcr.io/julianmb/halofpx:rocm
```

---

## 4. Managing Models Inside the Container

You can execute `halofpx` CLI commands directly inside the running container:

```bash
# 1. List model zoo and download status
docker exec -it halofpx halofpx list

# 2. Pull model from Hugging Face
docker exec -it halofpx halofpx pull nex-n2.5-mini

# 3. Load model into memory (auto-detects Vulkan0)
docker exec -it halofpx halofpx load nex-n2.5-mini

# 4. Check active model status and GPU telemetry
docker exec -it halofpx halofpx status
```

---

## 5. Building the Docker Image Locally

### Default Vulkan Image (Fast, Lightweight ~350 MB)
```bash
docker build -t halofpx:latest .
```

### Optional Dual ROCm + Vulkan Image (~2.5 GB)
```bash
docker build -f Dockerfile.rocm -t halofpx:rocm .
```

---

## 6. Hardware Notes

* **AMD Strix Halo (APU):** Unified memory allocation is passed through automatically via `--ipc=host` and `/dev/dri` (and `/dev/kfd` for ROCm).
* **Mesa RADV Wave64:** Mesa's RADV driver executes KHR cooperative matrix operations on Strix Halo's RDNA 3.5 compute units at peak token generation speeds.
* **AMD Discrete GPUs (dGPU):** Automatically executes on native Vulkan/ROCm targets with dedicated VRAM.

---

## 7. Backend Architecture: Vulkan-First vs. Optional ROCm

### Why Vulkan is Default
On AMD Strix Halo (`gfx1151`), Mesa RADV Wave64 provides superior decode and MTP speculative throughput (+89% MTP decode speedup) while requiring **zero proprietary runtime libraries** like `libhipblas.so.3` or `libamdhip64.so.7`. This allows the default container and binaries to be tiny, portable, and reliable.

### When to use the ROCm Image
If your workload consists of massive parallel prompt processing (e.g. concurrent batch prefill with thousands of tokens per batch), ROCm 7.2.3 HIP kernels provide +7-10% higher prefill throughput. For this use case, deploy the `rocm` profile (`Dockerfile.rocm`).
