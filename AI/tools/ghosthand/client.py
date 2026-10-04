import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from .errors import ErrorCode, GhostHandException

class GhostHandClient:
    def __init__(self, cli_path: Optional[str] = None, session_file: Optional[str] = None):
        self.cli_path = self._resolve_cli_path(cli_path)
        self.session_file: Optional[str] = session_file
        self.active_pid: Optional[int] = None
        self.active_process: Optional[str] = None
        self.active_window: Optional[str] = None

    def _resolve_cli_path(self, override_path: Optional[str]) -> str:
        candidates = [
            override_path,
            os.environ.get("FLAUI_CLI_PATH"),
            r"E:\FlaUI.Tools\flaui.exe",
            str(Path(__file__).resolve().parents[3] / "FlaUI.Tools" / "flaui.exe"),
            "flaui.exe",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return override_path or r"E:\FlaUI.Tools\flaui.exe"

    def get_state(self) -> Dict[str, Any]:
        return {
            "session_file": self.session_file,
            "active_pid": self.active_pid,
            "active_process": self.active_process,
            "active_window": self.active_window,
        }

    def get_state_signature(self) -> str:
        return f"{self.session_file}:{self.active_pid}:{self.active_process}"

    def run_raw(self, args: List[str], timeout_s: float = 30.0) -> Dict[str, Any]:
        cmd = [self.cli_path] + list(args)
        is_session_init = len(args) >= 2 and args[0] == "session" and args[1] in ("new", "attach")
        if self.session_file and not is_session_init and "--session" not in args:
            cmd.extend(["--session", self.session_file])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            raise GhostHandException(
                ErrorCode.TIMEOUT,
                f"Command '{' '.join(args)}' timed out after {timeout_s}s",
                recoverable=True,
            )
        except Exception as ex:
            raise GhostHandException(
                ErrorCode.ACTION_FAILED,
                f"Failed to execute CLI process: {str(ex)}",
                recoverable=False,
            )

        output = proc.stdout.strip() or proc.stderr.strip()
        if not output:
            if proc.returncode != 0:
                raise GhostHandException(
                    ErrorCode.ACTION_FAILED,
                    f"Command failed with exit code {proc.returncode} (no output)",
                    recoverable=True,
                )
            return {"success": True}

        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            if proc.returncode != 0:
                raise GhostHandException(
                    ErrorCode.ACTION_FAILED,
                    f"Command failed ({proc.returncode}): {output}",
                    recoverable=True,
                )
            return {"success": True, "raw_output": output}

        return data

    def _update_session_state(self, res: Dict[str, Any]) -> None:
        if res.get("success"):
            s_file = res.get("sessionFile") or res.get("session_file")
            if s_file:
                self.session_file = str(s_file)
            self.active_pid = res.get("pid") or res.get("processId")
            self.active_process = res.get("processName") or res.get("process_name")
            self.active_window = res.get("mainWindowTitle") or res.get("window_title")

    def session_new(
        self,
        app_path: str,
        args: Optional[str] = None,
        wait_title: Optional[str] = None,
        timeout_ms: int = 30000,
        session_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        cmd = ["session", "new", "--app", app_path, "--timeout", str(timeout_ms)]
        if args:
            cmd.extend(["--args", args])
        if wait_title:
            cmd.extend(["--wait-title", wait_title])
        target_session = session_file or self.session_file
        if target_session:
            cmd.extend(["--session", target_session])
        res = self.run_raw(cmd, timeout_s=(timeout_ms / 1000.0) + 5.0)
        self._update_session_state(res)
        return res

    def session_attach(
        self,
        pid: Optional[int] = None,
        process_name: Optional[str] = None,
        window_title: Optional[str] = None,
        timeout_ms: int = 10000,
        session_file: Optional[str] = None,
    ) -> Dict[str, Any]:
        cmd = ["session", "attach", "--timeout", str(timeout_ms)]
        if pid is not None:
            cmd.extend(["--pid", str(pid)])
        elif process_name:
            cmd.extend(["--name", process_name])
        elif window_title:
            cmd.extend(["--title", window_title])
        else:
            raise GhostHandException(
                ErrorCode.INVALID_ARGUMENT,
                "Must provide pid, process_name, or window_title to session_attach",
                recoverable=False,
            )
        target_session = session_file or self.session_file
        if target_session:
            cmd.extend(["--session", target_session])
        res = self.run_raw(cmd, timeout_s=(timeout_ms / 1000.0) + 5.0)
        self._update_session_state(res)
        return res

    def session_status(self) -> Dict[str, Any]:
        return self.run_raw(["session", "status"])

    def session_end(self) -> Dict[str, Any]:
        res = self.run_raw(["session", "end"])
        if res.get("success"):
            self.session_file = None
            self.active_pid = None
            self.active_process = None
            self.active_window = None
        return res

    def window_list(self) -> Dict[str, Any]:
        return self.run_raw(["window", "list"])

    def window_focus(self, window_handle: str) -> Dict[str, Any]:
        return self.run_raw(["window", "focus", "--window", window_handle])

    def window_close(self, window_handle: str) -> Dict[str, Any]:
        return self.run_raw(["window", "close", "--window", window_handle])

    def elem_find(
        self,
        aid: Optional[str] = None,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        class_name: Optional[str] = None,
        timeout_ms: int = 10000,
        window_handle: Optional[str] = None,
    ) -> Dict[str, Any]:
        cmd = ["elem", "find", "--timeout", str(timeout_ms)]
        if aid:
            cmd.extend(["--aid", aid])
        if name:
            cmd.extend(["--name", name])
        if control_type:
            cmd.extend(["--type", control_type])
        if class_name:
            cmd.extend(["--class", class_name])
        if window_handle:
            cmd.extend(["--window", window_handle])
        return self.run_raw(cmd, timeout_s=(timeout_ms / 1000.0) + 5.0)

    def elem_tree(
        self,
        depth: int = 3,
        root_id: Optional[str] = None,
        window_handle: Optional[str] = None,
    ) -> Dict[str, Any]:
        cmd = ["elem", "tree", "--depth", str(depth)]
        if root_id:
            cmd.extend(["--root", root_id])
        if window_handle:
            cmd.extend(["--window", window_handle])
        return self.run_raw(cmd, timeout_s=30.0)

    def elem_props(self, element_id: str) -> Dict[str, Any]:
        return self.run_raw(["elem", "props", "--id", element_id])

    def elem_click(self, element_id: str) -> Dict[str, Any]:
        return self.run_raw(["elem", "click", "--id", element_id])

    def elem_type(self, element_id: str, text: str) -> Dict[str, Any]:
        return self.run_raw(["elem", "type", "--id", element_id, "--text", text])

    def elem_set_value(self, element_id: str, value: str) -> Dict[str, Any]:
        return self.run_raw(["elem", "set-value", "--id", element_id, "--value", value])

    def elem_get_value(self, element_id: str) -> Dict[str, Any]:
        return self.run_raw(["elem", "get-value", "--id", element_id])

    def elem_get_state(self, element_id: str) -> Dict[str, Any]:
        return self.run_raw(["elem", "get-state", "--id", element_id])

    def elem_select(self, element_id: str, item: str) -> Dict[str, Any]:
        return self.run_raw(["elem", "select", "--id", element_id, "--item", item])

    def elem_keys(self, element_id: str, keys: str) -> Dict[str, Any]:
        return self.run_raw(["elem", "keys", "--keys", keys, "--id", element_id])

    def elem_scroll_into_view(self, element_id: str) -> Dict[str, Any]:
        return self.run_raw(["elem", "scroll-into-view", "--id", element_id])
