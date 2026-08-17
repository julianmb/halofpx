"""
rocmfpx.telemetry — Hardware & APU Subsystem Telemetry for AMD Strix Halo
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any

def get_system_telemetry() -> Dict[str, Any]:
    telemetry = {
        "platform": "AMD Strix Halo (Ryzen AI Max+ 395)",
        "cpu_model": "Unknown AMD Processor",
        "kernel": os.uname().release,
        "ram_total_gib": 0.0,
        "ttm_limit_gib": 0.0,
        "ttm_limit_ratio_pct": 0.0,
        "thp": "unknown",
        "gpu_dpm": "unknown",
        "npu_active": False
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

    # NPU Subsystem
    npu_node = Path("/dev/accel/accel0")
    if npu_node.exists():
        try:
            lsmod = subprocess.run("lsmod | grep amdxdna", shell=True, capture_output=True, text=True).stdout
            if "amdxdna" in lsmod:
                telemetry["npu_active"] = True
        except Exception:
            pass

    return telemetry
