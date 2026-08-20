"""
halofpx.engine_manager — Subprocess & Lifecycle Manager for ROCmFPX llama-server
"""

import os
import sys
import time
import signal
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any
from halofpx.config import get_engine_binary, get_amd_env, DEFAULT_ENGINE_PORT, ROOT_DIR
from halofpx.registry import ModelRegistry
from halofpx.hardware import get_hardware_profile

def get_cache_profile(system_ram_gib: float) -> Dict[str, Any]:
    if system_ram_gib >= 112:
        return {"name": "128GB", "cache_ram_mib": 32768, "ctx_checkpoints": 16}
    if system_ram_gib >= 56:
        return {"name": "64GB", "cache_ram_mib": 16384, "ctx_checkpoints": 8}
    return {"name": "32GB", "cache_ram_mib": 8192, "ctx_checkpoints": 4}

def build_cache_args(
    cache_profile: Dict[str, Any],
    slot_save_path: Path,
    mmap_enabled: bool,
    mlock: bool,
) -> list[str]:
    args = [
        "-ctxcp", str(cache_profile["ctx_checkpoints"]),
        "-cpent", str(cache_profile["checkpoint_every"]),
        "-cram", str(cache_profile["cache_ram_mib"]),
        "--cache-prompt",
        "--cache-reuse", str(cache_profile["cache_reuse"]),
        "--slot-save-path", str(slot_save_path),
        "--cont-batching",
        "--kv-unified",
        "--mmap" if mmap_enabled else "--no-mmap",
    ]
    if mlock:
        args.append("--mlock")
    return args

class EngineManager:
    def __init__(self, registry: Optional[ModelRegistry] = None, engine_port: int = DEFAULT_ENGINE_PORT):
        self.registry = registry or ModelRegistry()
        self.engine_port = engine_port
        self.process: Optional[subprocess.Popen] = None
        self.active_model_id: Optional[str] = None
        self.active_variant: Optional[str] = None
        self.active_device: Optional[str] = None
        self.start_time: Optional[float] = None
        self.active_cache_profile: Optional[Dict[str, Any]] = None

    def auto_detect_device(self, engine_bin: Path) -> str:
        try:
            res = subprocess.run([str(engine_bin), "--list-devices"], capture_output=True, text=True, timeout=5)
            devices_out = res.stdout + res.stderr
            if "Vulkan0" in devices_out:
                return "Vulkan0"
            elif "ROCm0" in devices_out:
                return "ROCm0"
        except Exception:
            pass
        return "Vulkan0"

    def load_model(
        self,
        model_id: str,
        variant: Optional[str] = None,
        ctx_size: Optional[int] = None,
        slots: Optional[int] = None,
        draft_n: Optional[int] = None,
        draft_p: Optional[float] = None,
        strict_mtp: bool = False,
        reasoning_budget: Optional[int] = 4096,
        reasoning_mode: str = "auto",
        device: Optional[str] = None,
        cache_ram_mib: Optional[int] = None,
        ctx_checkpoints: Optional[int] = None,
        cache_reuse: int = 256,
        checkpoint_every: int = 4096,
        mlock: bool = False,
        use_mmap: Optional[bool] = None,
        optimization_mode: str = "auto"
    ) -> Dict[str, Any]:
        # Unload current model if loaded
        if self.is_running():
            print(f"Unloading currently active model '{self.active_model_id}'...")
            self.unload_model()

        model = self.registry.get_model(model_id)
        if not model:
            return {"status": "error", "message": f"Model '{model_id}' not found in registry."}

        var_name = variant or model.get("default_variant")
        model_file = self.registry.get_model_file_path(model_id, var_name)
        if not model_file or not model_file.exists():
            return {
                "status": "error",
                "message": f"Model weights for '{model_id}:{var_name}' not found locally. Run 'halofpx pull {model_id}' first."
            }

        engine_bin = get_engine_binary("llama-server")
        if not engine_bin or not engine_bin.exists():
            return {
                "status": "error",
                "message": "llama-server binary not found. Run './scripts/build_engine.sh --prebuilt'."
            }

        hw = get_hardware_profile()
        v_info = model.get("variants", {}).get(var_name, {})
        min_vram = v_info.get("min_vram_gib", 16.0)
        if hw["vram_gib"] < min_vram:
            print(f"⚠️  [VRAM NOTICE] Model variant '{var_name}' recommends ~{min_vram} GiB VRAM (detected {hw['vram_gib']} GiB).")

        target_device = device or model.get("run_config", {}).get("backend", "auto")
        if target_device == "auto" or not target_device:
            target_device = self.auto_detect_device(engine_bin)

        cfg = model.get("run_config", {})
        ctx = ctx_size or cfg.get("ctx_size", 262144)
        threads = cfg.get("threads", 16)
        ngl = cfg.get("n_gpu_layers", 99)
        kv_k = cfg.get("kv_cache_type_k", "q8_0")
        kv_v = cfg.get("kv_cache_type_v", "turbo4")
        use_mtp = cfg.get("mtp_enabled", True)
        cache_enabled = optimization_mode == "cache" or (optimization_mode == "auto" and not use_mtp)
        if cache_enabled:
            use_mtp = False
            kv_k = "q8_0"
            kv_v = "q8_0"
        slot_count = slots if slots is not None else cfg.get("slots", 1)
        d_n = draft_n if draft_n is not None else cfg.get("draft_n", 4)
        d_p = draft_p if draft_p is not None else cfg.get("draft_p", 0.0)
        cache_profile = get_cache_profile(hw.get("system_ram_gib", 0.0))
        cache_profile["cache_ram_mib"] = cache_ram_mib if cache_ram_mib is not None else cache_profile["cache_ram_mib"]
        cache_profile["ctx_checkpoints"] = ctx_checkpoints if ctx_checkpoints is not None else cache_profile["ctx_checkpoints"]
        cache_profile["cache_reuse"] = cache_reuse
        cache_profile["checkpoint_every"] = checkpoint_every
        slot_save_path = ROOT_DIR / "cache" / "slots" / model_id
        slot_save_path.mkdir(parents=True, exist_ok=True)
        mmap_enabled = use_mmap if use_mmap is not None else cfg.get("mmap", not hw["is_apu"])

        cmd = [
            str(engine_bin),
            "-m", str(model_file),
            "-dev", target_device,
            "-ngl", str(ngl),
            "-fa", "on" if cfg.get("flash_attn", True) else "off",
            "-np", str(slot_count),
            "-c", str(ctx),
            "-b", "2048",
            "-ub", "1024",
            "-t", str(threads),
            "--poll", "100",
            "-ctk", str(kv_k),
            "-ctv", str(kv_v),
            "--presence-penalty", str(cfg.get("presence_penalty", 0.0)),
            "--repeat-penalty", str(cfg.get("repeat_penalty", 1.05)),
            "--port", str(self.engine_port),
            "--host", "127.0.0.1"
        ]

        mmproj_file = self.registry.get_mmproj_file_path(model_id)
        if mmproj_file and mmproj_file.exists():
            cmd.extend(["-mm", str(mmproj_file)])

        if cache_enabled:
            cmd.extend(build_cache_args(cache_profile, slot_save_path, mmap_enabled, mlock))
        else:
            cmd.extend([
                "-ctxcp", "0",
                "-cram", "0",
                "--no-cache-prompt",
                "--no-cache-idle-slots",
                "--mmap" if mmap_enabled else "--no-mmap",
                "--cont-batching",
                "--kv-unified"
            ])
            cache_profile = {"name": "MTP-speed", "enabled": False}

        if use_mtp:
            cmd.extend([
                "--spec-type", "draft-mtp",
                "--spec-draft-n-max", str(d_n),
                "--spec-draft-p-min", str(d_p)
            ])
            if strict_mtp:
                cmd.append("--spec-mtp-strict-qwen")

        if reasoning_mode == "off":
            cmd.extend(["--reasoning", "off"])
        elif reasoning_budget is not None and reasoning_budget >= 0:
            cmd.extend(["--reasoning-budget", str(reasoning_budget)])

        print(f"🚀 Spawning ROCmFPX backend: {model_id} ({var_name}) on {target_device}...")
        env = get_amd_env()
        
        self.process = subprocess.Popen(
            cmd,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid
        )

        # Poll health endpoint
        ready = False
        health_url = f"http://127.0.0.1:{self.engine_port}/health"
        for _ in range(60):
            try:
                with urllib.request.urlopen(health_url, timeout=1) as resp:
                    if resp.status == 200:
                        ready = True
                        break
            except Exception:
                pass
            if self.process.poll() is not None:
                break
            time.sleep(0.5)

        if not ready:
            self.unload_model()
            return {"status": "error", "message": "Backend engine failed to initialize within 30s."}

        self.active_model_id = model_id
        self.active_variant = var_name
        self.active_device = target_device
        self.start_time = time.time()
        self.active_cache_profile = cache_profile

        return {
            "status": "success",
            "model_id": model_id,
            "variant": var_name,
            "device": target_device,
            "context_size": ctx,
            "cache_profile": cache_profile,
            "optimization_mode": "cache" if cache_enabled else "speed",
            "engine_port": self.engine_port
        }

    def unload_model(self) -> Dict[str, Any]:
        if self.process:
            try:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                self.process.wait(timeout=5)
            except Exception:
                try:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                except Exception:
                    pass
        self.process = None
        prev_model = self.active_model_id
        self.active_model_id = None
        self.active_variant = None
        self.active_device = None
        self.start_time = None
        self.active_cache_profile = None
        return {"status": "success", "message": f"Model '{prev_model}' unloaded."}

    def is_running(self) -> bool:
        if self.process and self.process.poll() is None:
            return True
        return False

    def get_status(self) -> Dict[str, Any]:
        running = self.is_running()
        return {
            "loaded": running,
            "model_id": self.active_model_id if running else None,
            "variant": self.active_variant if running else None,
            "device": self.active_device if running else None,
            "uptime_seconds": round(time.time() - self.start_time, 1) if running and self.start_time else 0,
            "cache_profile": self.active_cache_profile if running else None,
            "engine_port": self.engine_port if running else None
        }
