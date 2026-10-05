# GhostHand MCP Server Documentation

## Overview

GhostHand is integrated as a local **Model Context Protocol (MCP)** server for **OpenCode**, giving the model (`Qwen3.5-9B`) coordinate-free, UIA3-based Windows automation capabilities over standard input/output (`stdio`).

```text
OpenCode (v1.18.34)
   ↓ stdio (JSON-RPC)
GhostHand MCP Server (mcp 2.3.0)
   ↓
GhostHand Client / Tools
   ↓
FlaUI.Tools (flaui.exe)
   ↓ UIA3
Windows Applications (Notepad, Calculator, Paint, etc.)
```

---

## Installation & Setup

1. **Python Environment**: `E:\Python\python.exe` (Python 3.12).
2. **MCP SDK**: Installed official `mcp >= 2.3.0` package.
3. **Module Resolution**: `E:\Python\Lib\site-packages\ghosthand.pth` points to `E:\AI` allowing direct invocation from anywhere.

---

## How to Run GhostHand MCP Server

### Standalone (Manual Testing)

Run the server directly via Python:

```powershell
E:\Python\python.exe -m ghosthand.mcp.server
```

*(Note: Stdio transport communicates JSON-RPC over stdout, and all diagnostic logs are printed to stderr).*

---

## OpenCode Configuration

OpenCode configuration is stored at [`E:\AI\.opencode\opencode.json`](file:///e:/AI/.opencode/opencode.json) and mirrored in [`E:\AI\config\opencode.json`](file:///e:/AI/config/opencode.json):

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "ghosthand": {
      "type": "local",
      "command": [
        "E:\\Python\\python.exe",
        "-m",
        "ghosthand.mcp.server"
      ],
      "cwd": "E:\\AI",
      "timeout": 30000
    }
  },
  "permission": {
    "ghosthand_*": "allow"
  },
  "agent": {
    "build": {
      "permission": {
        "ghosthand_*": "allow"
      }
    }
  }
}
```

---

## Verifying Connection in OpenCode

In PowerShell inside `E:\AI`, run:

```powershell
opencode mcp list
```

**Expected Output:**
```text
T  MCP Servers
|
•  ✓ ghosthand connected
|      E:\Python\python.exe -m ghosthand.mcp.server
|
—  1 server(s)
```

---

## Available MCP Tools

All tools return **compact JSON** designed to protect the 32k context window. Raw UI automation trees are never dumped by default.

| Tool Name | Purpose | Primary Parameters |
| :--- | :--- | :--- |
| `ghosthand_window_launch` | Launch a Windows app and create automation session | `app_path` (e.g. `"notepad.exe"`), `args` |
| `ghosthand_window_list` | List all top-level windows for active session | None |
| `ghosthand_window_focus` | Bring a window to foreground | `window_handle` (hex string) |
| `ghosthand_window_close` | Close an open window | `window_handle` (hex string) |
| `ghosthand_element_find` | Find a UI element by semantic properties | `automation_id`, `name`, `control_type` |
| `ghosthand_element_click` | Click an element using UIA Invoke/Toggle | `element_id` |
| `ghosthand_element_type` | Type text via simulated keystrokes | `element_id`, `text` |
| `ghosthand_element_set_value` | Set text value directly via UIA ValuePattern | `element_id`, `value` |
| `ghosthand_element_get_properties` | Inspect element attributes & supported patterns | `element_id` |
| `ghosthand_keyboard_press` | Send a special key (`enter`, `tab`, `esc`) | `element_id`, `key` |
| `ghosthand_keyboard_hotkey` | Send keyboard combo (`ctrl+s`, `alt+f4`) | `element_id`, `hotkey` |
| `ghosthand_session_attach` | Attach to an already running application | `process_name`, `pid`, or `window_title` |
| `ghosthand_session_status` | Check if active session & process are alive | None |
| `ghosthand_session_end` | Clean up and end active automation session | None |
| `ghosthand_element_tree` | Opt-in UI tree inspection (compact, capped at 50) | `depth` (default: 2), `level` |
| `ghosthand_screenshot` | Capture screen to disk and return file path | `output_path`, `element_id`, `window_handle` |

---

## Example OpenCode Workflow

When asking OpenCode to automate a Windows application:

### Prompt:
> *"Open Notepad and write 'Hello from Pocket AI' in it."*

### Execution:
1. OpenCode detects Windows automation intent and invokes:
   ```json
   ghosthand_window_launch({"app_path": "notepad.exe"})
   ```
   *Response:*
   ```json
   {"success": true, "message": "Launched notepad.exe successfully", "pid": 1234}
   ```

2. OpenCode finds the text document element:
   ```json
   ghosthand_element_find({"control_type": "Document"})
   ```
   *Response:*
   ```json
   {"success": true, "element": {"id": "elem_1", "control_type": "Document", "name": "Text editor"}}
   ```

3. OpenCode enters the text:
   ```json
   ghosthand_element_set_value({"element_id": "elem_1", "value": "Hello from Pocket AI"})
   ```
   *Response:*
   ```json
   {"success": true, "message": "Set value on element 'elem_1'"}
   ```

---

## Running Automated Tests

Run the full regression test suite (22 core tests + 9 MCP server tests = 31 tests):

```powershell
E:\Python\python.exe -m unittest discover -s E:\AI\tests -v
```
