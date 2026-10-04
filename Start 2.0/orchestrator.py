#!/usr/bin/env python3
"""
Windows automation orchestrator
===============================
Local llama.cpp server (Qwen)  <->  this script  <->  flaui CLI + sandboxed file ops

How it works
------------
Each turn the model must reply with ONE JSON action (enforced with a JSON schema so
small local models cannot break the format):

    {"thought": "...", "tool": "flaui|fs|sys|done", "command": "...", "args": {...}}

The orchestrator validates the action against an allowlist, asks you to confirm risky
ones, runs it, and sends the JSON result back as the next message. Repeats until the
model says "done" or the step limit is hit.

Requirements
------------
  * Windows, Python 3.10+ (stdlib only, no pip packages)
  * flaui:        dotnet tool install --global FlaUI.Tool
  * llama-server, e.g.:
        llama-server -m Qwen2.5-7B-Instruct-Q4_K_M.gguf -c 16384 --port 8080 --jinja

Usage
-----
    python orchestrator.py "Create notes.txt in the workspace with a shopping list"
    python orchestrator.py                      # interactive: type tasks one by one
    python orchestrator.py --allow-root D:\\Docs --auto-app winword.exe "..."
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

MAX_OBS = 3500   # max characters of one tool result sent back to the model
MAX_READ = 3000  # max characters returned by fs read

# --------------------------------------------------------------------------------------
# flaui command allowlist:  command -> (value options, boolean flags)
# The model can only call commands/options listed here. `report` is deliberately absent
# (it files GitHub issues) and so is anything not documented in the flaui README.
# --------------------------------------------------------------------------------------
FLAUI_SPEC: dict[str, tuple[list[str], list[str]]] = {
    "session new": (["app", "args", "wait-title", "wait-timeout", "timeout"], []),
    "session attach": (["pid", "name", "title", "timeout"], []),
    "session status": ([], []),
    "session end": ([], ["close-app", "force"]),
    "elem find": (["aid", "name", "type", "class", "timeout", "window"], []),
    "elem tree": (["root", "depth"], []),
    "elem props": (["id"], []),
    "elem click": (["id"], ["double", "right"]),
    "elem clear": (["id", "window"], []),
    "elem type": (["id", "text"], []),
    "elem set-value": (["id", "value"], []),
    "elem select": (["id", "item"], []),
    "elem get-value": (["id", "save"], []),
    "elem get-state": (["id"], []),
    "elem get-text": (["id", "window"], []),
    "elem keys": (["keys", "id", "window"], []),
    "elem menu": (["path", "window"], []),
    "elem scroll-into-view": (["id", "window"], []),
    "elem scroll": (["id", "horizontal", "vertical", "window"], []),
    "elem expand": (["id", "window"], []),
    "elem collapse": (["id", "window"], []),
    "elem grid-info": (["id", "window"], []),
    "elem get-cell": (["id", "row", "column", "window"], []),
    "window list": ([], []),
    "window focus": (["handle"], []),
    "window close": (["handle", "title"], ["force"]),
    "window minimize": (["handle"], []),
    "window maximize": (["handle"], []),
    "window get-state": (["handle"], []),
    "wait": (["aid", "title", "timeout", "value", "state"], []),
    "screenshot": (["output", "id", "window"], []),
}
# Commands the flaui README lists as supported inside `batch`
BATCH_OK = {
    "elem find", "elem click", "elem clear", "elem type", "elem select", "elem set-value",
    "elem get-value", "elem get-state", "elem keys", "elem scroll-into-view", "elem menu",
    "window list", "window focus", "window close", "screenshot",
}
RISKY_KEYS = {"alt+f4", "delete", "del", "ctrl+shift+delete"}
TOOLS = {"flaui", "fs", "sys", "done"}

ACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {"type": "string"},
        "tool": {"type": "string", "enum": sorted(TOOLS)},
        "command": {"type": "string"},
        "args": {"type": "object"},
        "summary": {"type": "string"},
    },
    "required": ["thought", "tool", "command", "args"],
    "additionalProperties": False,
}

DENIED = {"ok": False, "error": "The user DENIED this action. Do not retry it; choose another approach or finish with done."}


class ToolError(Exception):
    """A problem with the model's action that should be reported back to the model."""


@dataclass
class Config:
    server: str
    workspace: Path
    allowed_roots: list[Path]
    auto_apps: set[str]
    max_steps: int
    temperature: float
    flaui_exe: str
    session_dir: Path
    log_path: Path
    extra: dict = field(default_factory=dict)


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------
def truthy(v) -> bool:
    return v is True or str(v).strip().lower() in ("true", "1", "yes", "y")


def norm(a) -> dict:
    """Normalise arg names: wait_title -> wait-title."""
    return {str(k).replace("_", "-"): v for k, v in (a or {}).items()}


def app_key(s: str) -> str:
    name = Path(str(s).strip('"')).name.lower()
    return name if "." in name else name + ".exe"


def limit(obj, n: int = MAX_OBS) -> str:
    s = obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)
    if len(s) > n:
        s = s[:n] + f"... [truncated {len(s) - n} chars; narrow the query, e.g. smaller depth or --root]"
    return s


def log(cfg: Config, record: dict) -> None:
    record = {"ts": datetime.now().isoformat(timespec="seconds"), **record}
    with cfg.log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def gate(reason: str | None, act: dict) -> bool:
    """Ask the human before risky actions. Returns True if allowed."""
    if not reason:
        return True
    print(f"\n  !! Confirmation needed: {reason}")
    print(f"     action: {act['tool']} {act['command']} {json.dumps(act['args'], ensure_ascii=False)[:300]}")
    return input("     Allow? [y/N] ").strip().lower() in ("y", "yes")


# --------------------------------------------------------------------------------------
# Sandboxed paths + file tool
# --------------------------------------------------------------------------------------
def safe_path(cfg: Config, raw) -> Path:
    p = Path(os.path.expanduser(str(raw)))
    if not p.is_absolute():
        p = cfg.workspace / p
    p = p.resolve()
    for root in cfg.allowed_roots:
        if p == root or root in p.parents:
            return p
    raise ToolError(
        f"path is outside the allowed folders: {p}. Allowed: {[str(r) for r in cfg.allowed_roots]}"
    )


def need(a: dict, *keys: str) -> None:
    for k in keys:
        if k not in a or a[k] in (None, ""):
            raise ToolError(f"missing argument '{k}'")


def fs_reason(cfg: Config, cmd: str, a: dict) -> str | None:
    try:
        if cmd == "delete":
            return f"DELETE {safe_path(cfg, a['path'])}"
        if cmd == "write" and safe_path(cfg, a["path"]).exists():
            return f"overwrite existing file {safe_path(cfg, a['path'])}"
        if cmd in ("copy", "move") and safe_path(cfg, a["dst"]).exists():
            return f"{cmd} onto existing {safe_path(cfg, a['dst'])}"
    except (ToolError, KeyError):
        return None  # the real error is raised (and reported) when the action runs
    return None


def fs_exec(cfg: Config, cmd: str, a: dict) -> dict:
    if cmd == "list":
        p = safe_path(cfg, a.get("path", "."))
        if not p.is_dir():
            raise ToolError(f"not a folder: {p}")
        entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        items = [
            {"name": c.name, "type": "dir" if c.is_dir() else "file",
             "size": c.stat().st_size if c.is_file() else None}
            for c in entries[:200]
        ]
        return {"path": str(p), "items": items, "truncated": len(entries) > 200}

    if cmd == "exists":
        need(a, "path")
        return {"exists": safe_path(cfg, a["path"]).exists()}

    if cmd == "read":
        need(a, "path")
        p = safe_path(cfg, a["path"])
        if not p.is_file():
            raise ToolError(f"file not found: {p}")
        text = p.read_text(encoding="utf-8", errors="replace")
        return {"path": str(p), "content": text[:MAX_READ], "total_chars": len(text),
                "truncated": len(text) > MAX_READ}

    if cmd in ("write", "append"):
        need(a, "path")
        if a.get("content") is None:
            raise ToolError("missing argument 'content'")
        p = safe_path(cfg, a["path"])
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w" if cmd == "write" else "a", encoding="utf-8", newline="") as f:
            f.write(str(a["content"]))
        return {"path": str(p), "bytes": p.stat().st_size}

    if cmd == "mkdir":
        need(a, "path")
        p = safe_path(cfg, a["path"])
        p.mkdir(parents=True, exist_ok=True)
        return {"path": str(p)}

    if cmd in ("copy", "move"):
        need(a, "src", "dst")
        src, dst = safe_path(cfg, a["src"]), safe_path(cfg, a["dst"])
        if not src.exists():
            raise ToolError(f"source not found: {src}")
        if cmd == "move" and src in cfg.allowed_roots:
            raise ToolError("refusing to move an allowed root folder")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if cmd == "copy":
            if src.is_dir():
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        else:
            shutil.move(str(src), str(dst))
        return {"src": str(src), "dst": str(dst)}

    if cmd == "delete":
        need(a, "path")
        p = safe_path(cfg, a["path"])
        if p in cfg.allowed_roots:
            raise ToolError("refusing to delete an allowed root folder")
        if not p.exists():
            raise ToolError(f"not found: {p}")
        shutil.rmtree(p) if p.is_dir() else p.unlink()
        return {"deleted": str(p)}

    raise ToolError(
        f"unknown fs command '{cmd}'. Valid: list, exists, read, write, append, mkdir, copy, move, delete"
    )


# --------------------------------------------------------------------------------------
# sys tool (launch apps / sleep)
# --------------------------------------------------------------------------------------
def launch_reason(cfg: Config, target: str) -> str | None:
    bare = Path(target).name == target
    if bare and app_key(target) in cfg.auto_apps:
        return None
    return f"launch application '{target}'"


def sys_exec(cfg: Config, cmd: str, a: dict) -> dict:
    if cmd == "sleep":
        secs = max(0.0, min(float(a.get("seconds", 1)), 30.0))
        time.sleep(secs)
        return {"slept": secs}
    if cmd == "launch":
        if os.name != "nt":
            raise ToolError("launch is only supported on Windows")
        need(a, "target")
        os.startfile(str(a["target"]), arguments=str(a.get("args", "")))  # type: ignore[attr-defined]
        return {"launched": a["target"]}
    raise ToolError(f"unknown sys command '{cmd}'. Valid: launch, sleep")


# --------------------------------------------------------------------------------------
# flaui tool
# --------------------------------------------------------------------------------------
def validate_flaui(cfg: Config, cmd: str, a: dict) -> dict:
    spec = FLAUI_SPEC.get(cmd)
    if spec is None:
        raise ToolError(f"unknown flaui command '{cmd}'. Valid: {', '.join(FLAUI_SPEC)}")
    opts, flags = spec
    a = norm(a)
    bad = [k for k in a if k not in opts and k not in flags]
    if bad:
        raise ToolError(f"'{cmd}' does not accept {bad}. Allowed options: {opts + flags}")
    for k, v in a.items():
        if v is None or isinstance(v, (dict, list)):
            raise ToolError(f"option '{k}' must be a string, number or boolean")
    if cmd == "screenshot" and "output" in a:
        a["output"] = str(safe_path(cfg, a["output"]))  # screenshots only inside allowed folders
    if cmd == "elem tree" and "depth" not in a:
        a["depth"] = 2  # keep tree dumps small for the model's context window
    return a


def to_argv(cmd: str, a: dict) -> list[str]:
    _, flags = FLAUI_SPEC[cmd]
    argv = cmd.split()
    for k, v in a.items():
        if k in flags:
            if truthy(v):
                argv.append("--" + k)
        else:
            argv += ["--" + k, str(v)]
    return argv


def flaui_reason(cfg: Config, cmd: str, a: dict) -> str | None:
    if cmd == "session new":
        return launch_reason(cfg, str(a.get("app", "")))
    if cmd == "session end" and truthy(a.get("force")):
        return "force-kill the application"
    if cmd == "window close":
        return "close a window (unsaved work may be lost)"
    if cmd == "elem keys":
        k = str(a.get("keys", "")).lower().replace(" ", "")
        if k in RISKY_KEYS:
            return f"send risky keys '{k}'"
    return None


def run_flaui(cfg: Config, argv: list[str], timeout: int = 120) -> dict:
    try:
        r = subprocess.run(
            [cfg.flaui_exe, *argv], capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, cwd=cfg.session_dir,  # session files live here
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"flaui timed out after {timeout}s"}
    out = r.stdout.strip()
    try:
        parsed = json.loads(out) if out else None
    except json.JSONDecodeError:
        parsed = out
    ok = r.returncode == 0 and not (isinstance(parsed, dict) and parsed.get("success") is False)
    res: dict = {"ok": ok, "exit_code": r.returncode, "result": parsed}
    if r.stderr.strip():
        res["stderr"] = r.stderr.strip()[:500]
    if r.returncode == 3:
        res["hint"] = ("element not found within timeout: re-check aid/name, or explore with "
                       "'elem tree' (depth 2-3) or 'window list' (dialogs open as separate windows)")
    return res


def flaui_tool(cfg: Config, cmd: str, a: dict, act: dict) -> dict:
    if cmd == "batch":
        steps = a.get("steps")
        if not isinstance(steps, list) or not steps:
            raise ToolError('batch needs args.steps: a non-empty list of {"cmd": ..., "args": {...}}')
        clean, reason = [], None
        for s in steps:
            if not isinstance(s, dict):
                raise ToolError("each batch step must be an object {cmd, args}")
            c = str(s.get("cmd", "")).strip()
            if c not in BATCH_OK:
                raise ToolError(f"'{c}' cannot be used inside batch. Allowed: {sorted(BATCH_OK)}")
            sa = validate_flaui(cfg, c, s.get("args") or {})
            reason = reason or flaui_reason(cfg, c, sa)
            clean.append({"cmd": c, "args": sa})
        if not gate(reason, act):
            return DENIED
        with tempfile.NamedTemporaryFile("w", suffix=".json", dir=cfg.session_dir, delete=False,
                                         encoding="utf-8") as f:
            json.dump({"steps": clean}, f)
            path = f.name
        try:
            return run_flaui(cfg, ["batch", "--file", path])
        finally:
            Path(path).unlink(missing_ok=True)

    a = validate_flaui(cfg, cmd, a)
    if not gate(flaui_reason(cfg, cmd, a), act):
        return DENIED
    return run_flaui(cfg, to_argv(cmd, a))


# --------------------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------------------
def execute(cfg: Config, act: dict) -> dict:
    tool, cmd, a = act["tool"], str(act["command"]).strip(), norm(act["args"])
    try:
        if tool == "flaui":
            return flaui_tool(cfg, cmd, a, act)
        if tool == "fs":
            if not gate(fs_reason(cfg, cmd, a), act):
                return DENIED
            return {"ok": True, "result": fs_exec(cfg, cmd, a)}
        if tool == "sys":
            if cmd == "launch" and not gate(launch_reason(cfg, str(a.get("target", ""))), act):
                return DENIED
            return {"ok": True, "result": sys_exec(cfg, cmd, a)}
        raise ToolError(f"unknown tool '{tool}'")
    except ToolError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001 - report anything unexpected back to the model
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


# --------------------------------------------------------------------------------------
# Prompt
# --------------------------------------------------------------------------------------
def cheatsheet() -> str:
    lines = []
    for cmd, (opts, flags) in FLAUI_SPEC.items():
        parts = [f"{o}" for o in opts] + [f"[{f}: true]" for f in flags]
        lines.append(f"   - {cmd}: " + (", ".join(parts) if parts else "(no args)"))
    return "\n".join(lines)


SYSTEM_TEMPLATE = """You are a Windows automation agent. You finish the user's task by emitting exactly ONE action per turn as a JSON object. After each action you receive an OBSERVATION with the result.

Reply with ONLY this JSON (no markdown, no extra text):
{"thought": "<one short sentence>", "tool": "flaui|fs|sys|done", "command": "<command>", "args": {...}, "summary": "<only when tool is done>"}

TOOLS
1) flaui - drive a running Windows app through UI Automation. command = the flaui command, args = its options (names without --):
@@CHEAT@@
   - batch: args {"steps": [{"cmd": "elem find", "args": {"aid": "SaveBtn"}}, {"cmd": "elem click", "args": {"id": "$prev.elementId"}}]}
     Runs several steps at once; $prev.field uses the previous step's result. Allowed inside batch: elem find/click/clear/type/select/set-value/get-value/get-state/keys/scroll-into-view/menu, window list/focus/close, screenshot.
2) fs - file operations. Commands: list(path), exists(path), read(path), write(path, content), append(path, content), mkdir(path), copy(src, dst), move(src, dst), delete(path).
   Relative paths are inside the workspace: @@WORKSPACE@@
   Allowed folders: @@ROOTS@@
3) sys - launch(target, args) opens an app or file without creating a UI session; sleep(seconds) waits (max 30).
4) done - finish: {"thought": "...", "tool": "done", "command": "", "args": {}, "summary": "what was achieved, or why you had to stop"}

RULES
- Do file work (create/read/copy/move/delete files) with the fs tool, never through the GUI.
- To work in an app: flaui "session new" (app: "notepad.exe") or, if it is already running, "session attach" (name: "notepad"). Only one app session is active at a time; run session new/attach again to switch apps.
- Some modern packaged apps start a different process than the one launched. If session new cannot find the window: sys launch, then sys sleep 3, then session attach.
- Always "elem find" before interacting. Use the elementId from the result as "id". Never invent ids; after the UI changes, find the element again.
- Prefer finding by aid; otherwise by name (+ type such as Edit, Button, MenuItem, Document, ComboBox).
- When unsure what is on screen use "elem tree" (depth 2 or 3) or "window list". Dialogs such as Save As are separate windows: find them with window list and pass their handle as "window".
- Verify important results (elem get-value / get-text / get-state, or wait).
- If an action fails twice, change approach. If the task is impossible, finish with done and explain why.
- Some actions require the user's confirmation. If one is denied, do not retry it.
- Be efficient: use batch for known multi-step sequences.

EXAMPLES
{"thought": "Open Notepad.", "tool": "flaui", "command": "session new", "args": {"app": "notepad.exe"}}
{"thought": "Make the notes folder.", "tool": "fs", "command": "mkdir", "args": {"path": "notes"}}
"""


def build_system_prompt(cfg: Config) -> str:
    return (SYSTEM_TEMPLATE
            .replace("@@CHEAT@@", cheatsheet())
            .replace("@@WORKSPACE@@", str(cfg.workspace))
            .replace("@@ROOTS@@", ", ".join(str(r) for r in cfg.allowed_roots)))


# --------------------------------------------------------------------------------------
# LLM client (llama-server, OpenAI-compatible endpoint)
# --------------------------------------------------------------------------------------
_FORMATS = [  # newer builds -> older builds -> no constraint; we remember the first that works
    lambda: {"response_format": {"type": "json_schema",
                                 "json_schema": {"name": "action", "strict": True, "schema": ACTION_SCHEMA}}},
    lambda: {"response_format": {"type": "json_object", "schema": ACTION_SCHEMA}},
    lambda: {},
]
_fmt_idx = 0


def llm(cfg: Config, messages: list[dict]) -> str:
    global _fmt_idx
    url = cfg.server.rstrip("/") + "/v1/chat/completions"
    while True:
        body = {
            "model": "qwen",
            "messages": messages,
            "temperature": cfg.temperature,
            "max_tokens": 800,
            "stream": False,
            "cache_prompt": True,                            # reuse KV cache across turns (faster)
            "chat_template_kwargs": {"enable_thinking": False},  # Qwen3: skip <think> blocks
            **_FORMATS[_fmt_idx](),
        }
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=600) as r:
                data = json.load(r)
            return data["choices"][0]["message"].get("content") or ""
        except urllib.error.HTTPError as e:
            if e.code == 400 and _fmt_idx < len(_FORMATS) - 1:
                _fmt_idx += 1  # server rejected this response_format style; try the next
                continue
            raise RuntimeError(f"llama-server error {e.code}: {e.read().decode(errors='replace')[:300]}")


def parse_action(text: str) -> dict:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    i = text.find("{")
    if i < 0:
        raise ValueError("no JSON object found")
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[i:])
    except json.JSONDecodeError as e:
        raise ValueError(f"bad JSON: {e}")
    if not isinstance(obj, dict):
        raise ValueError("reply must be a JSON object")
    obj.setdefault("command", "")
    obj.setdefault("args", {})
    obj.setdefault("thought", "")
    if obj.get("tool") not in TOOLS:
        raise ValueError(f"'tool' must be one of {sorted(TOOLS)}")
    if not isinstance(obj["args"], dict):
        raise ValueError("'args' must be an object")
    return obj


def compact(msgs: list[dict], keep_last: int = 8, old_limit: int = 300) -> list[dict]:
    """Trim old observations so long tasks fit in the model's context window."""
    n, out = len(msgs), []
    for i, m in enumerate(msgs):
        if 2 <= i < n - keep_last and m["role"] == "user" and len(m["content"]) > old_limit:
            m = {**m, "content": m["content"][:old_limit] + " ...[older output trimmed]"}
        out.append(m)
    return out


# --------------------------------------------------------------------------------------
# Agent loop
# --------------------------------------------------------------------------------------
def run_task(cfg: Config, task: str) -> bool:
    messages = [
        {"role": "system", "content": build_system_prompt(cfg)},
        {"role": "user", "content": f"TASK: {task}"},
    ]
    log(cfg, {"event": "task", "task": task})
    bad_json, recent = 0, []

    for step in range(1, cfg.max_steps + 1):
        raw = llm(cfg, compact(messages))
        try:
            act = parse_action(raw)
        except ValueError as e:
            bad_json += 1
            print(f"[{step}] model reply not usable ({e})")
            if bad_json >= 3:
                print("Giving up: the model keeps returning invalid JSON.")
                return False
            messages += [
                {"role": "assistant", "content": raw[:500] or "(empty)"},
                {"role": "user", "content": f"OBSERVATION: invalid reply ({e}). Reply with ONLY one JSON object."},
            ]
            continue

        messages.append({"role": "assistant", "content": json.dumps(act, ensure_ascii=False)})
        print(f"[{step}] {act['thought']}")

        if act["tool"] == "done":
            summary = act.get("summary") or act["thought"]
            print(f"\nDONE: {summary}")
            log(cfg, {"event": "done", "summary": summary})
            return True

        print(f"    {act['tool']} {act['command']} {json.dumps(act['args'], ensure_ascii=False)[:200]}")
        obs = execute(cfg, act)
        print(f"    -> {'ok' if obs.get('ok') else 'FAIL'}  {limit(obs, 200)}")
        log(cfg, {"event": "action", "action": act, "result": limit(obs, 1500)})

        sig = json.dumps([act["tool"], act["command"], act["args"]], sort_keys=True)
        recent.append(sig)
        if len(recent) >= 5 and len(set(recent[-5:])) == 1:
            print("Stopping: the model repeated the same action 5 times.")
            return False
        if len(recent) >= 3 and len(set(recent[-3:])) == 1:
            obs["note"] = "You repeated the same action 3 times without progress. Try something different or finish with done."

        messages.append({"role": "user", "content": "OBSERVATION: " + limit(obs)})

    print(f"Stopped: reached the {cfg.max_steps}-step limit.")
    return False


# --------------------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------------------
def check_server(url: str) -> None:
    try:
        urllib.request.urlopen(url.rstrip("/") + "/health", timeout=5).read()
    except Exception as e:  # noqa: BLE001
        sys.exit(f"Cannot reach llama-server at {url} ({e}). Is it running and finished loading the model?")


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Local-LLM Windows automation orchestrator (flaui + files)")
    ap.add_argument("task", nargs="*", help="task in plain language (omit for interactive mode)")
    ap.add_argument("--server", default=os.environ.get("LLAMA_SERVER", "http://127.0.0.1:8080"))
    ap.add_argument("--workspace", default=str(Path.home() / "agent_workspace"),
                    help="default folder for files, session data, screenshots and the log")
    ap.add_argument("--allow-root", action="append", default=[],
                    help="extra folder the fs tool may touch (repeatable)")
    ap.add_argument("--auto-app", action="append", default=[],
                    help="app that may be launched without confirmation, e.g. winword.exe (repeatable)")
    ap.add_argument("--max-steps", type=int, default=30)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--flaui", default="flaui", help="path or name of the flaui executable")
    args = ap.parse_args()

    flaui_exe = shutil.which(args.flaui)
    if not flaui_exe:
        sys.exit("flaui not found. Install it with: dotnet tool install --global FlaUI.Tool")

    workspace = Path(args.workspace).expanduser().resolve()
    session_dir = workspace / ".flaui"
    session_dir.mkdir(parents=True, exist_ok=True)
    cfg = Config(
        server=args.server,
        workspace=workspace,
        allowed_roots=[workspace] + [Path(r).expanduser().resolve() for r in args.allow_root],
        auto_apps={"notepad.exe", "calc.exe", "mspaint.exe"} | {app_key(x) for x in args.auto_app},
        max_steps=args.max_steps,
        temperature=args.temperature,
        flaui_exe=flaui_exe,
        session_dir=session_dir,
        log_path=workspace / "agent_log.jsonl",
    )
    check_server(cfg.server)
    print(f"workspace: {cfg.workspace}\nlog:       {cfg.log_path}\n")

    try:
        if args.task:
            sys.exit(0 if run_task(cfg, " ".join(args.task)) else 1)
        while True:
            task = input("task> ").strip()
            if task.lower() in ("", "exit", "quit"):
                break
            run_task(cfg, task)
            print()
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except RuntimeError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
