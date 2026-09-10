"""
halofpx.chat — Interactive Terminal Chat REPL for HaloFPX & Lemonade Compatibility
"""

import sys
import json
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Any

try:
    import readline  # Enable arrow keys, line editing, and history in terminal
except ImportError:
    pass


def _http_get(url: str, timeout: float = 3.0) -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "halofpx-chat"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
    return None


def _http_post_json(url: str, data: Dict[str, Any], timeout: float = 60.0) -> Optional[Dict[str, Any]]:
    try:
        body = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "halofpx-chat"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
            return {"status": "error", "message": err_body}
        except Exception:
            return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def start_chat_repl(
    host: str = "127.0.0.1",
    port: int = 8010,
    model_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
    variant: Optional[str] = None
):
    """Start an interactive chat session with the HaloFPX model server."""
    base_url = f"http://{host}:{port}"
    health = _http_get(f"{base_url}/health") or _http_get(f"{base_url}/api/v1/health")

    if not health:
        print(f"\033[1;31mError: HaloFPX server is not reachable at {base_url}\033[0m")
        print(f"Start the server first with:\n  \033[1;34mhalofpx serve\033[0m\n")
        return 1

    active_model = health.get("active_model")

    # If model_id specified, check if we need to load or switch model
    if model_id and active_model != model_id:
        print(f"\033[1;34mLoading model '{model_id}' on {base_url}...\033[0m")
        load_payload = {"model_id": model_id}
        if variant:
            load_payload["variant"] = variant
        load_resp = _http_post_json(f"{base_url}/api/v1/load", load_payload)
        if not load_resp or load_resp.get("status") == "error":
            print(f"\033[1;31mFailed to load model '{model_id}': {load_resp}\033[0m")
            return 1
        active_model = model_id
        print(f"\033[1;32mModel '{active_model}' loaded successfully!\033[0m\n")

    if not active_model:
        # Check registered models to see what can be loaded
        models_data = _http_get(f"{base_url}/api/v1/models")
        ready_models = []
        if models_data:
            for m in models_data.get("models", []):
                if m.get("is_ready"):
                    ready_models.append(m["model_id"])

        if ready_models:
            print(f"No model currently active. Available local models: {', '.join(ready_models)}")
            print(f"Loading '{ready_models[0]}'...")
            load_resp = _http_post_json(f"{base_url}/api/v1/load", {"model_id": ready_models[0]})
            if load_resp and load_resp.get("status") != "error":
                active_model = ready_models[0]
            else:
                print("\033[1;31mPlease specify a model: halofpx run <model_id>\033[0m")
                return 1
        else:
            print("\033[1;31mNo models ready to load. Run 'halofpx list' or 'halofpx pull <model>' first.\033[0m")
            return 1

    # Banner
    print("\033[1;36m" + "=" * 78)
    print(f" 💬 HaloFPX Interactive Chat — {active_model}")
    print(f" Connected to: {base_url}")
    print(" Commands: /help, /model, /clear, /status, /exit")
    print("=" * 78 + "\033[0m\n")

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    while True:
        try:
            user_input = input("\033[1;36mUser > \033[0m").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\033[1;33mExiting chat. Goodbye!\033[0m")
            break

        if not user_input:
            continue

        # REPL commands
        if user_input.lower() in ("/exit", "/quit", "/q"):
            print("\033[1;33mGoodbye!\033[0m")
            break

        if user_input.lower() == "/clear":
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            print("\033[1;32mConversation context cleared.\033[0m\n")
            continue

        if user_input.lower() == "/help":
            print("\nAvailable chat commands:")
            print("  \033[1m/help\033[0m    - Show this help message")
            print("  \033[1m/clear\033[0m   - Reset conversation context")
            print("  \033[1m/model\033[0m   - Show currently active model")
            print("  \033[1m/status\033[0m  - Show engine and hardware telemetry")
            print("  \033[1m/exit\033[0m    - Exit chat session\n")
            continue

        if user_input.lower() == "/model":
            print(f"\nActive model: \033[1;32m{active_model}\033[0m\n")
            continue

        if user_input.lower() == "/status":
            st = _http_get(f"{base_url}/api/v1/status")
            if st:
                eng = st.get("engine", {})
                telem = st.get("telemetry", {})
                print("\nServer Status:")
                print(f"  Model: {eng.get('model_id')} ({eng.get('variant')})")
                print(f"  Device: {eng.get('device')}")
                print(f"  VRAM / RAM: {telem.get('ram_used_gib', 0):.1f} / {telem.get('ram_total_gib', 0):.1f} GiB")
                print(f"  GPU Busy: {telem.get('gpu_busy_percent', 0)}%\n")
            else:
                print("Could not retrieve status.")
            continue

        # Append user message
        messages.append({"role": "user", "content": user_input})

        # Stream response
        print("\033[1;32mAssistant > \033[0m", end="", flush=True)

        payload = {
            "model": active_model,
            "messages": messages,
            "stream": True,
            "temperature": 0.7
        }

        full_reply = ""
        in_thinking = False

        try:
            req = urllib.request.Request(
                f"{base_url}/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "halofpx-chat"}
            )
            with urllib.request.urlopen(req, timeout=300.0) as resp:
                for line in resp:
                    line_str = line.decode("utf-8").strip()
                    if not line_str or not line_str.startswith("data: "):
                        continue
                    data_str = line_str[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        choices = chunk.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})

                        reasoning = delta.get("reasoning_content")
                        if reasoning:
                            if not in_thinking:
                                sys.stdout.write("\033[2m<think>\n")
                                in_thinking = True
                            sys.stdout.write(reasoning)
                            sys.stdout.flush()

                        content = delta.get("content", "")
                        if content:
                            if in_thinking:
                                sys.stdout.write("</think>\033[0m\n")
                                in_thinking = False
                            sys.stdout.write(content)
                            sys.stdout.flush()
                            full_reply += content
                    except json.JSONDecodeError:
                        continue
            if in_thinking:
                sys.stdout.write("</think>\033[0m\n")
            sys.stdout.write("\n\n")
            sys.stdout.flush()
            messages.append({"role": "assistant", "content": full_reply})
        except KeyboardInterrupt:
            print("\n\033[1;33m[Generation interrupted]\033[0m\n")
            if full_reply:
                messages.append({"role": "assistant", "content": full_reply})
        except Exception as e:
            print(f"\n\033[1;31mError during streaming: {e}\033[0m\n")

    return 0
