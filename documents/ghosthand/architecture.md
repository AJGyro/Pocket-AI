# GhostHand Architecture

## Overview
GhostHand is a semantic Windows desktop automation system designed for local LLM agents (such as Qwen) within the Pocket AI portable environment. It uses Microsoft UI Automation (UIA3) via FlaUI, completely eschewing screen coordinates, mouse cursor movement, and pixel matching.

```
                    ┌───────────────────────────────────┐
                    │            User Client            │
                    │   Terminal (main.py) OR           │
                    │   Browser Web UI (app.py:8000)    │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────▼─────────────────┐
                    │      Pocket AI Agent Runner       │
                    │  (main.py / app.py SSE Streaming) │
                    └─────────────────┬─────────────────┘
                                      │ HTTP POST /v1/chat/completions
                    ┌─────────────────▼─────────────────┐
                    │      Local llama-server.exe       │
                    │       (Qwen2.5-Coder-7B)          │
                    └─────────────────┬─────────────────┘
                                │ Tool Call Requests (JSON / Schema)
                    ┌───────────▼────────────┐
                    │    Pocket AI Tools     │
                    │   (AI/tools/ghosthand) │
                    └───────────┬────────────┘
                                │ Subprocess CLI Execution
                    ┌───────────▼────────────┐
                    │   FlaUI.Tools / CLI    │
                    │      (flaui.exe)       │
                    └───────────┬────────────┘
                                │ C# In-Process Engine
                    ┌───────────▼────────────┐
                    │     GhostHand.Core     │
                    │     (FlaUI + UIA3)     │
                    └───────────┬────────────┘
                                │ COM / Windows API
                    ┌───────────▼────────────┐
                    │ Windows UI Automation  │
                    │   Target Application   │
                    └────────────────────────┘
```

## Architectural Tenets
1. **Semantic Interaction Only**: Elements are selected by `AutomationId`, `Name`, `ControlType`, and `ClassName`. Interaction occurs through UIA Control Patterns (Invoke, Value, Toggle, SelectionItem, etc.).
2. **Untouched Cursor**: Mouse cursor is never hijacked, preventing user disturbance and race conditions.
3. **Session Caching**: Elements found in a session receive an 8-character hex ID, cached for fast subsequent actions.
4. **Context Capping**: Full UI trees can exceed model context limits. GhostHand implements semantic observation levels (`minimal`, `normal`, `detailed`) with item capping.
5. **Typed Error Taxonomy**: All errors are categorized with `ErrorCode`, human-readable explanations, and recovery hints for the LLM.

## Runtime Session State Management
To prevent ambiguity when multiple session files (`*.session.json`) exist in the workspace, `GhostHandClient` actively maintains session state:
- `session_file`: Absolute path to the active session file.
- `active_pid`: The operating system PID of the target application.
- `active_process`: The process name.
- `active_window`: The main window title.

All subsequent tool calls (`ui_observe`, `ui_find`, `ui_click`, `ui_type`, etc.) automatically pass `--session <session_file>` to `flaui.exe`, completely preventing session collision.

## Application Launch & Process Discovery
Packaged Windows 10/11 applications (e.g. `calc.exe`, modern `notepad.exe`) launch via stub executables that terminate immediately and redirect execution to a background process (e.g. `CalculatorApp.exe`).
- GhostHand maintains a target matrix (`KNOWN_APP_TARGETS`) mapping launcher aliases to candidate processes and window titles.
- `app_launch` launches the application and polls candidate processes/titles until a window is successfully bound, returning a fully initialized session.

## Deterministic Agent Execution Loop & Thrash Prevention
To prevent speculative trial-and-error (thrashing), GhostHand guides the LLM through a deterministic 4-step sequence:
1. **Launch & Attach**: `app_launch` resolves the executable path across Windows system directories, launches the process, and automatically waits for the window to bind the session.
2. **Observe**: The agent calls `ui_observe(level='normal')` once to receive the exact control hierarchy, IDs, and control types.
3. **Select**: The agent references observed element IDs directly (e.g. `Document` control in modern Notepad) instead of guessing control types.
4. **Act & Conclude**: Executes `ui_type`, `ui_click`, or `ui_keys` and finishes with a summary.

The agent runner monitors call history and intercepts consecutive failing calls with identical parameters in the same session state, directing the model to inspect `ui_observe` results rather than repeating failing calls.
