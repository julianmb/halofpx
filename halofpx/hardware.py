"""
rocmfpx.hardware — Hardware Architecture & VRAM Detection for AMD Platforms
Dynamically detects AMD APUs (Unified Memory) and discrete Radeon GPUs (VRAM)
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

def get_system_ram_gib() -> float:
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    return round(int(line.split()[1]) / (1024 * 1024), 1)
    except Exception:
        pass
    return 0.0

def detect_amdgpu_arch() -> str:
    # 1. Environment override
    if "CMAKE_HIP_ARCHITECTURES" in os.environ:
        return os.environ["CMAKE_HIP_ARCHITECTURES"]
    if "ROCMFPX_GPU_ARCH" in os.environ:
        return os.environ["ROCMFPX_GPU_ARCH"]

    # 2. Try rocm_agent_enumerator
    try:
        res = subprocess.run(["rocm_agent_enumerator"], capture_output=True, text=True, timeout=3)
        for line in res.stdout.strip().split():
            if line.startswith("gfx") and line != "gfx000":
                return line.strip()
    except Exception:
        pass

    # 3. Try offload-arch
    try:
        res = subprocess.run(["offload-arch"], capture_output=True, text=True, timeout=3)
        for line in res.stdout.strip().split():
            if line.startswith("gfx") and line != "gfx000":
                return line.strip()
    except Exception:
        pass

    # 4. Try rocminfo
    try:
        res = subprocess.run(["rocminfo"], capture_output=True, text=True, timeout=3)
        for line in res.stdout.splitlines():
            if "gfx" in line:
                for token in line.split():
                    if token.startswith("gfx") and len(token) >= 6:
                        return token.strip()
    except Exception:
        pass

    # Default fallback
    return "gfx1151"

def get_gpu_vram_gib() -> float:
    # 1. Check discrete GPU VRAM via sysfs
    for card_dir in Path("/sys/class/drm").glob("card*"):
        vram_file = card_dir / "device" / "mem_info_vram_total"
        if vram_file.exists():
            try:
                bytes_val = int(vram_file.read_text().strip())
                gib = bytes_val / (1024**3)
                if gib > 1.0:
                    return round(gib, 1)
            except Exception:
                pass

    # 2. Check APU shared memory / TTM ceiling
    mem_kb = 0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_kb = int(line.split()[1])
                    break
    except Exception:
        pass

    if mem_kb > 0:
        total_ram_gb = mem_kb / (1024 * 1024)
        ttm_file = Path("/sys/module/ttm/parameters/pages_limit")
        if ttm_file.exists():
            try:
                pages = int(ttm_file.read_text().strip())
                ttm_gb = pages * 4 / (1024 * 1024)
                return round(ttm_gb, 1)
            except Exception:
                pass
        return round(total_ram_gb * 0.5, 1)

    return 16.0

def get_hardware_profile() -> Dict[str, Any]:
    arch = detect_amdgpu_arch()
    is_apu = arch in ["gfx1151", "gfx1150", "gfx1103"]
    
    # Classify architecture family
    if arch in ["gfx1151", "gfx1150"]:
        platform_name = "AMD Strix Halo (Ryzen AI Max APU)"
        family = "strix_halo"
    elif arch in ["gfx1200", "gfx1201"]:
        platform_name = f"AMD Radeon RDNA4 GPU ({arch})"
        family = "rdna4"
    elif arch.startswith("gfx110"):
        platform_name = f"AMD Radeon RDNA3 GPU ({arch})"
        family = "rdna3"
    elif arch.startswith("gfx103"):
        platform_name = f"AMD Radeon RDNA2 GPU ({arch})"
        family = "rdna2"
    else:
        platform_name = f"AMD Radeon GPU ({arch})"
        family = "generic_amdgpu"

    # NPU Detection
    has_npu = False
    if Path("/dev/accel/accel0").exists():
        try:
            lsmod = subprocess.run("lsmod | grep amdxdna", shell=True, capture_output=True, text=True).stdout
            if "amdxdna" in lsmod:
                has_npu = True
        except Exception:
            pass

    return {
        "arch": arch,
        "family": family,
        "platform_name": platform_name,
        "is_apu": is_apu,
        "vram_gib": get_gpu_vram_gib(),
        "system_ram_gib": get_system_ram_gib(),
        "has_npu": has_npu,
        "threads": min(os.cpu_count() or 16, 32)
    }
