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

---

## 7. Troubleshooting: `error while loading shared libraries: libhipblas.so.3`

The pre-compiled ROCmFPX engine binaries link against the ROCm 7.2.x runtime
(`libhipblas.so.3`, `librocblas.so.5`, `libamdhip64.so.7`, `libhipblaslt.so.1`,
`libhsa-runtime64.so.1`, `librocprofiler-register.so.0`), which a base Ubuntu
image does not include. There are two ways to resolve it:

### Option A — Mount the host ROCm runtime (zero image changes, recommended)

If the host already has ROCm 7.2.x installed (most Strix Halo workstations do),
bind-mount the runtime libraries into the container:

```bash
docker run -d \
  --device=/dev/kfd --device=/dev/dri \
  --group-add video --group-add render \
  --ipc=host \
  -v /opt/rocm/lib:/opt/rocm/lib:ro \
  -e LD_LIBRARY_PATH=/opt/rocm/lib:/app/engine/bin \
  -p 8010:8010 \
  ghcr.io/julianmb/halofpx:latest
```

or with `docker compose`, add to the service:

```yaml
    volumes:
      - /opt/rocm/lib:/opt/rocm/lib:ro
    environment:
      - LD_LIBRARY_PATH=/opt/rocm/lib:/app/engine/bin
```

Verify inside the container: `ldd /app/engine/bin/llama-server | grep 'not found'`
should print nothing.

### Option B — Build a container variant with the ROCm runtime baked in (~1.2 GB larger)

Create a `Dockerfile.rocm` from the base `Dockerfile` with this block inserted
before the engine-binary step (this mirrors the q38rocm#5 fix — see
[julianmb/q38rocm](https://github.com/julianmb/q38rocm) for the full recipe):

```dockerfile
# ROCm 7.2.3 runtime subset (halofpx#4)
RUN curl -fsSL "https://repo.radeon.com/amdgpu-install/7.2.3/ubuntu/noble/amdgpu-install_7.2.3.70203-1_all.deb" -o /tmp/amdgpu-install.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/amdgpu-install.deb \
    && rm -f /tmp/amdgpu-install.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        hip-runtime-amd hipblas rocblas hipblaslt hsa-rocr \
        rocprofiler-register rocsolver roctracer comgr \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
```

```bash
docker build -f Dockerfile.rocm -t halofpx:rocm .
```

The default image intentionally stays lean: Vulkan0 (Mesa RADV) is the fastest
decode backend on Strix Halo and needs none of these libraries. Only add the
ROCm runtime when you specifically want the ROCm0 backend inside the container.
