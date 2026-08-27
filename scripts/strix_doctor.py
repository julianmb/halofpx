#!/usr/bin/env python3
"""
strix_doctor.py — Comprehensive System, GPU, ROCm, Vulkan & Memory Health Check for AMD Platforms
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

try:
    from rocmfpx.hardware import get_hardware_profile
except ImportError:
    get_hardware_profile = None

def color(text, code): return f"\033[{code}m{text}\033[0m"
def green(text): return color(text, "1;32")
def yellow(text): return color(text, "1;33")
def red(text): return color(text, "1;31")
def cyan(text): return color(text, "1;36")
def bold(text): return color(text, "1")

def run_cmd(cmd):
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=5)
        return res.stdout.strip()
    except Exception:
        return ""

def check_env_var(name, expected=None):
    val = os.environ.get(name)
    if not val:
        print(f"  [{red('FAIL')}] {name:<32} Not set!")
        return False
    if expected and val != expected:
        print(f"  [{yellow('WARN')}] {name:<32} = {val} (recommended: {expected})")
        return True
    print(f"  [{green('PASS')}] {name:<32} = {val}")
    return True

def main():
    hw = get_hardware_profile() if get_hardware_profile else {
        "arch": "gfx1151",
        "family": "strix_halo",
        "platform_name": "AMD Strix Halo",
        "is_apu": True,
        "vram_gib": 120.0,
        "has_npu": True
    }

    print("\n" + "=" * 76)
    print(bold(f" 🩺 AMD GPU & SYSTEM HEALTH DIAGNOSTIC — {hw['platform_name']}"))
    print("=" * 76)

    # 1. System & APU Hardware
    print(f"\n{cyan('1. Host CPU & GPU Hardware Architecture')}")
    cpu_info = run_cmd("lscpu | grep 'Model name:' | sed 's/Model name:[ \t]*//'")
    print(f"  - CPU Model:          {cpu_info or 'Unknown AMD Processor'}")
    kernel_ver = run_cmd("uname -r")
    print(f"  - Linux Kernel:       {kernel_ver}")
    print(f"  - Detected GPU Arch:  {hw['arch']} ({hw['platform_name']})")
    print(f"  - Available VRAM/UMA: {hw['vram_gib']} GiB")

    # 2. Memory & TTM / GTT
    print(f"\n{cyan('2. Unified Memory & TTM / GTT Subsystem')}")
    mem_total_kb = 0
    try:
        with open("/proc/meminfo", "r") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    mem_total_kb = int(line.split()[1])
                    break
    except Exception:
        pass
    mem_total_gb = mem_total_kb / 1024 / 1024
    print(f"  - Total Visible RAM:  {mem_total_gb:.2f} GiB")

    if hw["is_apu"]:
        ttm_path = Path("/sys/module/ttm/parameters/pages_limit")
        if ttm_path.exists():
            try:
                pages = int(ttm_path.read_text().strip())
                ttm_gb = pages * 4 / 1024 / 1024
                ratio = (ttm_gb / mem_total_gb) * 100 if mem_total_gb > 0 else 0
                if ratio >= 75:
                    print(f"  - [{green('PASS')}] TTM/GTT Limit:      {ttm_gb:.2f} GiB ({ratio:.1f}% of RAM)")
                else:
                    print(f"  - [{yellow('WARN')}] TTM/GTT Limit:      {ttm_gb:.2f} GiB ({ratio:.1f}% of RAM) — Consider setting >= 75%")
            except Exception:
                pass
    else:
        print(f"  - [{green('PASS')}] Discrete GPU VRAM:   {hw['vram_gib']} GiB dedicated VRAM")

    # 3. Transparent Hugepages (THP)
    thp_path = Path("/sys/kernel/mm/transparent_hugepage/enabled")
    if thp_path.exists():
        thp_val = thp_path.read_text().strip()
        if "[always]" in thp_val:
            print(f"  - [{green('PASS')}] Transparent Hugepages: always")
        elif "[madvise]" in thp_val:
            print(f"  - [{green('PASS')}] Transparent Hugepages: madvise")
        else:
            print(f"  - [{yellow('WARN')}] Transparent Hugepages: {thp_val}")

    # 4. GPU Power & DPM Status
    print(f"\n{cyan('3. GPU Clock & DPM Power Governor')}")
    dpm_path = Path("/sys/class/drm/card0/device/power_dpm_force_performance_level")
    if dpm_path.exists():
        try:
            dpm_val = dpm_path.read_text().strip()
            if dpm_val == "high":
                print(f"  - [{green('PASS')}] GPU Performance Level: {dpm_val} (Clock locked high)")
            else:
                print(f"  - [{yellow('INFO')}] GPU Performance Level: {dpm_val} (run ./scripts/apply_hardware_tweaks.sh to lock 'high')")
        except Exception:
            pass
    else:
        print(f"  - [{yellow('INFO')}] GPU DPM path not directly accessible in current permissions")

    # 5. ROCm & HIP Recognition
    print(f"\n{cyan('4. ROCm & HIP GPU Backend')}")
    rocminfo_out = run_cmd("rocminfo 2>/dev/null")
    if hw["arch"] in rocminfo_out:
        print(f"  - [{green('PASS')}] ROCm GPU Target:     {hw['arch']} detected via rocminfo")
    else:
        print(f"  - [{yellow('INFO')}] ROCm Target:         {hw['arch']}")

    # 6. Vulkan / RADV Driver
    print(f"\n{cyan('5. Vulkan & RADV Cooperative Matrices')}")
    vulkan_out = run_cmd("vulkaninfo 2>/dev/null")
    if "RADV" in vulkan_out or "STRIX" in vulkan_out or "Radeon" in vulkan_out:
        print(f"  - [{green('PASS')}] Vulkan Driver:        Mesa RADV")
    else:
        print(f"  - [{yellow('WARN')}] Vulkan Driver:        RADV check returned generic status")

    # 7. Environment Variables Check
    print(f"\n{cyan('6. Runtime Environment Variables')}")
    if hw["is_apu"]:
        check_env_var("HSA_OVERRIDE_GFX_VERSION", "11.5.1")
        check_env_var("GGML_HIP_ENABLE_UNIFIED_MEMORY", "1")
    check_env_var("ROCM_FLUSH_ACCEPT", "1")
    check_env_var("RADV_PERFTEST", "gpl,sam,nggc")
    check_env_var("HIP_VISIBLE_DEVICES", "0")

    # 8. Binaries Check
    print(f"\n{cyan('7. ROCmFPX Engine Binaries')}")
    required_bins = ["llama-server", "llama-cli", "llama-quantize", "llama-bench"]
    for b in required_bins:
        bin_path = shutil.which(b) or (ROOT_DIR / "engine" / "bin" / b)
        if bin_path and Path(bin_path).exists() and os.access(bin_path, os.X_OK):
            print(f"  - [{green('PASS')}] {b:<20} Ready ({bin_path})")
        else:
            print(f"  - [{yellow('WARN')}] {b:<20} Missing (run ./scripts/build_engine.sh)")

    print("\n" + "=" * 76)
    print(bold(" 💡 RECOMMENDATIONS:"))
    print("  1. Load optimal environment:   source ./scripts/setup_env.sh")
    print("  2. Apply hardware tweaks:      ./scripts/apply_hardware_tweaks.sh")
    print("  3. List models for your GPU:   python3 -m rocmfpx.cli list")
    print("=" * 76 + "\n")

if __name__ == "__main__":
    main()
