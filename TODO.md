# ROCmFPX Server — Backlog & Overnight Tasks

## 🌙 Overnight Tasks

### 1. Upload Laguna S 2.1 ROCmFP4 (61.20 GiB) to Hugging Face
The repository `julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4` is already created with the Model Card and `.gitattributes`. Run this command overnight to upload the 61.20 GiB weights:

```bash
# Run in background (e.g. via tmux or nohup)
hf upload julianmb/Laguna-S-2.1-ROCmFP4-StrixKVSpine-v4 \
  /home/user/source/laguna-s21/models/laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf \
  laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf \
  --commit-message "weights: upload Laguna S 2.1 ROCmFP4 StrixKVSpine v4 GGUF (61.20 GiB)"
```

**Post-Upload Action:** Once uploaded, delete the local file to free 61.2 GiB:
```bash
rm -f /home/user/source/laguna-s21/models/laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf \
      /home/user/source/laguna-s21/hf-pub/laguna-s-2.1-ROCmFP4-StrixKVSpine-v4.gguf
```

---

## 📋 General Roadmap & Backlog

### Ops & Packaging
- [ ] **PyPI Package Release:** Build and publish `rocmfpx-server` to PyPI for standard `pip install rocmfpx-server`.
- [ ] **systemd Unit (`rocmfpx-server.service`):** Provide a drop-in systemd service unit for headless mini-PC and background server boots.
- [ ] **Pre-Built RDNA Binary Releases:** Create validated GitHub release assets for discrete AMD GPUs once tested on physical hardware.

### Server Core & Robustness
- [ ] **Background Model Pulling:** Convert `POST /api/v1/pull` into an asynchronous background task with a progress polling endpoint.
- [ ] **Engine File Logging:** Stream backend `llama-server` stdout/stderr to a dedicated rotating `server.log` file instead of `/dev/null` for easier debugging.
- [ ] **Engine Load Lock:** Implement an asyncio mutex around `POST /api/v1/load` to prevent race conditions during rapid model switches.
- [ ] **Shared HTTPX Connection Pool:** Reuse a persistent `httpx.AsyncClient` across requests with configurable connection pool sizes.
- [ ] **Orphan Subprocess Cleanup:** Scan for stale `llama-server` processes and pidfiles during server startup.

### Community & Extensions
- [ ] **NPU Socket Drafter Bridge:** Implement an IPC / Unix Domain Socket bridge between `/dev/accel/accel0` FastFlowLM and the `llama-server` speculative verification queue.
- [ ] **Embedded Web Chat Interface:** Serve a lightweight HTML/JS chat frontend directly on `GET http://localhost:8010/` without Docker dependencies.
- [ ] **Asynchronous REST Quantization Endpoint:** Implement `POST /api/v1/quantize` to convert HF models to ROCmFP4 via REST API.
- [ ] **Ollama API Emulation:** Add `/api/tags`, `/api/generate`, and `/api/chat` endpoints for drop-in Ollama CLI/app compatibility on port `11434`.
