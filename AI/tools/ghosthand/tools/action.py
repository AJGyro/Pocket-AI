import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from ..client import GhostHandClient
from ...base import BaseTool

APP_PROFILES: Dict[str, Dict[str, Any]] = {
    "notepad": {
        "valid_processes": ["notepad"],
        "disallowed_processes": ["chrome", "msedge", "firefox", "brave"],
        "default_session_name": "notepad.session.json",
    },
    "notepad.exe": {
        "valid_processes": ["notepad"],
        "disallowed_processes": ["chrome", "msedge", "firefox", "brave"],
        "default_session_name": "notepad.session.json",
    },
    "calc": {
        "valid_processes": ["calculatorapp", "calculator", "applicationframehost"],
        "disallowed_processes": ["chrome", "msedge", "firefox", "brave"],
        "frame_host_title_required": "Calculator",
        "default_session_name": "calculator.session.json",
    },
    "calc.exe": {
        "valid_processes": ["calculatorapp", "calculator", "applicationframehost"],
        "disallowed_processes": ["chrome", "msedge", "firefox", "brave"],
        "frame_host_title_required": "Calculator",
        "default_session_name": "calculator.session.json",
    },
    "calculator": {
        "valid_processes": ["calculatorapp", "calculator", "applicationframehost"],
        "disallowed_processes": ["chrome", "msedge", "firefox", "brave"],
        "frame_host_title_required": "Calculator",
        "default_session_name": "calculator.session.json",
    },
    "chrome": {
        "valid_processes": ["chrome"],
        "disallowed_processes": [],
        "default_session_name": "chrome.session.json",
    },
    "chrome.exe": {
        "valid_processes": ["chrome"],
        "disallowed_processes": [],
        "default_session_name": "chrome.session.json",
    },
    "mspaint": {
        "valid_processes": ["mspaint", "paint"],
        "disallowed_processes": ["chrome", "msedge", "firefox"],
        "default_session_name": "mspaint.session.json",
    },
}

def resolve_executable(app_path: str) -> str:
    if os.path.isabs(app_path) and os.path.exists(app_path):
        return app_path
    which = shutil.which(app_path)
    if which:
        return which

    cand = app_path if app_path.lower().endswith(".exe") else f"{app_path}.exe"
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidates = [
        os.path.join(system_root, "System32", cand),
        os.path.join(system_root, cand),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), cand),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WindowsApps", cand),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return app_path

def get_running_pids(image_names: List[str]) -> Set[int]:
    pids = set()
    for name in image_names:
        img_name = name if name.lower().endswith(".exe") else f"{name}.exe"
        try:
            res = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH", "/FI", f"IMAGENAME eq {img_name}"],
                capture_output=True,
                text=True,
                timeout=4,
                encoding="utf-8",
                errors="replace",
            )
            for line in res.stdout.strip().splitlines():
                parts = [p.strip('"') for p in line.split('","')]
                if len(parts) >= 2 and parts[1].isdigit():
                    pids.add(int(parts[1]))
        except Exception:
            pass
    return pids

class AppLaunchTool(BaseTool):
    name = "app_launch"
    description = "Launch an application (e.g. 'notepad.exe', 'calc.exe') and automatically establish an active automation session."
    parameters = {
        "type": "object",
        "properties": {
            "app_path": {
                "type": "string",
                "description": "Executable name or path (e.g. 'notepad.exe', 'calc.exe').",
            },
            "args": {
                "type": "string",
                "description": "Optional command line arguments.",
            },
            "wait_title": {
                "type": "string",
                "description": "Optional window title text to wait for.",
            },
            "timeout_ms": {
                "type": "integer",
                "description": "Timeout in milliseconds (default 15000).",
                "default": 15000,
            },
        },
        "required": ["app_path"],
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def _validate_session(
        self,
        app_path: str,
        profile: Optional[Dict[str, Any]],
        res: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        if not res.get("success"):
            return False, res.get("message", "Session attachment failed")

        proc_name = (res.get("processName") or res.get("process_name") or "").lower()
        pid = res.get("pid") or res.get("processId")
        win_title = res.get("mainWindowTitle") or res.get("window_title") or ""

        if profile:
            if proc_name in profile.get("disallowed_processes", []):
                return False, f"Launch validation failed: requested {app_path} but attached session belongs to {proc_name} (PID {pid})."

            if proc_name not in profile.get("valid_processes", []):
                return False, f"Launch validation failed: requested {app_path} but attached process is '{proc_name}', expected one of {profile.get('valid_processes')}."

            if proc_name == "applicationframehost":
                req_title = profile.get("frame_host_title_required", "").lower()
                if req_title and req_title not in win_title.lower():
                    return False, f"Launch validation failed: ApplicationFrameHost window title is '{win_title}', expected to contain '{req_title}'."
        else:
            expected_stem = Path(app_path).stem.lower()
            if expected_stem not in proc_name:
                return False, f"Launch validation failed: requested {app_path} but attached process is '{proc_name}'."

        return True, None

    def execute(
        self,
        app_path: str,
        args: Optional[str] = None,
        wait_title: Optional[str] = None,
        timeout_ms: int = 15000,
        **kwargs,
    ) -> Dict[str, Any]:
        resolved = resolve_executable(app_path)
        app_key = Path(app_path).name.lower()
        profile = APP_PROFILES.get(app_key) or APP_PROFILES.get(Path(app_path).stem.lower())

        valid_procs = profile["valid_processes"] if profile else [Path(resolved).stem.lower()]
        target_session_name = profile["default_session_name"] if profile else f"{Path(resolved).stem.lower()}.session.json"
        target_session_path = os.path.abspath(target_session_name)

        before_pids = get_running_pids(valid_procs)

        cmd = [resolved]
        if args:
            cmd.extend(args.split())

        try:
            proc = subprocess.Popen(cmd)
            launcher_pid = proc.pid
        except Exception as ex:
            return {
                "success": False,
                "message": f"Failed to start process '{resolved}': {str(ex)}",
            }

        deadline = time.time() + (timeout_ms / 1000.0)
        last_error = None
        first_iteration = True

        while first_iteration or time.time() < deadline:
            first_iteration = False
            current_pids = get_running_pids(valid_procs)
            new_pids = current_pids - before_pids

            candidates: List[Tuple[str, Any]] = []
            for np in sorted(new_pids, reverse=True):
                candidates.append(("pid", np))

            if launcher_pid in current_pids and launcher_pid not in new_pids:
                candidates.append(("pid", launcher_pid))

            for p in valid_procs:
                candidates.append(("name", p))

            if wait_title:
                candidates.append(("title", wait_title))

            for mode, val in candidates:
                try:
                    attach_timeout = min(1000, max(200, timeout_ms))
                    if mode == "pid":
                        res = self.client.session_attach(
                            pid=val,
                            timeout_ms=attach_timeout,
                            session_file=target_session_path,
                        )
                    elif mode == "name":
                        res = self.client.session_attach(
                            process_name=val,
                            timeout_ms=attach_timeout,
                            session_file=target_session_path,
                        )
                    else:
                        res = self.client.session_attach(
                            window_title=val,
                            timeout_ms=attach_timeout,
                            session_file=target_session_path,
                        )

                    is_valid, err_msg = self._validate_session(app_path, profile, res)
                    if is_valid:
                        return res
                    if err_msg:
                        last_error = err_msg
                except Exception as ex:
                    last_error = str(ex)

            rem = deadline - time.time()
            if rem > 0:
                time.sleep(min(0.2, rem))

        return {
            "success": False,
            "error_code": "LAUNCH_VALIDATION_FAILED",
            "message": f"Application '{app_path}' launched, but session validation failed within {timeout_ms}ms: {last_error}",
            "recovery": [
                "Verify the requested application window is open",
                "Check session_status to see current session status",
            ],
        }

class UiClickTool(BaseTool):
    name = "ui_click"
    description = "Click an element by ID using its UIA Invoke or Toggle pattern."
    parameters = {
        "type": "object",
        "properties": {
            "element_id": {
                "type": "string",
                "description": "Element ID to click.",
            },
        },
        "required": ["element_id"],
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, element_id: str, **kwargs) -> Dict[str, Any]:
        return self.client.elem_click(element_id=element_id)

class UiTypeTool(BaseTool):
    name = "ui_type"
    description = "Type text into an editable element using keyboard simulation."
    parameters = {
        "type": "object",
        "properties": {
            "element_id": {
                "type": "string",
                "description": "Element ID to type into.",
            },
            "text": {
                "type": "string",
                "description": "Text to type.",
            },
        },
        "required": ["element_id", "text"],
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, element_id: str, text: str, **kwargs) -> Dict[str, Any]:
        res = self.client.elem_type(element_id=element_id, text=text)
        if res.get("success"):
            return res
        self.client.elem_click(element_id=element_id)
        time.sleep(0.1)
        retry_res = self.client.elem_type(element_id=element_id, text=text)
        if retry_res.get("success"):
            return retry_res
        return res

class UiSetValueTool(BaseTool):
    name = "ui_set_value"
    description = "Set an element's value directly via UIA ValuePattern (faster and more reliable than typing for text boxes)."
    parameters = {
        "type": "object",
        "properties": {
            "element_id": {
                "type": "string",
                "description": "Element ID to set value on.",
            },
            "value": {
                "type": "string",
                "description": "Value to set.",
            },
        },
        "required": ["element_id", "value"],
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, element_id: str, value: str, **kwargs) -> Dict[str, Any]:
        return self.client.elem_set_value(element_id=element_id, value=value)

class UiKeysTool(BaseTool):
    name = "ui_keys"
    description = "Send key shortcuts or sequences to an element (e.g. 'ctrl+s', 'enter', 'alt+f4')."
    parameters = {
        "type": "object",
        "properties": {
            "element_id": {
                "type": "string",
                "description": "Element ID to send keys to.",
            },
            "keys": {
                "type": "string",
                "description": "Key sequence (e.g. 'ctrl+s', 'enter', 'tab').",
            },
        },
        "required": ["element_id", "keys"],
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, element_id: str, keys: str, **kwargs) -> Dict[str, Any]:
        return self.client.elem_keys(element_id=element_id, keys=keys)
