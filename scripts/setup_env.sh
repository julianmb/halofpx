#!/usr/bin/env bash
# ==============================================================================
# setup_env.sh — AMD Platform Runtime Environment Setup (Strix Halo & RDNA4)
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Detect GPU Architecture
detect_arch() {
    if [ -n "${CMAKE_HIP_ARCHITECTURES:-}" ]; then
        echo "$CMAKE_HIP_ARCHITECTURES"
        return
    fi
    if command -v rocm_agent_enumerator >/dev/null 2>&1; then
        for a in $(rocm_agent_enumerator 2>/dev/null); do
            if [[ "$a" =~ ^gfx[0-9a-f]+$ ]] && [ "$a" != "gfx000" ]; then
                echo "$a"
                return
            fi
        done
    fi
    if command -v offload-arch >/dev/null 2>&1; then
        for a in $(offload-arch 2>/dev/null); do
            if [[ "$a" =~ ^gfx[0-9a-f]+$ ]] && [ "$a" != "gfx000" ]; then
                echo "$a"
                return
            fi
        done
    fi
    echo "gfx1151"
}

TARGET_ARCH="$(detect_arch)"

# 2. Generic AMD GPU Settings
export HIP_VISIBLE_DEVICES="${HIP_VISIBLE_DEVICES:-0}"
export ROCM_FLUSH_ACCEPT=1
export AMD_VULKAN_ICD=RADV
export VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.json
export RADV_PERFTEST="gpl,sam,nggc"

# 3. APU Specific Overrides (Strix Halo gfx1151 only)
if [ "$TARGET_ARCH" == "gfx1151" ] || [ "$TARGET_ARCH" == "gfx1150" ]; then
    export HSA_OVERRIDE_GFX_VERSION=11.5.1
    export GGML_HIP_ENABLE_UNIFIED_MEMORY=1
fi

# 4. Engine Binary Resolution
POSSIBLE_BIN_DIRS=(
    "${ROCMFPX_BIN_DIR:-}"
    "${SCRIPT_DIR}/../engine/bin"
    "${SCRIPT_DIR}/engine/bin"
    "/home/user/source/strix-halo-rocmfpx-hub/engine/bin"
    "/usr/local/bin"
)

for bdir in "${POSSIBLE_BIN_DIRS[@]}"; do
    if [ -n "$bdir" ] && [ -x "${bdir}/llama-server" ]; then
        export PATH="${bdir}:${PATH}"
        export LD_LIBRARY_PATH="${bdir}:${LD_LIBRARY_PATH:-}"
        break
    fi
done

echo "✅ AMD GPU ROCmFPX & Vulkan RADV environment successfully configured!"
echo "   • Detected Target:    ${TARGET_ARCH}"
if [ "$TARGET_ARCH" == "gfx1151" ]; then
    echo "   • Platform:           AMD Strix Halo (128 GB/64 GB Unified Memory)"
elif [ "$TARGET_ARCH" == "gfx1201" ] || [ "$TARGET_ARCH" == "gfx1200" ]; then
    echo "   • Platform:           AMD Radeon RX 9070 / 9070 XT (RDNA4 dGPU)"
fi
echo "   • Vulkan Driver:      Mesa RADV (Wave64 KHR_coopmat)"
