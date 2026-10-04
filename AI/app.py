import argparse
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

AI_DIR = Path(__file__).resolve().parent
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

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
   - Once the user's task is completed, answer concisely describing what was done."""

class QwenClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080/v1", model: str = "qwen2.5-coder-7b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def check_health(self) -> bool:
        url = f"{self.base_url}/models"
        req = urllib.request.Request(url, headers={"User-Agent": "PocketAI-Web"})
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
                "User-Agent": "PocketAI-Web",
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

class PocketAIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, dist_dir: Path, registry: ToolRegistry, qwen_client: QwenClient, **kwargs):
        self.dist_dir = dist_dir
        self.registry = registry
        self.qwen_client = qwen_client
        super().__init__(*args, directory=str(dist_dir), **kwargs)

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        url_path = self.path.split("?")[0].rstrip("/")
        if not url_path:
            url_path = "/"

        if url_path in ("/health", "/v1/health"):
            self._handle_health()
            return

        if url_path in ("/models", "/v1/models"):
            self._handle_models()
            return

        if url_path == "/api/tools":
            self._handle_tools()
            return

        if url_path == "/api/session":
            self._handle_session()
            return

        target_file = self.dist_dir / url_path.lstrip("/")
        if target_file.is_file():
            self._serve_file(target_file)
            return

        index_file = self.dist_dir / "index.html"
        if index_file.is_file():
            self._serve_file(index_file)
        else:
            self.send_error(404, "Frontend dist/index.html not found. Run 'npm run build' in AI/web.")

    def do_POST(self):
        url_path = self.path.split("?")[0].rstrip("/")
        if url_path in ("/chat/completions", "/v1/chat/completions"):
            self._handle_chat_completions()
            return

        self.send_error(404, "Endpoint not found")

    def _serve_file(self, file_path: Path):
        content_type, _ = mimetypes.guess_type(str(file_path))
        if not content_type:
            if file_path.suffix == ".ts" or file_path.suffix == ".tsx":
                content_type = "application/javascript"
            else:
                content_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as ex:
            self.send_error(500, f"Error reading file: {ex}")

    def _handle_health(self):
        qwen_alive = self.qwen_client.check_health()
        data = {
            "status": "ok",
            "app": "Pocket AI",
            "engine": "GhostHand (FlaUI + UIA3)",
            "qwen_connected": qwen_alive,
            "tools_count": len(self.registry.list_tools()),
            "kv_slots": 1,
        }
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_models(self):
        data = {
            "object": "list",
            "data": [
                {"id": "pocket-ai-ghosthand", "object": "model"},
                {"id": self.qwen_client.model, "object": "model"},
            ],
        }
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_tools(self):
        tools = self.registry.get_schemas()
        body = json.dumps({"tools": tools}, default=str).encode("utf-8")
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_session(self):
        try:
            status_tool = self.registry.get("session_status")
            res = status_tool.execute() if status_tool else {}
        except Exception as ex:
            res = {"success": False, "error": str(ex)}
        body = json.dumps(res).encode("utf-8")
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_chat_completions(self):
        content_len = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(content_len).decode("utf-8")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON payload")
            return

        is_stream = payload.get("stream", False)
        incoming_messages = payload.get("messages", [])
        temperature = payload.get("temperature", 0.2)

        if not incoming_messages:
            self.send_error(400, "Messages cannot be empty")
            return

        conversation: List[Dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        for m in incoming_messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
                content = " ".join(text_parts)
            conversation.append({"role": role, "content": content})

        if is_stream:
            self._stream_agent_execution(conversation, temperature)
        else:
            self._sync_agent_execution(conversation, temperature)

    def _send_sse_delta(self, content: str):
        event = {
            "choices": [
                {
                    "delta": {"content": content},
                    "index": 0,
                    "finish_reason": None,
                }
            ]
        }
        chunk = f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")
        self.wfile.write(chunk)
        self.wfile.flush()

    def _send_sse_done(self):
        done = b"data: [DONE]\n\n"
        self.wfile.write(done)
        self.wfile.flush()

    def _stream_agent_execution(self, conversation: List[Dict[str, Any]], temperature: float):
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        tools_schema = self.registry.get_schemas()
        failed_calls: Dict[str, int] = {}
        max_steps = 30

        try:
            for _ in range(max_steps):
                resp = self.qwen_client.chat_completion(conversation, tools=tools_schema, temperature=temperature)
                choice = resp.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content") or ""
                tool_calls = message.get("tool_calls") or []

                if not tool_calls and ("<tool_call>" in content or '"tool"' in content):
                    tool_calls = parse_fallback_tool_calls(content)

                if not tool_calls:
                    if content:
                        self._send_sse_delta(content)
                    break

                conversation.append({
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
                    args_preview = json.dumps(args, ensure_ascii=False)
                    if len(args_preview) > 100:
                        args_preview = args_preview[:100] + "..."

                    self._send_sse_delta(f"\n\n> ⚙️ **GhostHand**: `{tool_name}({args_preview})`\n")

                    call_sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
                    if failed_calls.get(call_sig, 0) >= 1:
                        res = {
                            "success": False,
                            "error": f"Tool '{tool_name}' failed on the previous attempt with these exact arguments in the current session. Strategy adjusted.",
                        }
                        self._send_sse_delta("> ↳ ⚠️ *Duplicate failing call blocked by thrash prevention*\n\n")
                    else:
                        try:
                            res = self.registry.execute(tool_name, **args)
                            if res.get("success"):
                                failed_calls.pop(call_sig, None)
                                if tool_name in ("app_launch", "session_attach", "session_end"):
                                    failed_calls.clear()
                                short_info = res.get("mainWindowTitle") or res.get("name") or res.get("id") or "Success"
                                self._send_sse_delta(f"> ↳ ✅ `{short_info}`\n\n")
                            else:
                                failed_calls[call_sig] = failed_calls.get(call_sig, 0) + 1
                                err = res.get("message") or res.get("error") or "Operation failed"
                                self._send_sse_delta(f"> ↳ ❌ `{err}`\n\n")
                        except Exception as ex:
                            res = {"success": False, "error": str(ex)}
                            failed_calls[call_sig] = failed_calls.get(call_sig, 0) + 1
                            self._send_sse_delta(f"> ↳ ❌ `{ex}`\n\n")

                    conversation.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": tool_name,
                        "content": json.dumps(res, ensure_ascii=False),
                    })

            self._send_sse_done()
            self.close_connection = True
        except Exception as ex:
            self._send_sse_delta(f"\n\n**Agent Execution Error**: {ex}\n")
            self._send_sse_done()
            self.close_connection = True

    def _sync_agent_execution(self, conversation: List[Dict[str, Any]], temperature: float):
        tools_schema = self.registry.get_schemas()
        failed_calls: Dict[str, int] = {}
        max_steps = 10
        final_content = ""

        try:
            for _ in range(max_steps):
                resp = self.qwen_client.chat_completion(conversation, tools=tools_schema, temperature=temperature)
                choice = resp.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content") or ""
                tool_calls = message.get("tool_calls") or []

                if not tool_calls and ("<tool_call>" in content or '"tool"' in content):
                    tool_calls = parse_fallback_tool_calls(content)

                if not tool_calls:
                    final_content = content
                    break

                conversation.append({
                    "role": "assistant",
                    "content": content,
                    "tool_calls": tool_calls,
                })

                for call in tool_calls:
                    fn = call.get("function", {})
                    tool_name = fn.get("name", "")
                    raw_args = fn.get("arguments", "{}")
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                    call_id = call.get("id", f"call_{int(time.time()*1000)}")

                    call_sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
                    if failed_calls.get(call_sig, 0) >= 1:
                        res = {"success": False, "error": "Duplicate call blocked"}
                    else:
                        try:
                            res = self.registry.execute(tool_name, **args)
                            if res.get("success"):
                                failed_calls.pop(call_sig, None)
                                if tool_name in ("app_launch", "session_attach", "session_end"):
                                    failed_calls.clear()
                            else:
                                failed_calls[call_sig] = failed_calls.get(call_sig, 0) + 1
                        except Exception as ex:
                            res = {"success": False, "error": str(ex)}
                            failed_calls[call_sig] = failed_calls.get(call_sig, 0) + 1

                    conversation.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "name": tool_name,
                        "content": json.dumps(res, ensure_ascii=False),
                    })

            response_data = {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "pocket-ai-ghosthand",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": final_content},
                        "finish_reason": "stop",
                    }
                ],
            }
            body = json.dumps(response_data).encode("utf-8")
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as ex:
            self.send_error(500, f"Agent Error: {ex}")

def create_server(host: str, port: int, dist_dir: Path, registry: ToolRegistry, qwen_client: QwenClient):
    def handler_factory(*args, **kwargs):
        return PocketAIHandler(*args, dist_dir=dist_dir, registry=registry, qwen_client=qwen_client, **kwargs)

    return ThreadingHTTPServer((host, port), handler_factory)

def main():
    parser = argparse.ArgumentParser(description="Pocket AI Web View & Automation Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--url", default="http://127.0.0.1:8080/v1", help="Qwen server endpoint")
    parser.add_argument("--model", default="qwen2.5-coder-7b", help="Qwen model name")
    parser.add_argument("--dist", default=str(AI_DIR / "web" / "dist"), help="Path to built web dist")
    args = parser.parse_args()

    dist_path = Path(args.dist).resolve()
    if not dist_path.exists() or not (dist_path / "index.html").exists():
        print(f"[!] Warning: dist directory not found at {dist_path}")
        print("    Build the frontend by running 'npm run build' inside AI/web.")

    registry = register_all_tools()
    qwen = QwenClient(base_url=args.url, model=args.model)

    server = create_server(args.host, args.port, dist_path, registry, qwen)

    print("=" * 70)
    print(" Pocket AI Web View Server (GhostHand + FlaUI + Qwen)")
    print(f" Web UI:        http://{args.host}:{args.port}")
    print(f" Target Qwen:   {args.url}")
    print(f" Tools Loaded:  {len(registry.list_tools())}")
    print(f" Frontend Dist: {dist_path}")
    print("=" * 70)

    if qwen.check_health():
        print(" [+] Connected to Qwen server.")
    else:
        print(" [!] Notice: Qwen server is not running at http://127.0.0.1:8080.")
        print("     Run 'E:\\Start\\Qwen2.5-server.bat' to start the local LLM.")
    print("\n Server running. Press Ctrl+C to stop.\n")

    try:
        server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        print("\nStopping Pocket AI Web Server...")
        server.server_close()

if __name__ == "__main__":
    main()
