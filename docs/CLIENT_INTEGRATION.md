# Client & UI Integration Guide for ROCmFPX Server

`halofpx` runs an OpenAI-compatible HTTP API on:
```
http://localhost:8010/v1
```

By default, the server runs **headless/standalone** to maximize available unified RAM for LLM inference (consuming zero extra RAM for web servers). You can optionally connect any desktop client, IDE extension, or browser-based Web UI.

---

## 📑 Supported Frontends & Tools
- [1. Open WebUI (Optional Browser Chat GUI)](#1-open-webui-browser-chat-gui)
- [2. LibreChat](#2-librechat)
- [3. Desktop Web Clients (Chatbox, NextChat, TypingMind)](#3-desktop-clients-chatbox-nextchat-typingmind)
- [4. Continue.dev (VS Code & JetBrains)](#4-continuedev-vs-code--jetbrains)
- [5. Cursor IDE](#5-cursor-ide)
- [6. LiteLLM Proxy](#6-litellm-proxy)
- [7. Python Agent Frameworks (LangChain, LlamaIndex, AutoGen)](#7-python-agent-frameworks)

---

## 1. Open WebUI (Browser Chat GUI)

Open WebUI provides a ChatGPT-like browser interface with multi-model switching, document upload (RAG), and user accounts.

### Option A: Via Docker Compose Profile (Recommended)
Run the server with the optional `webui` profile:
```bash
# Starts both halofpx (port 8010) and Open WebUI (port 3000)
docker compose --profile webui up -d
```
Open **http://localhost:3000** in your browser.

### Option B: Standalone Open WebUI Docker Container
If `halofpx` is already running on your host:
```bash
docker run -d -p 3000:8080 \
  --add-host=host.docker.internal:host-gateway \
  -e OPENAI_API_BASE_URL=http://host.docker.internal:8010/v1 \
  -e OPENAI_API_KEY=sk-no-key \
  -v open-webui-data:/app/backend/data \
  --name open-webui \
  --restart unless-stopped \
  ghcr.io/open-webui/open-webui:main
```

### Option C: Connect an Existing Open WebUI Instance
1. In Open WebUI, navigate to **Settings** > **Admin Settings** > **Connections**.
2. Under **OpenAI API**, set:
   - **API Base URL:** `http://localhost:8010/v1` (or `http://host.docker.internal:8010/v1` if in Docker)
   - **API Key:** `sk-no-key`
3. Click **Verify Connection**.
4. Select `qwen38-27b` or `nemotron-3.5-30b` from the model selector dropdown.

---

## 2. LibreChat

[LibreChat](https://github.com/danny-avila/LibreChat) is an open-source AI chat platform.

Add the following to your `librechat.yaml`:

```yaml
endpoints:
  custom:
    - name: "ROCmFPX Strix Halo"
      apiKey: "sk-no-key"
      baseURL: "http://localhost:8010/v1"
      models:
        default: ["qwen38-27b", "nemotron-3.5-30b", "ornith-35b"]
        fetch: true
      titleConvo: true
      titleModel: "nemotron-3.5-30b"
      modelDisplayLabel: "ROCmFPX"
```

---

## 3. Desktop Clients (Chatbox, NextChat, TypingMind)

For native desktop apps like **Chatbox**, **NextChat**, **Msty**, or **TypingMind**:

1. Open **Settings** > **Model Provider** > **OpenAI API**.
2. **API Host / Base URL:** `http://localhost:8010` (or `http://localhost:8010/v1`)
3. **API Key:** `sk-no-key`
4. **Model Name:** `qwen38-27b` (or any model loaded via `halofpx load <model_id>`).

---

## 4. Continue.dev (VS Code & JetBrains)

[Continue.dev](https://continue.dev) connects inline coding assistants to local models.

Add the following to `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Qwen 3.8 27B (Strix Halo ROCmFP4)",
      "provider": "openai",
      "model": "qwen38-27b",
      "apiBase": "http://localhost:8010/v1",
      "apiKey": "sk-no-key",
      "contextLength": 131072,
      "roles": ["chat", "edit"]
    },
    {
      "title": "Nemotron 3.5 30B (MoE Speed)",
      "provider": "openai",
      "model": "nemotron-3.5-30b",
      "apiBase": "http://localhost:8010/v1",
      "apiKey": "sk-no-key",
      "contextLength": 65536,
      "roles": ["chat", "edit"]
    }
  ]
}
```

---

## 5. Cursor IDE

In Cursor Settings:
1. Open **Cursor Settings** > **Models**.
2. Under **OpenAI API Key**, enter `sk-no-key`.
3. Enable **Override OpenAI Base URL** and set:
   ```
   http://localhost:8010/v1
   ```
4. Add model: `qwen38-27b`.

---

## 6. LiteLLM Proxy (Multi-Model Routing)

Use LiteLLM to route between local Strix Halo models and cloud APIs with unified logging:

```yaml
# litellm_config.yaml
model_list:
  - model_name: local-reasoning
    litellm_params:
      model: openai/qwen38-27b
      api_base: http://localhost:8010/v1
      api_key: sk-no-key
  - model_name: local-fast-moe
    litellm_params:
      model: openai/nemotron-3.5-30b
      api_base: http://localhost:8010/v1
      api_key: sk-no-key
```

Run LiteLLM proxy:
```bash
litellm --config litellm_config.yaml --port 4000
```

---

## 7. Python Agent Frameworks

### 7.1 LangChain
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    base_url="http://localhost:8010/v1",
    api_key="sk-no-key",
    model="qwen38-27b",
    temperature=0.7
)

response = llm.invoke("Write a Python script that calculates matrix multiplication on Vulkan.")
print(response.content)
```

### 7.2 LlamaIndex
```python
from llama_index.llms.openai_like import OpenAILike

llm = OpenAILike(
    model="qwen38-27b",
    api_base="http://localhost:8010/v1",
    api_key="sk-no-key",
    is_chat_model=True
)

response = llm.complete("Explain the difference between Wave32 and Wave64.")
print(response.text)
```

---

## 8. Ollama Clients (Drop-In)

halofpx exposes Ollama's core API surface, so tools built for Ollama work without changes:

```bash
# Point any Ollama client at halofpx
export OLLAMA_HOST=http://localhost:8010

ollama list          # -> GET /api/tags
ollama run ornith-1.5-35b:latest "Say hi"   # -> POST /api/generate
```

Supported endpoints: `GET /api/version`, `GET /api/tags`, `POST /api/chat`, `POST /api/generate` (streaming NDJSON and non-streaming). The requested model must be the active one — load it first with `halofpx load <model_id>`.

---

## 9. DFlash2 Sidecar (Structured Output Acceleration)

For structured-output workloads (JSON, code, tool calls), a community-quantized DFlash2 drafter in ROCmFP4_FAST format is available:

- **[agentionai/Qwen3.8-27B-DFlash2-ROCmFP4-FAST-GGUF](https://huggingface.co/agentionai/Qwen3.8-27B-DFlash2-ROCmFP4-FAST-GGUF)** — 65.6 tok/s structured (4.7× bare), requires [LaurentZuijdwijk fork](https://github.com/LaurentZuijdwijk/llama.cpp).

See the full guide in [q38rocm docs](https://github.com/julianmb/q38rocm/blob/main/docs/DFLASH2_ALTERNATIVE.md).
