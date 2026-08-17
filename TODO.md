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

- [ ] **Multi-Model Concurrency Routing:** Allow hosting multiple small models (e.g. 0.6B + 30B) concurrently on separate engine ports.
- [ ] **NPU Socket Drafter Bridge:** Implement an IPC / Unix Domain Socket bridge between `/dev/accel/accel0` FastFlowLM and the `llama-server` speculative verification queue.
- [ ] **Embedded Web Chat Interface:** Serve a lightweight HTML/JS chat frontend directly on `GET http://localhost:8010/` without Docker dependencies.
- [ ] **Asynchronous REST Quantization Endpoint:** Implement `POST /api/v1/quantize` to convert HF models to ROCmFP4 via REST API.
- [ ] **Ollama API Emulation:** Add `/api/tags`, `/api/generate`, and `/api/chat` endpoints for drop-in Ollama CLI/app compatibility on port `11434`.
