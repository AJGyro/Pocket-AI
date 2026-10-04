# GhostHand Tool Reference

Complete reference of the 14 automation tools exposed to LLM agents via `ToolRegistry`.

---

## 1. Application & Session Tools

### `app_launch`
Launches an application and automatically attaches an active automation session.
- **Path Resolution**: Automatically checks `PATH`, `C:\Windows\System32`, `C:\Windows`, and `WindowsApps` aliases.
- **Strict Session Isolation**: Records running PIDs before launch, detects newly created processes, and binds strictly to the requested application. Disallowed processes (e.g., Chrome, Edge) are rejected. Validates `ApplicationFrameHost` window titles for packaged apps (e.g. Calculator).
- **Parameters**:
  - `app_path` (string, required): Executable name or path (e.g. `"notepad.exe"`, `"calc.exe"`).
  - `args` (string, optional): Command line arguments.
  - `wait_title` (string, optional): Window title to wait for.
  - `timeout_ms` (integer, default: 15000): Timeout in milliseconds.
- **Returns**: Session status dictionary including `pid`, `processName`, `mainWindowTitle`, and `sessionFile`.

### `session_attach`
Attaches to an already running application.
- **Parameters**:
  - `process_name` (string, optional): Process name without `.exe` (e.g. `"notepad"`).
  - `pid` (integer, optional): Operating system Process ID.
  - `window_title` (string, optional): Main window title to match.
  - `timeout_ms` (integer, default: 10000): Discovery timeout.
- **Returns**: Session attachment details.

### `session_status`
Queries the health of the active session.
- **Returns**: `process_alive`, `window_valid`, `cached_elements_count`, `main_window_title`.

### `session_end`
Terminates the active session and cleans up cached element references.

---

## 2. Window Management Tools

### `window_list`
Lists all top-level windows belonging to the attached process.
- **Returns**: Array of window objects containing hex handles, titles, and states.

### `window_focus`
Brings a specific window to the foreground.
- **Parameters**: `window_handle` (string, required, hex e.g. `"0x1A2B"`).

### `window_close`
Closes a window by handle.
- **Parameters**: `window_handle` (string, required, hex e.g. `"0x1A2B"`).

---

## 3. Semantic Observation Tools

### `ui_observe`
Scans the target window and returns a flattened, capped list of UI controls.
- **Output Schema**: Each element provides `id` (cached session ID), `name`, `control_type`, `automation_id`, `class_name`, `bounds`, `is_enabled`, `is_offscreen`, and `value`.
- **Parameters**:
  - `depth` (integer, default: 3): Tree descent depth.
  - `level` (string, default: `"normal"`):
    - `"minimal"`: Retains interactive controls (`Document`, `Edit`, `Button`, `MenuItem`, `ComboBox`, `CheckBox`, etc.).
    - `"normal"`: Standard hierarchy; prunes anonymous container panes while keeping controls. Capped at 150 items.
    - `"detailed"`: Full subtree up to 300 items.
  - `root_id` (string, optional): Element ID to scope observation to.
  - `window_handle` (string, optional): Hex window handle.

### `ui_find`
Finds an element matching semantic search criteria.
- **Fallback Aliases**: Automatically checks `Document` if an `Edit` search fails, and vice versa.
- **Semantic Number & Operator Aliases**: In apps like Windows Calculator where buttons have automation IDs like `num2Button` and names like `"Two"` rather than literal `"2"`, `ui_find` automatically maps digits (`0`-`9`) and operators (`+`, `-`, `*`, `/`, `=`, `.`) to their canonical UIA automation IDs and English names, enabling seamless semantic discovery without guessing element IDs.
- **Parameters**:
  - `automation_id` (string, optional): UIA AutomationId (preferred).
  - `name` (string, optional): Text label.
  - `control_type` (string, optional): UIA ControlType (`"Button"`, `"Document"`, `"Edit"`, etc.).
  - `class_name` (string, optional): Control class name.
  - `timeout_ms` (integer, default: 10000).
  - `window_handle` (string, optional).
- **Returns**: Element metadata and session-scoped `id`.

### `ui_get_properties`
Retrieves full UIA properties and supported pattern list for an element.
- **Parameters**: `element_id` (string, required).

---

## 4. Interaction Tools

### `ui_click`
Clicks a control via UIA `InvokePattern` or `TogglePattern` without moving the mouse cursor.
- **Parameters**: `element_id` (string, required).

### `ui_type`
Sends text keystrokes into an editable element or document.
- **Document & Non-ValuePattern Controls**: If direct text setting is not supported (e.g. `Document` in modern Notepad), automatically falls back to clicking/focusing the element and sending keyboard simulation keystrokes.
- **Parameters**:
  - `element_id` (string, required): Element ID to type into.
  - `text` (string, required): String to type.

### `ui_set_value`
Directly sets the text value of an element via `ValuePattern`. Faster and more reliable than typing for standard text inputs (note: modern Notepad `Document` controls do not support `ValuePattern`; use `ui_type` instead).
- **Parameters**:
  - `element_id` (string, required).
  - `value` (string, required): Text value to set.

### `ui_keys`
Sends key combinations or single navigation keys to the focused element.
- **Supported Sequences**: `"ctrl+s"`, `"alt+f4"`, `"enter"`, `"tab"`, `"escape"`, `"ctrl+shift+s"`, etc.
- **Parameters**:
  - `element_id` (string, required).
  - `keys` (string, required).
