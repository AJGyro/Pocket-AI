import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tools import ToolRegistry, register_all_tools

SYSTEM_PROMPT = """You are GhostHand, an intelligent Windows desktop automation agent powered by FlaUI and Microsoft UI Automation (UIA3).
Your job is to execute user instructions on Windows applications using your provided tools.

Deterministic Workflow:
1. Application Launch:
   - If the app is not already open, call app_launch(app_path='notepad.exe') (or 'calc.exe', etc.).
   - app_launch automatically launches the application AND attaches the active automation session.
   - NEVER call session_attach immediately after a successful app_launch — the session is ALREADY attached.
2. Inspect the UI (Observe First):
   - Call ui_observe(level='normal') once to get the window's elements.
   - Inspect the returned 'elements' list: find the target element and note its 'id', 'control_type', and 'name'.
   - Note for Notepad & modern apps: The main text editor in Windows Notepad has control_type 'Document' (named 'Text editor' or automation_id 'ContentTextBox'), NOT an 'Edit' or 'TextBox'.
3. Interaction:
   - To type text: call ui_type(element_id=..., text=...) using the observed element 'id'.
   - To click buttons: call ui_click(element_id=...).
   - To send shortcuts: call ui_keys(element_id=..., keys='ctrl+s').
4. Anti-Thrashing & Recovery Rules:
   - NEVER repeat the exact same failed tool call.
   - If a tool reports an error or thrash warning, stop and inspect the error message carefully.
   - Never call session_attach repeatedly with the same process name. If attachment fails, check window_list or try window_title.
   - Once the user's task is completed, answer concisely describing what was done."""

class QwenClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080/v1", model: str = "qwen2.5-coder-7b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def check_health(self) -> bool:
        url = f"{self.base_url}/models"
        req = urllib.request.Request(url, headers={"User-Agent": "GhostHand-Agent"})
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status in (200, 204)
        except Exception:
            return False

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GhostHand-Agent",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read().decode("utf-8")
                return json.loads(data)
        except urllib.error.HTTPError as ex:
            err_body = ex.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP Error {ex.code}: {err_body}")
        except urllib.error.URLError as ex:
            raise ConnectionError(f"Cannot reach Qwen server at {self.base_url}: {ex.reason}")

def parse_fallback_tool_calls(text: str) -> List[Dict[str, Any]]:
    results = []
    tag_matches = re.finditer(r"<tool_call>\s*({.*?})\s*</tool_call>", text, re.DOTALL)
    for m in tag_matches:
        try:
            call_obj = json.loads(m.group(1))
            name = call_obj.get("name") or call_obj.get("tool")
            args = call_obj.get("arguments") or call_obj.get("args") or {}
            if name:
                results.append({"function": {"name": name, "arguments": json.dumps(args)}})
        except Exception:
            continue

    if not results:
        block_matches = re.finditer(r"```(?:json)?\s*({[\s\S]*?\"tool\"[\s\S]*?})\s*```", text)
        for m in block_matches:
            try:
                call_obj = json.loads(m.group(1))
                name = call_obj.get("tool") or call_obj.get("name")
                args = call_obj.get("args") or call_obj.get("arguments") or {}
                if name:
                    results.append({"function": {"name": name, "arguments": json.dumps(args)}})
            except Exception:
                continue

    return results

class AgentRunner:
    def __init__(self, client: QwenClient, registry: ToolRegistry):
        self.client = client
        self.registry = registry
        self.messages: List[Dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    def reset(self):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def run_turn(self, user_input: str, max_steps: int = 10):
        self.messages.append({"role": "user", "content": user_input})
        tools_schema = self.registry.get_schemas()
        failed_calls: Dict[str, int] = {}

        for step in range(max_steps):
            try:
                resp = self.client.chat_completion(self.messages, tools=tools_schema)
            except Exception as ex:
                print(f"\n[-] Error contacting model: {ex}")
                return

            choice = resp.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content") or ""
            tool_calls = message.get("tool_calls") or []

            if not tool_calls and ("<tool_call>" in content or '"tool"' in content):
                tool_calls = parse_fallback_tool_calls(content)

            if not tool_calls:
                print(f"\n[Agent] > {content.strip()}\n")
                self.messages.append({"role": "assistant", "content": content})
                return

            self.messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": tool_calls,
            })

            for call in tool_calls:
                fn = call.get("function", {})
                tool_name = fn.get("name", "")
                raw_args = fn.get("arguments", "{}")
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except json.JSONDecodeError:
                        args = {}
                else:
                    args = raw_args or {}

                call_id = call.get("id", f"call_{int(time.time()*1000)}")
                print(f"  [*] [Tool] {tool_name}({json.dumps(args, ensure_ascii=False)})")

                call_sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"

                if failed_calls.get(call_sig, 0) >= 1:
                    res = {
                        "success": False,
                        "error": f"Tool '{tool_name}' failed on the previous attempt with these exact arguments in the current session. Do not repeat failed calls without changing parameters or strategy.",
                    }
                    print(f"      [-] Thrash prevented: repeated failing call blocked")
                else:
                    try:
                        res = self.registry.execute(tool_name, **args)
                        res_str = json.dumps(res, ensure_ascii=False)
                        short_res = res_str if len(res_str) <= 180 else res_str[:180] + "..."
                        print(f"      [+] Result: {short_res}")

                        if res.get("success"):
                            failed_calls.pop(call_sig, None)
                            if tool_name in ("app_launch", "session_attach", "session_end"):
                                failed_calls.clear()
                        else:
                            failed_calls[call_sig] = failed_calls.get(call_sig, 0) + 1
                    except Exception as ex:
                        res = {"success": False, "error": str(ex)}
                        failed_calls[call_sig] = failed_calls.get(call_sig, 0) + 1
                        print(f"      [-] Error: {ex}")

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "name": tool_name,
                    "content": json.dumps(res, ensure_ascii=False),
                })

        print("\n[!] Step limit reached for this turn.")

def main():
    parser = argparse.ArgumentParser(description="GhostHand Agent Terminal Chat")
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1", help="Qwen server endpoint")
    parser.add_argument("--model", default="qwen2.5-coder-7b", help="Model name alias")
    args = parser.parse_args()

    registry = register_all_tools()
    client = QwenClient(base_url=args.url, model=args.model)
    runner = AgentRunner(client, registry)

    print("=" * 70)
    print(" GhostHand Windows Automation Agent (Qwen + FlaUI + UIA3)")
    print(f" Target Server: {args.url}")
    print(f" Tools Loaded: {len(registry.list_tools())}")
    print(" Type 'exit' to quit, 'clear' to reset chat, 'status' to check server.")
    print("=" * 70)

    if client.check_health():
        print(" Connected to Qwen server.")
    else:
        print(" Notice: Qwen server is not running at http://127.0.0.1:8080.")
        print(" Run 'E:\\Start\\Qwen2.5-server.bat' in another terminal to start it.")
    print()

    while True:
        try:
            user_input = input("You > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting GhostHand.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit"):
            print("Goodbye.")
            break
        if user_input.lower() == "clear":
            runner.reset()
            print("Chat history reset.\n")
            continue
        if user_input.lower() == "status":
            alive = client.check_health()
            print(f"Server at {args.url} alive: {alive}\n")
            continue

        runner.run_turn(user_input)

if __name__ == "__main__":
    main()
