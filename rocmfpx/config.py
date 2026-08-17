"""
rocmfpx.config — Global Server & Hardware Configuration for AMD Strix Halo
"""

import os
import shutil
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT_DIR / "registry"
MODELS_FILE = REGISTRY_DIR / "models.json"
PRESETS_FILE = REGISTRY_DIR / "presets.json"
SCRIPTS_DIR = ROOT_DIR / "scripts"

# Model Cache Directories
HF_CACHE_DIRS = [
    Path("/var/lib/lemonade/.cache/huggingface/hub"),
    Path(os.path.expanduser("~/.cache/huggingface/hub")),
    ROOT_DIR / "models",
    Path("/home/user/source/strix-halo-rocmfpx-hub/models")
]

# Engine Search Paths
ENGINE_SEARCH_PATHS = [
    ROOT_DIR / "engine" / "bin",
    Path("/home/user/source/strix-halo-rocmfpx-hub/engine/bin"),
    Path("/home/user/source/ROCmFPX/build-strix-rocmfp4/bin"),
    Path("/usr/local/bin")
]

# Server Ports
DEFAULT_ROUTER_PORT = int(os.environ.get("ROCMFPX_PORT", "8010"))
DEFAULT_ENGINE_PORT = int(os.environ.get("ROCMFPX_ENGINE_PORT", "8800"))
DEFAULT_HOST = os.environ.get("ROCMFPX_HOST", "0.0.0.0")

def get_engine_binary(name="llama-server") -> Path | None:
    system_bin = shutil.which(name)
    if system_bin:
        return Path(system_bin)
    for p in ENGINE_SEARCH_PATHS:
        candidate = p / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    return None

def get_strix_env() -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "HSA_OVERRIDE_GFX_VERSION": env.get("HSA_OVERRIDE_GFX_VERSION", "11.5.1"),
        "GGML_HIP_ENABLE_UNIFIED_MEMORY": env.get("GGML_HIP_ENABLE_UNIFIED_MEMORY", "1"),
        "HIP_VISIBLE_DEVICES": env.get("HIP_VISIBLE_DEVICES", "0"),
        "ROCM_FLUSH_ACCEPT": env.get("ROCM_FLUSH_ACCEPT", "1"),
        "AMD_VULKAN_ICD": env.get("AMD_VULKAN_ICD", "RADV"),
        "VK_ICD_FILENAMES": env.get("VK_ICD_FILENAMES", "/usr/share/vulkan/icd.d/radeon_icd.json"),
        "RADV_PERFTEST": env.get("RADV_PERFTEST", "gpl,sam,nggc")
    })
    engine_bin = get_engine_binary("llama-server")
    if engine_bin:
        bin_dir = str(engine_bin.parent)
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["LD_LIBRARY_PATH"] = f"{bin_dir}:{env.get('LD_LIBRARY_PATH', '')}"
    return env
