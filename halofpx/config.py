"""
halofpx.config — Global Server & Hardware Configuration for AMD Strix Halo & Radeon Platforms
"""

import os
import shutil
from pathlib import Path
from halofpx.hardware import get_hardware_profile

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
REGISTRY_DIR = ROOT_DIR / "registry"
MODELS_FILE = REGISTRY_DIR / "models.json"
PRESETS_FILE = REGISTRY_DIR / "presets.json"
SCRIPTS_DIR = ROOT_DIR / "scripts"

# Models Storage Directory: defaults to ROOT_DIR / "models" unless specified
# by the user via the HALOFPX_MODELS_DIR environment variable.
MODELS_DIR = Path(os.environ.get("HALOFPX_MODELS_DIR", ROOT_DIR / "models")).expanduser().resolve()


def get_lemonade_cache_dirs() -> list[Path]:
    """Discover Lemonade inference engine and Hugging Face cache directories for compatibility."""
    dirs: list[Path] = []
    # Environment overrides
    for env_var in ("LEMONADE_CACHE_DIR", "LEMONADE_MODELS_DIR"):
        raw = os.environ.get(env_var)
        if raw:
            p = Path(raw).expanduser().resolve()
            if p not in dirs:
                dirs.append(p)

    # Standard system & user locations
    candidates = [
        Path("/var/lib/lemonade/.cache/huggingface/hub"),
        Path("/var/lib/lemonade/.cache"),
        Path(os.path.expanduser("~/.cache/lemonade")),
        Path(os.path.expanduser("~/.cache/lemonade/models")),
    ]
    for c in candidates:
        if c.exists() and c not in dirs:
            dirs.append(c)

    # Optional inspection of Lemonade config
    lemonade_cfg = Path("/var/lib/lemonade/config.json")
    if lemonade_cfg.exists():
        try:
            import json
            with open(lemonade_cfg, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            extra = cfg.get("extra_models_dir")
            if extra:
                p = Path(extra).expanduser().resolve()
                if p.exists() and p not in dirs:
                    dirs.append(p)
        except Exception:
            pass

    return dirs


# Model Cache Directories
def _parse_dirs_env(env_var: str, defaults: list) -> list:
    raw = os.environ.get(env_var)
    if raw:
        return [Path(p) for p in raw.split(os.pathsep) if p]
    return defaults


_default_cache_dirs = [
    MODELS_DIR,
    ROOT_DIR / "models",
    Path.home() / "source" / "halofpx-research" / "models",
    Path(os.path.expanduser("~/.cache/huggingface/hub")),
]
for _ld in get_lemonade_cache_dirs():
    if _ld not in _default_cache_dirs:
        _default_cache_dirs.append(_ld)

HF_CACHE_DIRS = _parse_dirs_env("HALOFPX_HF_CACHE_DIRS", _default_cache_dirs)


# Engine Search Paths
ENGINE_SEARCH_PATHS = _parse_dirs_env("HALOFPX_ENGINE_SEARCH_PATHS", [
    ROOT_DIR / "engine" / "bin",
    Path.home() / "source" / "halofpx-research" / "engine" / "bin",
    Path.home() / "source" / "ROCmFPX" / "build-strix-rocmfp4" / "bin",
    Path.home() / "source" / "ROCmFPX" / "build-rdna4" / "bin",
    Path("/usr/local/bin")
])

# Server Ports & Security
DEFAULT_ROUTER_PORT = int(os.environ.get("HALOFPX_PORT", os.environ.get("ROCMFPX_PORT", "8010")))
DEFAULT_ENGINE_PORT = int(os.environ.get("HALOFPX_ENGINE_PORT", os.environ.get("ROCMFPX_ENGINE_PORT", "8800")))
# Default to loopback only; the Dockerfile/compose passes --host 0.0.0.0 explicitly when exposed.
DEFAULT_HOST = os.environ.get("HALOFPX_HOST", os.environ.get("ROCMFPX_HOST", "127.0.0.1"))
HALOFPX_API_KEY = os.environ.get("HALOFPX_API_KEY", os.environ.get("ROCMFPX_API_KEY", "")).strip()

def get_engine_binary(name="llama-server") -> Path | None:
    system_bin = shutil.which(name)
    if system_bin:
        return Path(system_bin)
    for p in ENGINE_SEARCH_PATHS:
        candidate = p / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    return None

def find_vulkan_icd() -> str:
    if "VK_ICD_FILENAMES" in os.environ and os.path.exists(os.environ["VK_ICD_FILENAMES"]):
        return os.environ["VK_ICD_FILENAMES"]
    possible_paths = [
        "/usr/share/vulkan/icd.d/radeon_icd.x86_64.json",
        "/usr/share/vulkan/icd.d/radeon_icd.json",
        "/usr/share/vulkan/icd.d/radeon_icd.i686.json",
        "/etc/vulkan/icd.d/radeon_icd.json",
        "/etc/vulkan/icd.d/radeon_icd.x86_64.json"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            return p
    return "/usr/share/vulkan/icd.d/radeon_icd.json"

def get_amd_env() -> dict[str, str]:
    hw = get_hardware_profile()
    env = os.environ.copy()
    
    # Generic AMD GPU Vulkan & ROCm configuration
    env.update({
        "HIP_VISIBLE_DEVICES": env.get("HIP_VISIBLE_DEVICES", "0"),
        "ROCM_FLUSH_ACCEPT": env.get("ROCM_FLUSH_ACCEPT", "1"),
        "AMD_VULKAN_ICD": env.get("AMD_VULKAN_ICD", "RADV"),
        "VK_ICD_FILENAMES": find_vulkan_icd(),
        "RADV_PERFTEST": env.get("RADV_PERFTEST", "gpl,sam,nggc")
    })

    if os.path.exists("/lib/x86_64-linux-gnu/libdrm_amdgpu.so.1"):
        cur_preload = env.get("LD_PRELOAD", "")
        if "/lib/x86_64-linux-gnu/libdrm_amdgpu.so.1" not in cur_preload:
            env["LD_PRELOAD"] = f"/lib/x86_64-linux-gnu/libdrm_amdgpu.so.1:{cur_preload}".strip(":")

    # APU / Strix Halo specific environment variables (DO NOT set on RDNA4 dGPUs)
    if hw["is_apu"] and hw["arch"] in ["gfx1151", "gfx1150"]:
        env["HSA_OVERRIDE_GFX_VERSION"] = env.get("HSA_OVERRIDE_GFX_VERSION", "11.5.1")
        env["GGML_HIP_ENABLE_UNIFIED_MEMORY"] = env.get("GGML_HIP_ENABLE_UNIFIED_MEMORY", "1")

    engine_bin = get_engine_binary("llama-server")
    if engine_bin:
        bin_dir = str(engine_bin.parent)
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["LD_LIBRARY_PATH"] = f"{bin_dir}:{env.get('LD_LIBRARY_PATH', '')}"
    return env

# Alias for backwards compatibility
get_strix_env = get_amd_env
