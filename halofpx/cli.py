"""
halofpx.cli — Unified Command Line Interface for HaloFPX Model Server
"""

import sys
import argparse
import uvicorn
import requests

from halofpx.config import (
    DEFAULT_ROUTER_PORT,
    DEFAULT_ENGINE_PORT,
    DEFAULT_HOST,
    ROOT_DIR,
    MODELS_DIR,
    HF_CACHE_DIRS,
    ENGINE_SEARCH_PATHS,
    get_engine_binary,
    get_lemonade_config_path,
    get_lemonade_status,
    sync_lemonade_extra_models_dir,
)
from halofpx.registry import ModelRegistry
from halofpx.model_manager import ModelManager
from halofpx.engine_manager import EngineManager
from halofpx.telemetry import get_system_telemetry
from halofpx.hardware import get_hardware_profile
from halofpx.chat import start_chat_repl

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

    print("\n" + "=" * 105)
    print(bold(f" 📦 HaloFPX Model Zoo — {hw['platform_name']} ({hw['vram_gib']} GiB VRAM)"))
    print("=" * 105)

    table = []
    for m in models:
        model_id = m["model_id"]
        category = m.get("category", "")
        hf_repo = m.get("hf_repo", "")
        source = m.get("source", "zoo")
        variants = m.get("variants_status", {})

        if getattr(args, "lemonade", False) and source not in ("lemonade_user", "extra_models_dir"):
            continue

        source_label = (
            yellow("lemonade") if source == "lemonade_user"
            else cyan("extra") if source == "extra_models_dir"
            else green("zoo")
        )

        if m.get("vision_capable"):
            vision_status = green("✅ Ready") if m.get("vision_ready") else cyan("☁️ Pull required")
        else:
            vision_status = dim("—")

        for vname, vdata in variants.items():
            min_vram = vdata.get("min_vram_gib", 16.0)
            fits_gpu = hw["vram_gib"] >= min_vram

            if vdata["downloaded"]:
                status_str = green("✅ Ready") if fits_gpu else yellow(f"⚠️ Ready (Needs {min_vram:.0f}G)")
            else:
                status_str = cyan("☁️ Available (HF)") if fits_gpu else dim(f"☁️ Needs {min_vram:.0f}G")

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
                source_label,
                hf_repo or dim("local")
            ])

    headers = ["Model ID", "Variant", "BPW", "Size", "Min VRAM", "Status", "Vision", "Source", "Origin"]
    print(format_table(table, headers))
    print("\n💡 Run & chat: 'halofpx run <model_id>' | Pull: 'halofpx pull <model_id>'\n")

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
            return True
        else:
            print(f"\n{red('❌ Load failed:')} {data.get('detail')}\n")
            return False
    except Exception:
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
        return res.get("status") == "success"

def cmd_unload(args):
    url = f"http://{args.host}:{args.port}/api/v1/unload"
    try:
        resp = requests.post(url, timeout=10)
        print(resp.json().get("message", "Model unloaded."))
    except Exception:
        print("Server not reachable.")

def cmd_run(args):
    loaded = cmd_load(args)
    if not getattr(args, "no_chat", False) and loaded:
        start_chat_repl(
            host=args.host,
            port=args.port,
            model_id=args.model_id,
            variant=args.variant
        )

def cmd_chat(args):
    start_chat_repl(
        host=args.host,
        port=args.port,
        model_id=getattr(args, "model_id", None),
        system_prompt=getattr(args, "system_prompt", None),
        variant=getattr(args, "variant", None)
    )

def cmd_backends(args):
    hw = get_hardware_profile()
    engine_bin = get_engine_binary("llama-server")
    lemonade_status = get_lemonade_status()

    print("\n" + "=" * 80)
    print(bold(" ⚙️  HaloFPX Compute Backends & Engine Runtime"))
    print("=" * 80)
    print(f" Platform Hardware:     {cyan(hw['platform_name'])} ({hw['arch']}, {hw['vram_gib']} GiB VRAM)")
    print(f" Detected APU Mode:     {green('Yes (Strix Halo Unified Memory)') if hw['is_apu'] else 'No (Discrete GPU)'}")
    print("-" * 80)
    print(bold(" Supported Acceleration Backends:"))
    print(f"  • {bold('Vulkan0')} (RADV)        : {green('Active')} — Cooperative Matrix CM1, FP4/FP8/FP16 kernels")
    print(f"  • {bold('ROCm0')} (HIP/gfx1151)   : {green('Supported')} — ROCm 7.2.x runtime closure (libhipblas.so.3)")
    print(f"  • {bold('CPU')} (AVX-512)         : {green('Supported')} — High-throughput Zen 5 CPU threads")
    print("-" * 80)
    print(bold(" Runtime Engine Status:"))
    if engine_bin:
        print(f"  • ROCmFPX llama-server: {green('Found')} ({engine_bin})")
    else:
        print(f"  • ROCmFPX llama-server: {yellow('Not found in engine search paths')}")

    print(bold(" Lemonade Service Integration:"))
    if lemonade_status.get("running"):
        h = lemonade_status.get("health", {})
        print(f"  • Lemonade Server:     {green('Running')} on port {lemonade_status['port']} (v{h.get('version', 'unknown')})")
        print(f"  • Active Model:        {h.get('model_loaded') or 'None'}")
    else:
        print(f"  • Lemonade Server:     {dim('Offline (port 13305)')}")
    print("=" * 80 + "\n")

def cmd_delete(args):
    model_mgr = ModelManager()
    if not getattr(args, "yes", False):
        try:
            confirm = input(f"Are you sure you want to delete model '{args.model_id}'? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                print("Aborted.")
                return
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return

    res = model_mgr.delete_model(args.model_id, args.variant)
    if res.get("status") == "success":
        print(f"\n{green('✅ ' + res['message'])}\n")
    else:
        print(f"\n{red('❌ Delete failed:')} {res.get('message')}\n")

def cmd_config(args):
    action = getattr(args, "action", "show") or "show"
    if action == "sync-lemonade":
        ok = sync_lemonade_extra_models_dir()
        if ok:
            print(f"\n{green('✅ Successfully synchronized Lemonade extra_models_dir')} -> {MODELS_DIR}\n")
        else:
            print(f"\n{red('❌ Failed to synchronize Lemonade config')}\n")
        return

    # Default: show configuration
    lem_cfg = get_lemonade_config_path()
    lem_extra = None
    if lem_cfg and lem_cfg.exists():
        try:
            import json
            with open(lem_cfg, "r") as f:
                lem_extra = json.load(f).get("extra_models_dir")
        except Exception:
            pass

    print("\n" + "=" * 80)
    print(bold(" 🔧 HaloFPX Configuration & Model Paths"))
    print("=" * 80)
    print(f" Root Directory:        {ROOT_DIR}")
    print(f" Models Directory:      {MODELS_DIR}")
    print(f" HF Cache Dirs:         {', '.join(str(p) for p in HF_CACHE_DIRS[:3])}...")
    print(f" Engine Search Paths:   {', '.join(str(p) for p in ENGINE_SEARCH_PATHS[:3])}...")
    print(f" Default Router Port:   {DEFAULT_ROUTER_PORT}")
    print(f" Default Engine Port:   {DEFAULT_ENGINE_PORT}")
    print("-" * 80)
    print(bold(" Lemonade Compatibility:"))
    print(f" Lemonade Config:       {lem_cfg or 'Not found'}")
    print(f" Extra Models Dir:      {lem_extra or '(empty)'}")
    synced = str(lem_extra) == str(MODELS_DIR) if lem_extra else False
    print(f" Status:                {green('Synced') if synced else yellow('Not synced (run halofpx config sync-lemonade)')}")
    print("=" * 80 + "\n")

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

    lem_stat = get_lemonade_status()
    if lem_stat.get("running"):
        h = lem_stat.get("health", {})
        print(f" Lemonade Daemon:   {green('Running')} (port {lem_stat['port']}, v{h.get('version', 'unknown')})")
    else:
        print(f" Lemonade Daemon:   {dim('Offline (port 13305)')}")
    print("=" * 80 + "\n")

def cmd_doctor(args):
    import subprocess
    doc_script = ROOT_DIR / "scripts" / "strix_doctor.py"
    subprocess.run([sys.executable, str(doc_script)])

def cmd_bench(args):
    import subprocess
    bench_script = ROOT_DIR / "scripts" / "benchmark.py"
    subprocess.run([sys.executable, str(bench_script), "--port", str(args.port)])

def build_parser() -> argparse.ArgumentParser:
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

    # run (Lemonade command parity)
    p_run = subparsers.add_parser("run", help="Load a model and launch interactive chat REPL")
    p_run.add_argument("model_id", help="Model identifier to load and run")
    p_run.add_argument("--variant", help="Quantization variant")
    p_run.add_argument("--ctx", type=int, help="Context window size override")
    p_run.add_argument("--slots", type=int, help="Number of concurrent server slots")
    p_run.add_argument("--draft-n", type=int, help="Max MTP draft tokens")
    p_run.add_argument("--draft-p", type=float, help="Min MTP probability threshold")
    p_run.add_argument("--strict", action="store_true", help="Strict lossless greedy verification")
    p_run.add_argument("--device", choices=["Vulkan0", "ROCm0"], help="Compute backend override")
    p_run.add_argument("--reasoning", default="auto", choices=["auto", "on", "off"], help="Reasoning mode")
    p_run.add_argument("--reasoning-budget", type=int, default=4096, help="Reasoning budget limit")
    p_run.add_argument("--cache-ram", type=int, help="Prompt cache size in MiB")
    p_run.add_argument("--ctx-checkpoints", type=int, help="Context checkpoints per slot")
    p_run.add_argument("--cache-reuse", type=int, default=256, help="Minimum reusable prompt chunk size")
    p_run.add_argument("--checkpoint-every", type=int, default=4096, help="Checkpoint interval in tokens")
    p_run.add_argument("--mlock", action="store_true", help="Pin model pages in RAM")
    mmap_group_run = p_run.add_mutually_exclusive_group()
    mmap_group_run.add_argument("--mmap", dest="mmap", action="store_true", help="Memory-map model weights")
    mmap_group_run.add_argument("--no-mmap", dest="mmap", action="store_false", help="Load weights without mmap")
    p_run.set_defaults(mmap=None)
    p_run.add_argument("--optimization-mode", choices=["auto", "speed", "cache"], default="auto", help="Optimization mode")
    p_run.add_argument("--no-chat", action="store_true", help="Load model without starting chat REPL")
    p_run.add_argument("--port", type=int, default=DEFAULT_ROUTER_PORT, help="Server port")
    p_run.add_argument("--host", default="127.0.0.1", help="Server host")

    # chat (Lemonade command parity)
    p_chat = subparsers.add_parser("chat", help="Start interactive terminal chat session")
    p_chat.add_argument("model_id", nargs="?", help="Model identifier to chat with")
    p_chat.add_argument("--variant", help="Quantization variant")
    p_chat.add_argument("--system-prompt", help="System prompt to initialize chat")
    p_chat.add_argument("--port", type=int, default=DEFAULT_ROUTER_PORT, help="Server port")
    p_chat.add_argument("--host", default="127.0.0.1", help="Server host")

    # list
    p_list = subparsers.add_parser("list", help="List registered models and local cache status")
    p_list.add_argument("--downloaded", action="store_true", help="Only list downloaded models")
    p_list.add_argument("--all", action="store_true", help="List all models (default)")
    p_list.add_argument("--lemonade", action="store_true", help="Filter for Lemonade user and discovered models")

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

    # delete / rm (Lemonade command parity)
    p_del = subparsers.add_parser("delete", aliases=["rm"], help="Delete downloaded model files from local cache")
    p_del.add_argument("model_id", help="Model identifier to delete")
    p_del.add_argument("--variant", help="Specific quantization variant to delete")
    p_del.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

    # status
    p_status = subparsers.add_parser("status", help="Show server and hardware status")
    p_status.add_argument("--port", type=int, default=DEFAULT_ROUTER_PORT, help="Server port")
    p_status.add_argument("--host", default="127.0.0.1", help="Server host")

    # backends (Lemonade command parity)
    p_backends = subparsers.add_parser("backends", help="List supported hardware compute backends and engine status")

    # config (Lemonade command parity)
    p_cfg = subparsers.add_parser("config", help="View or modify HaloFPX configuration and Lemonade integration")
    p_cfg.add_argument("action", nargs="?", choices=["show", "sync-lemonade"], default="show", help="Action to execute (default: show)")

    # doctor
    p_doc = subparsers.add_parser("doctor", help="Run hardware and environment diagnostic")

    # bench
    p_bench = subparsers.add_parser("bench", help="Run multi-prompt benchmark suite")
    p_bench.add_argument("--port", type=int, default=DEFAULT_ROUTER_PORT, help="Server port")

    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.subcommand == "serve":
        cmd_serve(args)
    elif args.subcommand == "run":
        cmd_run(args)
    elif args.subcommand == "chat":
        cmd_chat(args)
    elif args.subcommand == "list":
        cmd_list(args)
    elif args.subcommand == "pull":
        cmd_pull(args)
    elif args.subcommand == "load":
        cmd_load(args)
    elif args.subcommand == "unload":
        cmd_unload(args)
    elif args.subcommand in ("delete", "rm"):
        cmd_delete(args)
    elif args.subcommand == "status":
        cmd_status(args)
    elif args.subcommand == "backends":
        cmd_backends(args)
    elif args.subcommand == "config":
        cmd_config(args)
    elif args.subcommand == "doctor":
        cmd_doctor(args)
    elif args.subcommand == "bench":
        cmd_bench(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
