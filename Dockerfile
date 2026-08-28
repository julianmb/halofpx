# ==============================================================================
# Dockerfile — HaloFPX Model Server for AMD Strix Halo & Radeon GPUs
# ==============================================================================

FROM ubuntu:24.04

ARG ENGINE_RELEASE=v1.5.2

LABEL maintainer="HaloFPX & Strix Halo Open Source Community"
LABEL description="Unified HaloFPX / ROCmFP4 Model Server for AMD Strix Halo & Radeon GPUs"

ENV DEBIAN_FRONTEND=noninteractive
ENV HIP_VISIBLE_DEVICES=0
ENV ROCM_FLUSH_ACCEPT=1
ENV AMD_VULKAN_ICD=RADV
ENV RADV_PERFTEST="gpl,sam,nggc"
ENV PATH="/app/engine/bin:${PATH}"
ENV LD_LIBRARY_PATH="/app/engine/bin:${LD_LIBRARY_PATH}"
ENV PYTHONPATH="/app:${PYTHONPATH}"

WORKDIR /app

# Install system dependencies & Mesa RADV Vulkan drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    vulkan-tools \
    mesa-vulkan-drivers \
    libvulkan1 \
    libgomp1 \
    python3 \
    python3-pip \
    tar \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install pre-compiled ROCmFPX engine binaries
# The pre-compiled binaries link against the ROCm 7.2.x runtime
# (libhipblas.so.3, librocblas.so.5, libamdhip64.so.7, ...) which this
# lean image intentionally omits — the Vulkan0 backend (fastest decode on
# Strix Halo) needs none of them. For the ROCm0 backend, mount the host
# ROCm libs or bake the runtime subset: docs/DOCKER_GUIDE.md §7 (issue #4).
RUN mkdir -p /app/engine && \
    curl -L "https://github.com/julianmb/q38rocm/releases/download/${ENGINE_RELEASE}/strix-halo-rocmfpx-engine-v1.5.2-linux-x86_64.tar.gz" -o /tmp/engine.tar.gz && \
    tar -xzf /tmp/engine.tar.gz -C /tmp/ && \
    cp -a /tmp/strix-halo-rocmfpx-engine/* /app/engine/ && \
    rm -rf /tmp/strix-halo-rocmfpx-engine /tmp/engine.tar.gz

# Install Python requirements
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy source code
COPY . /app/
RUN chmod +x /app/scripts/*.sh /app/scripts/*.py

EXPOSE 8010

HEALTHCHECK --interval=10s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8010/health || exit 1

ENTRYPOINT ["python3", "-m", "halofpx.cli", "serve", "--host", "0.0.0.0", "--port", "8010"]
