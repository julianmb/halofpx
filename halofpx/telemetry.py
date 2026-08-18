"""
halofpx.telemetry — Hardware & APU Subsystem Telemetry for AMD Platforms
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any
from halofpx.hardware import get_hardware_profile

def get_system_telemetry() -> Dict[str, Any]:
    hw = get_hardware_profile()
    telemetry = {
        "platform": hw["platform_name"],
        "gpu_arch": hw["arch"],
        "is_apu": hw["is_apu"],
        "vram_gib": hw["vram_gib"],
        "cpu_model": "Unknown AMD Processor",
        "kernel": os.uname().release,
        "ram_total_gib": 0.0,
        "ttm_limit_gib": 0.0,
        "ttm_limit_ratio_pct": 0.0,
        "thp": "unknown",
        "gpu_dpm": "unknown",
        "npu_active": hw["has_npu"]
    }

    # CPU Model
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    telemetry["cpu_model"] = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass

    # RAM & TTM
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
        mem_gb = mem_kb / (1024 * 1024)
        telemetry["ram_total_gib"] = round(mem_gb, 2)
        
        if hw["is_apu"]:
            ttm_file = Path("/sys/module/ttm/parameters/pages_limit")
            if ttm_file.exists():
                try:
                    pages = int(ttm_file.read_text().strip())
                    ttm_gb = pages * 4 / (1024 * 1024)
                    telemetry["ttm_limit_gib"] = round(ttm_gb, 2)
                    telemetry["ttm_limit_ratio_pct"] = round((ttm_gb / mem_gb) * 100, 1)
                except Exception:
                    pass

    # Transparent Hugepages
    thp_file = Path("/sys/kernel/mm/transparent_hugepage/enabled")
    if thp_file.exists():
        try:
            thp_text = thp_file.read_text().strip()
            for opt in ["always", "madvise", "never"]:
                if f"[{opt}]" in thp_text:
                    telemetry["thp"] = opt
                    break
        except Exception:
            pass

    # GPU DPM
    dpm_file = Path("/sys/class/drm/card0/device/power_dpm_force_performance_level")
    if dpm_file.exists():
        try:
            telemetry["gpu_dpm"] = dpm_file.read_text().strip()
        except Exception:
            pass

    return telemetry
