# AGENTS.md — halofpx

## What this repo is
Public unified model server & zoo for AMD Strix Halo:
github.com/julianmb/halofpx. Runs Ornith/Qwen/Nemotron/DeepSeek ROCmFP4
quants behind one OpenAI-compatible endpoint (port 8010).

**Checkout note:** this repo lives INSIDE the workshop
(`~/source/strix-halo-rocmfpx-hub`) as a git submodule. After committing and
pushing here, bump the pointer in the parent repo.

## Verify before pushing
```bash
python3 -m unittest discover -s tests -p "test_*.py"   # 12 tests, must pass
python3 -m py_compile halofpx/*.py scripts/*.py
python3 -m json.tool registry/models.json > /dev/null
```

## Architecture map
- `halofpx/server.py` — FastAPI router + OpenAI proxy (CORS, auth, async)
- `halofpx/engine_manager.py` — llama-server subprocess lifecycle, flag builder
- `halofpx/model_manager.py` — HF pull + SHA256 verify (weights AND mmproj)
- `halofpx/registry.py` — zoo catalog, local-file resolution, vision readiness
- `halofpx/config.py` — ports/paths/env; `get_amd_env()` sets gfx1151 vars
- `registry/models.json` — source of truth for the model zoo

## Conventions & gotchas
1. **Engine flags:** the ROCmFPX fork accepts SINGLE-dash only for
   `-ctxcp -cpent -cram`. Double-dash forms fail at startup. Everything else
   is normal long-form (`--cache-prompt`, `-dev`, ...).
2. **Blocking calls:** never call `engine_mgr.load_model` /
   `model_mgr.pull_model` directly in async endpoints — wrap in
   `asyncio.to_thread`.
3. **Version string:** single source in `halofpx/__init__.py::__version__`;
   do not hardcode elsewhere.
4. **Host default:** `DEFAULT_HOST=127.0.0.1`; only the Dockerfile binds
   0.0.0.0 explicitly.
5. **Vision/multimodal:** mmproj is a top-level registry asset
   (`"mmproj": {...}` with hf_repo/sha256). `vision_ready` is reported
   separately from `is_ready`. Pull downloads + checksum-verifies it.
6. **MTP per model:** MTP is a measured net loss on hybrid-attention MoE
   (ornith-1.5-35b) — its run_config ships `mtp_enabled: false`. Don't
   "fix" that without benchmark evidence.
7. **Machine paths:** config search paths reference
   `~/source/strix-halo-rocmfpx-hub` by design (workshop layout), overridable
   via `HALOFPX_HF_CACHE_DIRS` / `HALOFPX_ENGINE_SEARCH_PATHS`.
8. Commit style: conventional commits (`feat:`, `fix:`, `docs:`,
   `refactor:`); push straight to `main`.

## Benchmarks & claims
Any performance number published in README/docs must come from a measured
run recorded in `docs/BENCHMARKS.md`. No projected numbers without a
"(Projected)" label.

## Quant provenance (mandatory)
Every variant in `registry/models.json` carries a `source` field recording
what it was built from (e.g. "upstream Q8_0 --allow-requantize"). Never add
or publish a quant without it — the Qwen3.8 FAST quant shipped with unknown
provenance and we could not reproduce or audit it. Requantize only from
Q8_0/BF16-class sources; never from k-quants (double-quantization).
