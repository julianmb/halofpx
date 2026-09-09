#!/usr/bin/env bash
# ==============================================================================
# build_engine.sh — Build or Download ROCmFPX Engine for AMD Radeon (gfx1151 / gfx1201)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENGINE_DIR="${SCRIPT_DIR}/../engine"
REPO_URL="https://github.com/charlie12345/ROCmFPX.git"
PINNED_COMMIT="${PINNED_COMMIT:-main}"
RELEASE_TARBALL_URL="https://github.com/julianmb/halofpx/releases/download/v1.0.0/strix-halo-rocmfpx-engine-v1.0.0-linux-x86_64.tar.gz"
EXPECTED_TARBALL_SHA="bbc7845db0c012b97f1c9b8a2733a7083c6f9a749a453866fbe1994151d3364f"

# 1. Architecture Detection
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
    if command -v rocminfo >/dev/null 2>&1; then
        for tok in $(rocminfo 2>/dev/null); do
            if [[ "$tok" =~ ^gfx1[0-9a-f]{3}$ ]]; then
                echo "$tok"
                return
            fi
        done
    fi
    echo "gfx1151"
}

TARGET_ARCH="$(detect_arch)"

download_prebuilt() {
    if [ "$TARGET_ARCH" != "gfx1151" ] && [ "$TARGET_ARCH" != "gfx1150" ]; then
        echo "⚠️  [NOTICE] Pre-compiled binaries in v1.0.0 are packaged for Strix Halo (gfx1151)."
        echo "   For other AMD GPUs (${TARGET_ARCH}), compiling from source is required."
        echo "   Proceeding with source compilation for ${TARGET_ARCH}..."
        return 1
    fi

    echo "================================================================================"
    echo " 📥 Downloading Pre-Compiled ROCmFPX Engine (v1.0.0) for AMD Strix Halo"
    echo " Source: ${RELEASE_TARBALL_URL}"
    echo "================================================================================"
    mkdir -p "${ENGINE_DIR}"
    TAR_PATH="/tmp/strix-halo-engine-v1.0.0.tar.gz"
    
    curl -L "${RELEASE_TARBALL_URL}" -o "${TAR_PATH}" --progress-bar
    
    if command -v sha256sum >/dev/null 2>&1; then
        echo "${EXPECTED_TARBALL_SHA}  ${TAR_PATH}" | sha256sum -c -
        echo "✅ Checksum verified!"
    fi
    
    echo "Extracting binaries into ${ENGINE_DIR}..."
    tar -xzf "${TAR_PATH}" -C /tmp/
    cp -a /tmp/strix-halo-rocmfpx-engine/* "${ENGINE_DIR}/"
    rm -rf /tmp/strix-halo-rocmfpx-engine "${TAR_PATH}"
    
    echo "✅ Pre-built engine ready in: ${ENGINE_DIR}/bin"
    echo "Verifying available hardware acceleration backends..."
    "${ENGINE_DIR}/bin/llama-server" --list-devices 2>/dev/null || true
    echo "Run: source ./scripts/setup_env.sh"
    exit 0
}

# Parse CLI flags
BUILD_MODE="vulkan"
DOWNLOAD_ONLY=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prebuilt|--download)
            DOWNLOAD_ONLY=1
            shift
            ;;
        --rocm|--dual|--hip)
            BUILD_MODE="dual"
            shift
            ;;
        --vulkan|--vulkan-only)
            BUILD_MODE="vulkan"
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --vulkan (default)  Build lightweight standalone Vulkan engine (no ROCm/HIP required)"
            echo "  --rocm, --dual      Build dual ROCm (HIP) + Vulkan engine for high-batch prefill"
            echo "  --prebuilt          Download pre-compiled release tarball"
            echo "  -h, --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Run '$0 --help' for usage."
            exit 1
            ;;
    esac
done

if [ "$DOWNLOAD_ONLY" -eq 1 ]; then
    if download_prebuilt; then
        exit 0
    fi
fi

echo "================================================================================"
echo " ⚙️ ROCmFPX llama.cpp Engine Setup for AMD Platforms"
echo " Build Mode:           ${BUILD_MODE^^} (Primary backend: Vulkan0 Wave64)"
echo " Target Architecture:  ${TARGET_ARCH}"
if [ "$TARGET_ARCH" == "gfx1151" ] || [ "$TARGET_ARCH" == "gfx1150" ]; then
    echo " Platform:             AMD Strix Halo / Ryzen AI Max APU (Unified Memory)"
else
    echo " Platform:             AMD Radeon GPU (${TARGET_ARCH})"
fi
echo "================================================================================"

# Check compiler dependencies
MISSING_TOOLS=0
for tool in cmake git; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "⚠️  Tool '$tool' is not installed."
        MISSING_TOOLS=1
    fi
done

# Check Vulkan shader compiler (glslc)
if ! command -v glslc >/dev/null 2>&1; then
    echo "⚠️  'glslc' (Vulkan shader compiler) not found."
    echo "   To compile with Vulkan, install: sudo apt install glslc libvulkan-dev mesa-vulkan-drivers"
    if [ "$TARGET_ARCH" == "gfx1151" ]; then
        read -p "Would you like to download the pre-compiled Strix Halo binaries instead? [Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            download_prebuilt
        fi
    fi
    MISSING_TOOLS=1
fi

if [ "$BUILD_MODE" == "dual" ]; then
    if ! command -v hipcc >/dev/null 2>&1 && [ ! -d "/opt/rocm" ]; then
        echo "⚠️  ROCm toolchain (hipcc) not found for dual build. Falling back to pure Vulkan build..."
        BUILD_MODE="vulkan"
    fi
fi

if [ "$MISSING_TOOLS" -eq 1 ]; then
    echo "Required build tools are missing. Falling back to pre-compiled release download..."
    download_prebuilt
fi

# Clone or Update ROCmFPX Repository
if [ ! -d "${ENGINE_DIR}/src/.git" ]; then
    echo "Cloning ROCmFPX toolchain into ${ENGINE_DIR}/src..."
    mkdir -p "${ENGINE_DIR}"
    git clone "${REPO_URL}" "${ENGINE_DIR}/src"
fi

cd "${ENGINE_DIR}/src"
echo "Checking out pinned commit: ${PINNED_COMMIT}..."
git fetch origin
git checkout "${PINNED_COMMIT}" || true

PATCH_FILE="${SCRIPT_DIR}/../patches/mtp-prompt-cache-fix.patch"
if [ -f "${PATCH_FILE}" ]; then
    echo "Applying MTP prompt cache checkpoint fix (issue #3)..."
    git apply "${PATCH_FILE}" 2>/dev/null || true
fi

# Configure CMake
if [ "$BUILD_MODE" == "dual" ]; then
    BUILD_DIR="${ENGINE_DIR}/src/build-${TARGET_ARCH}-dual"
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"

    CMAKE_FLAGS=(
        -DGGML_HIP=ON
        -DAMDGPU_TARGETS="${TARGET_ARCH}"
        -DCMAKE_HIP_ARCHITECTURES="${TARGET_ARCH}"
        -DGGML_VULKAN=ON
        -DGGML_VULKAN_CHECK_RESULTS=OFF
        -DGGML_AVX=ON
        -DGGML_AVX2=ON
        -DGGML_AVX512=ON
        -DGGML_F16C=ON
        -DGGML_FMA=ON
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON
        -DLLAMA_BUILD_WEBUI=OFF
        -DCMAKE_BUILD_TYPE=Release
    )
    echo "Configuring CMake with Dual ROCm (HIP) + Vulkan support for ${TARGET_ARCH}..."
else
    BUILD_DIR="${ENGINE_DIR}/src/build-vulkan"
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"

    CMAKE_FLAGS=(
        -DGGML_VULKAN=ON
        -DGGML_HIP=OFF
        -DGGML_VULKAN_CHECK_RESULTS=OFF
        -DGGML_AVX=ON
        -DGGML_AVX2=ON
        -DGGML_AVX512=ON
        -DGGML_F16C=ON
        -DGGML_FMA=ON
        -DCMAKE_POSITION_INDEPENDENT_CODE=ON
        -DLLAMA_BUILD_WEBUI=OFF
        -DCMAKE_BUILD_TYPE=Release
    )
    echo "Configuring CMake with Standalone Vulkan engine (zero ROCm link-time dependencies)..."
fi

cmake .. "${CMAKE_FLAGS[@]}"

JOBS="${JOBS:-$(nproc 2>/dev/null || echo 8)}"
echo "Compiling binaries with ${JOBS} parallel threads..."
cmake --build . --config Release -j "${JOBS}" --target llama-server llama-cli llama-bench llama-quantize

# Link/Install Executables to engine/bin
mkdir -p "${ENGINE_DIR}/bin"
cp -f bin/llama-server bin/llama-cli bin/llama-bench bin/llama-quantize "${ENGINE_DIR}/bin/"

echo "================================================================================"
echo " ✅ Build Complete (${BUILD_MODE^^})!"
echo " Binaries installed to: ${ENGINE_DIR}/bin"
echo " Detected backends on host:"
"${ENGINE_DIR}/bin/llama-server" --list-devices 2>/dev/null || true
echo " Export environment:    source ./scripts/setup_env.sh"
echo "================================================================================"
