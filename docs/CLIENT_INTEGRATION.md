# Client Integration Guide for ROCmFPX Server

`rocmfpx-server` runs an OpenAI-compatible API endpoint on:
```
http://localhost:8010/v1
```

---

## 1. Open WebUI
1. In Open WebUI, navigate to **Settings** > **Admin Settings** > **Connections**.
2. Set **OpenAI API Base URL** to `http://localhost:8010/v1` (or `http://host.docker.internal:8010/v1` in Docker).
3. Set **API Key** to `sk-no-key`.
4. Click **Verify Connection** and select your model from the chat dropdown.

---

## 2. Continue.dev (VS Code & JetBrains)
Add to `~/.continue/config.json`:

```json
{
  "models": [
    {
      "title": "Qwen 3.8 27B (ROCmFP4)",
      "provider": "openai",
      "model": "qwen38-27b",
      "apiBase": "http://localhost:8010/v1",
      "apiKey": "sk-no-key",
      "contextLength": 32768,
      "roles": ["chat", "edit"]
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen 3 0.6B Autocomplete",
    "provider": "openai",
    "model": "qwen3-0.6b",
    "apiBase": "http://localhost:8010/v1",
    "apiKey": "sk-no-key"
  }
}
```

---

## 3. Cursor IDE
1. Open **Cursor Settings** > **Models**.
2. Set **Override OpenAI Base URL** to `http://localhost:8010/v1`.
3. Add model name: `qwen38-27b`.

---

## 4. Python OpenAI SDK
```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8010/v1", api_key="sk-no-key")

response = client.chat.completions.create(
    model="qwen38-27b",
    messages=[{"role": "user", "content": "Explain Strix Halo architecture."}],
    temperature=0.7
)

print(response.choices[0].message.content)
```
