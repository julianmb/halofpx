"""
halofpx.cli — Unified Command Line Interface for HaloFPX Model Server
"""

import sys
import argparse
import uvicorn
import requests

from halofpx.config import DEFAULT_ROUTER_PORT, DEFAULT_HOST, ROOT_DIR
from halofpx.registry import ModelRegistry
from halofpx.model_manager import ModelManager
from halofpx.engine_manager import EngineManager
from halofpx.telemetry import get_system_telemetry
from halofpx.hardware import get_hardware_profile

def color(text, code): return f"\033[{code}m{text}\033[0m"
def green(text): return color(text, "1;32")
def yellow(text): return color(text, "1;33")
def cyan(text): return color(text, "1;36")
def bold(text): return color(text, "1")
def red(text): return color(text, "1;31")
def dim(text): return color(text, "2")

def format_table(rows, headers):
    cols = len(headers)
    widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            clean_val = str(val).replace("\033[1;32m", "").replace("\033[1;33m", "").replace("\033[1;36m", "").replace("\033[1;31m", "").replace("\033[2m", "").replace("\033[0m", "")
            widths[i] = max(widths[i], len(clean_val))
    
    sep = "+" + "+".join(["-" * (w + 2) for w in widths]) + "+"
    head_str = "| " + " | ".join([f"{headers[i]:<{widths[i]}}" for i in range(cols)]) + " |"
    
    out = [sep, head_str, sep]
    for row in rows:
        row_str = "| "
        for i, val in enumerate(row):
            clean_val = str(val).replace("\033[1;32m", "").replace("\033[1;33m", "").replace("\033[1;36m", "").replace("\033[1;31m", "").replace("\033[2m", "").replace("\033[0m", "")
            pad = widths[i] - len(clean_val)
            row_str += str(val) + (" " * pad) + " | "
        out.append(row_str[:-1])
    out.append(sep)
    return "\n".join(out)

def cmd_serve(args):
    hw = get_hardware_profile()
    print("=" * 80)
    print(bold(" 🚀 Starting HaloFPX Unified Model Server"))
    print(f" Detected Hardware: {cyan(hw['platform_name'])} ({hw['vram_gib']} GiB VRAM)")
    print("=" * 80)
    print(f" Host / Port:      http://{args.host}:{args.port}")
    print(f" OpenAI Endpoint:   http://{args.host}:{args.port}/v1/chat/completions")
    print(f" Management API:    http://{args.host}:{args.port}/api/v1")
    print("=" * 80)

    # If auto-load model requested
    if args.model:
        from halofpx.server import engine_mgr
        print(f"Auto-loading initial model: {args.model}...")
        engine_mgr.load_model(args.model, variant=args.variant)

    uvicorn.run("halofpx.server:app", host=args.host, port=args.port, log_level="info")

def cmd_list(args):
    registry = ModelRegistry()
    models = registry.list_models()
    hw = get_hardware_profile()

    print("\n" + "=" * 95)
    print(bold(f" 📦 HaloFPX Model Zoo — {hw['platform_name']} ({hw['vram_gib']} GiB VRAM)"))
    print("=" * 95)

    table = []
    for m in models:
        model_id = m["model_id"]
        category = m.get("category", "")
        hf_repo = m.get("hf_repo", "")
        variants = m.get("variants_status", {})
        if m.get("vision_capable"):
            vision_status = green("✅ Ready") if m.get("vision_ready") else cyan("☁️ Pull required")
        else:
            vision_status = dim("—")
        
        for vname, vdata in variants.items():
            min_vram = vdata.get("min_vram_gib", 16.0)
            fits_gpu = hw["vram_gib"] >= min_vram
            
            if vdata["downloaded"]:
                status_str = green("✅ Ready") if fits_gpu else yellow(f"⚠️ Ready (Needs {min_vram}G)")
            else:
                status_str = cyan("☁️ Available (HF)") if fits_gpu else dim(f"☁️ Needs {min_vram}G")

            if args.downloaded and not vdata["downloaded"]:
                continue
            table.append([
                model_id,
                vname,
                f"{vdata['bpw']:.2f}",
                f"{vdata['size_gib']:.2f} GiB",
                f"{min_vram:.0f} GiB",
                status_str,
                vision_status,
                hf_repo
            ])

    headers = ["Model ID", "Variant", "BPW", "Size", "Min VRAM", "Status", "Vision", "Hugging Face Repo"]
    print(format_table(table, headers))
    print("\n💡 Pull a model: 'halofpx pull <model_id>' | Load: 'halofpx load <model_id>'\n")

def cmd_pull(args):
    model_mgr = ModelManager()
    res = model_mgr.pull_model(args.model_id, args.variant)
    if res.get("status") == "success":
        print(f"\n{green('✅ Successfully pulled')} {res['model_id']}:{res['variant']} ({res['size_gib']} GiB)")
        print(f"Location: {res['local_path']}\n")
        if res.get("vision_ready"):
            print(f"{green('✅ Vision projector ready')}: {res['mmproj_path']}\n")
    else:
        print(f"\n{red('❌ Pull failed:')} {res.get('message')}\n")

def cmd_load(args):
    url = f"http://{args.host}:{args.port}/api/v1/load"
    payload = {
        "model_id": args.model_id,
        "variant": args.variant,
        "ctx_size": args.ctx,
        "slots": args.slots,
        "draft_n": args.draft_n,
        "draft_p": args.draft_p,
        "strict_mtp": args.strict,
        "reasoning_budget": args.reasoning_budget,
        "reasoning_mode": args.reasoning,
        "device": args.device,
        "cache_ram_mib": args.cache_ram,
        "ctx_checkpoints": args.ctx_checkpoints,
        "cache_reuse": args.cache_reuse,
        "checkpoint_every": args.checkpoint_every,
        "mlock": args.mlock,
        "use_mmap": args.mmap,
        "optimization_mode": args.optimization_mode
    }
    try:
        resp = requests.post(url, json=payload, timeout=60)
        data = resp.json()
        if resp.status_code == 200:
            print(f"\n{green('✅ Model loaded successfully!')}")
            print(f"  • Model:   {data.get('model_id')} ({data.get('variant')})")
            print(f"  • Device:  {data.get('device')}")
            print(f"  • Context: {data.get('context_size')} tokens\n")
        else:
            print(f"\n{red('❌ Load failed:')} {data.get('detail')}\n")
    except Exception as e:
        # Fallback to direct local load if server not running
        print(f"Server not running on port {args.port}. Starting direct local engine...")
        eng = EngineManager()
        res = eng.load_model(
            args.model_id,
            args.variant,
            ctx_size=args.ctx,
            slots=args.slots,
            draft_n=args.draft_n,
            draft_p=args.draft_p,
            strict_mtp=args.strict,
            device=args.device,
            cache_ram_mib=args.cache_ram,
            ctx_checkpoints=args.ctx_checkpoints,
            cache_reuse=args.cache_reuse,
            checkpoint_every=args.checkpoint_every,
            mlock=args.mlock,
            use_mmap=args.mmap,
            optimization_mode=args.optimization_mode
        )
        print(res)

def cmd_unload(args):
    url = f"http://{args.host}:{args.port}/api/v1/unload"
    try:
        resp = requests.post(url, timeout=10)
        print(resp.json().get("message", "Model unloaded."))
    except Exception:
        print("Server not reachable.")

def cmd_status(args):
    telemetry = get_system_telemetry()
    print("\n" + "=" * 80)
    print(bold(" 📊 HaloFPX SERVER & APU HARDWARE STATUS"))
    print("=" * 80)
    print(f" Platform:          {cyan(telemetry['platform'])}")
    print(f" Host CPU:          {telemetry['cpu_model']}")
    print(f" Linux Kernel:      {telemetry['kernel']}")
    print(f" Total RAM / VRAM:  {telemetry['vram_gib']} GiB")
    if telemetry.get("is_apu"):
        print(f" TTM Memory Limit:  {telemetry['ttm_limit_gib']} GiB ({telemetry['ttm_limit_ratio_pct']}% of RAM)")
    print(f" GPU DPM Governor:  {telemetry['gpu_dpm']}")
    print(f" AMD XDNA 2 NPU:    {green('Active (/dev/accel/accel0)') if telemetry['npu_active'] else yellow('Inactive')}")
    print("-" * 80)

    url = f"http://{args.host}:{args.port}/api/v1/status"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            st = resp.json().get("engine", {})
            if st.get("loaded"):
                print(f" Active Model:      {green(st.get('model_id'))} ({st.get('variant')})")
                print(f" Backend Device:    {st.get('device')}")
                print(f" Uptime:            {st.get('uptime_seconds')} seconds")
            else:
                print(f" Active Model:      {yellow('None loaded (Idle)')}")
    except Exception:
        print(f" Server Status:     {yellow('HTTP server is offline')}")
    print("=" * 80 + "\n")

def cmd_doctor(args):
    import subprocess
    doc_script = ROOT_DIR / "scripts" / "strix_doctor.py"
    subprocess.run([sys.executable, str(doc_script)])

def cmd_bench(args):
    import subprocess
    bench_script = ROOT_DIR / "scripts" / "benchmark.py"
    subprocess.run([sys.executable, str(bench_script), "--port", str(args.port)])

def main():
    parser = argparse.ArgumentParser(
        description="halofpx — Unified Model Server & CLI for AMD Strix Halo & Radeon GPUs",
        prog="halofpx"
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommand to execute")

    # serve
    p_serve = subparsers.add_parser("serve", help="Start the unified model server")
    p_serve.add_argument("--port", type=int, default=DEFAULT_ROUTER_PORT, help="Server port")
    p_serve.add_argument("--host", default=DEFAULT_HOST, help="Bind host")
    p_serve.add_argument("-m", "--model", help="Auto-load model on startup")
    p_serve.add_argument("--variant", help="Model quantization variant")

    # list
    p_list = subparsers.add_parser("list", help="List registered models and local cache status")
    p_list.add_argument("--downloaded", action="store_true", help="Only list downloaded models")

    # pull
    p_pull = subparsers.add_parser("pull", help="Download a model from Hugging Face")
    p_pull.add_argument("model_id", help="Registered model identifier")
    p_pull.add_argument("--variant", help="Quantization variant")

    # load
    p_load = subparsers.add_parser("load", help="Load a model into unified memory / VRAM")
    p_load.add_argument("model_id", help="Registered model identifier")
    p_load.add_argument("--variant", help="Quantization variant")
    p_load.add_argument("--ctx", type=int, help="Context window size override")
    p_load.add_argument("--slots", type=int, help="Number of concurrent server slots")
    p_load.add_argument("--draft-n", type=int, help="Max MTP draft tokens")
    p_load.add_argument("--draft-p", type=float, help="Min MTP probability threshold")
    p_load.add_argument("--strict", action="store_true", help="Strict lossless greedy verification")
    p_load.add_argument("--device", choices=["Vulkan0", "ROCm0"], help="Compute backend override")
    p_load.add_argument("--reasoning", default="auto", choices=["auto", "on", "off"], help="Reasoning mode")
    p_load.add_argument("--reasoning-budget", type=int, default=4096, help="Reasoning budget limit")
    p_load.add_argument("--cache-ram", type=int, help="Prompt cache size in MiB (auto by system RAM)")
    p_load.add_argument("--ctx-checkpoints", type=int, help="Context checkpoints per slot (auto by system RAM)")
    p_load.add_argument("--cache-reuse", type=int, default=256, help="Minimum reusable prompt chunk size")
    p_load.add_argument("--checkpoint-every", type=int, default=4096, help="Checkpoint interval in tokens")
    p_load.add_argument("--mlock", action="store_true", help="Pin model pages in RAM (requires memlock permission)")
    mmap_group = p_load.add_mutually_exclusive_group()
    mmap_group.add_argument("--mmap", dest="mmap", action="store_true", help="Memory-map model weights")
    mmap_group.add_argument("--no-mmap", dest="mmap", action="store_false", help="Load weights without mmap")
    p_load.set_defaults(mmap=None)
    p_load.add_argument("--optimization-mode", choices=["auto", "speed", "cache"], default="auto", help="Use MTP speed mode or reusable checkpoint cache mode")
    p_load.add_argument("--port", type=int, default=DEFAULT_ROUTER_PORT, help="Server port")
    p_load.add_argument("--host", default="127.0.0.1", help="Server host")

    # unload
    p_unload = subparsers.add_parser("unload", help="Unload currently active model")
    p_unload.add_argument("--port", type=int, default=DEFAULT_ROUTER_PORT, help="Server port")
    p_unload.add_argument("--host", default="127.0.0.1", help="Server host")

    # status
    p_status = subparsers.add_parser("status", help="Show server and hardware status")
    p_status.add_argument("--port", type=int, default=DEFAULT_ROUTER_PORT, help="Server port")
    p_status.add_argument("--host", default="127.0.0.1", help="Server host")

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Run hardware and environment diagnostic")

    # bench
    p_bench = subparsers.add_parser("bench", help="Run multi-prompt benchmark suite")
    p_bench.add_argument("--port", type=int, default=DEFAULT_ROUTER_PORT, help="Server port")

    args = parser.parse_args()

    if args.subcommand == "serve":
        cmd_serve(args)
    elif args.subcommand == "list":
        cmd_list(args)
    elif args.subcommand == "pull":
        cmd_pull(args)
    elif args.subcommand == "load":
        cmd_load(args)
    elif args.subcommand == "unload":
        cmd_unload(args)
    elif args.subcommand == "status":
        cmd_status(args)
    elif args.subcommand == "doctor":
        cmd_doctor(args)
    elif args.subcommand == "bench":
        cmd_bench(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
