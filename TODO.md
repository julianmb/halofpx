# ROCmFPX Server — Backlog & Overnight Tasks

## 🌙 Overnight Tasks

### 1. Upload Laguna S 2.1 ROCmFP4 (61.20 GiB) to Hugging Face
The repository `julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4` is already created with the Model Card and `.gitattributes`. Run this command overnight to upload the 61.20 GiB weights:

```bash
# Run in background (e.g. via tmux or nohup)
hf upload julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4 \
  /home/user/source/halofpx-research/laguna-s21/models/laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf \
  laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf \
  --commit-message "weights: upload Laguna S 2.1 ROCmFP4 StrixKVSpine v4 GGUF (61.20 GiB)"
```

**Post-Upload Action:** Once uploaded, delete the local file to free 61.2 GiB:
```bash
rm -f /home/user/source/halofpx-research/laguna-s21/models/laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf \
      /home/user/source/halofpx-research/laguna-s21/hf-pub/laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf
```

---

## 📋 General Roadmap & Backlog

### Ops & Packaging
- [ ] **PyPI Package Release:** Build and publish `halofpx` to PyPI for standard `pip install halofpx`.
- [ ] **systemd Unit (`halofpx.service`):** Provide a drop-in systemd service unit for headless mini-PC and background server boots.
- [ ] **Pre-Built RDNA Binary Releases:** Create validated GitHub release assets for discrete AMD GPUs once tested on physical hardware.

### Server Core & Robustness
- [ ] **Background Model Pulling:** Convert `POST /api/v1/pull` into an asynchronous background task with a progress polling endpoint.
- [ ] **Engine File Logging:** Stream backend `llama-server` stdout/stderr to a dedicated rotating `server.log` file instead of `/dev/null` for easier debugging.
- [ ] **Engine Load Lock:** Implement an asyncio mutex around `POST /api/v1/load` to prevent race conditions during rapid model switches.
- [ ] **Shared HTTPX Connection Pool:** Reuse a persistent `httpx.AsyncClient` across requests with configurable connection pool sizes.
- [ ] **Orphan Subprocess Cleanup:** Scan for stale `llama-server` processes and pidfiles during server startup.

### Community & Extensions
- [ ] **Embedded Web Chat Interface:** Serve a lightweight HTML/JS chat frontend directly on `GET http://localhost:8010/` without Docker dependencies.
- [ ] **Asynchronous REST Quantization Endpoint:** Implement `POST /api/v1/quantize` to convert HF models to ROCmFP4 via REST API.
- [ ] **Ollama API Emulation:** Add `/api/tags`, `/api/generate`, and `/api/chat` endpoints for drop-in Ollama CLI/app compatibility on port `11434`.

## 🔮 Pending: GLM-5.3-Flash (glm5next) integration

Bring-up already done on strix halo (2026-08-28): project lives at
`~/source/glm5nextrocm` — unsloth 93GB `UD-IQ1_S` runs coherent at 9.31 tok/s
raw decode (vulkan), server + `reasoning_effort` QA'd. receipts in
`glm5nextrocm/results/`, tracking doc `glm5nextrocm/docs/PR27754-tracking.md`.

**Blocker:** the canonical engine (`build-strix-rocmfp4`) cannot load the
`glm5next` arch yet, and the halofpx server is a single-engine hot-swap — so a
registry entry today would fail to load. unsloth's branch is a separate
worktree (`~/source/ROCmFPX-glm5next`) with no ROCmFP4 kernels.

**Trigger to integrate:** the canonical engine can load `glm5next` — either
upstream [PR #27754](https://github.com/ggml-org/llama.cpp/pull/27754) merges
and ROCmFPX rebases onto it, or the arch is hand-ported (days-scale, scoped in
`glm5nextrocm/HANDOVER.md`).

**Then (same 3-step pattern as qwen38-flash-next):**
1. registry entry in `registry/models.json` — variants + sha256 + measured numbers
2. hub `config/models.json` entry
3. preset json (ctx 8192+ bounded, `-fa off` required for MLA correctness)
