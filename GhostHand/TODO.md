# GhostHand Task List

## Phase 1: C# Foundation (GhostHand.Core)
- [x] Create GhostHand solution (`GhostHand.slnx`) and projects
- [x] Configure `net10.0-windows`, dependencies (`FlaUI.Core`, `FlaUI.UIA3`, `WindowsForms`), and warnings
- [x] Define Error taxonomy and typed error models (`ErrorCodes.cs`, `GhostHandError.cs`)
- [x] Define DTO models (`ElementInfo.cs`, `ActionResult.cs`, `ObservationResult.cs`, `ElementSelector.cs`, `GhostHandSession.cs`)
- [x] Define automation interface (`IGhostHandAutomation.cs`)
- [x] Implement structured logging (`GhostHandLogger.cs`)
- [x] Implement UIA pattern capability detector (`CapabilityResolver.cs`)
- [x] Implement element resolver with session caching (`ElementResolver.cs`)
- [x] Implement key parser for keyboard input (`KeyParser.cs`)
- [x] Implement Win32 interop (`NativeInterop.cs`)
- [x] Implement FlaUI + UIA3 automation engine (`FlaUiAutomation.cs`)
- [x] Fix compilation issues and verify clean build
- [x] Add project reference and write unit tests for C# core models, key parsing, and selectors
- [x] Verify unit tests pass (12/12 passed)

## Phase 2: Python Tooling & CLI Integration (`AI/tools/ghosthand`)
- [x] Create `AI/tools/ghosthand/__init__.py`
- [x] Implement `errors.py` with Python error types matching C# ErrorCodes
- [x] Implement `models.py` with typed Pydantic/dataclass structures
- [x] Implement `client.py` wrapping FlaUI CLI subprocess (`flaui.exe`)
- [x] Implement session management tools (`session_attach`, `session_status`, `session_end`)
- [x] Implement window inspection tools (`window_list`, `window_focus`, `window_close`)
- [x] Implement semantic observation tools (`ui_observe`, `ui_find`, `ui_get_properties`)
- [x] Implement action tools (`app_launch`, `ui_click`, `ui_type`, `ui_set_value`, `ui_keys`)
- [x] Implement `register.py` exposing `get_ghosthand_tools()`
- [x] Register GhostHand tools in `AI/tools/__init__.py`
- [x] Write Python unit tests for GhostHand tools (5/5 passed)

## Phase 3: Interactive Terminal Agent & Qwen Integration (`AI/main.py`)
- [x] Create `AI/main.py` terminal chat loop
- [x] Implement OpenAI-compatible client for local llama-server (`http://127.0.0.1:8080/v1`)
- [x] Implement tool calling loop handling both native `tool_calls` and JSON tool calls
- [x] Create automation system prompt for Qwen Windows workflows
- [x] Add unit test suite for main agent runner (`AI/tests/test_main.py`)
- [x] Verify execution and update TODO list (7/7 Python tests passed)

## Active Session State & Discovery Architecture
- [x] Explicit active session management in `GhostHandClient` to eliminate "Multiple session files found" error
- [x] Multi-candidate app discovery in `app_launch` for modern/packaged apps (Calculator, Notepad, VS Code)
- [x] State-aware thrash prevention in `main.py` resetting on session changes
- [x] System prompt recovery guidelines prohibiting blind repeat calls
- [x] Verify full test suites (12 C# tests + 7 Python tests = 19 passed)

## Phase 4: Session Isolation, Registry Routing & Calculator Semantic Resolution
- [x] BUG 1 Fix: Strict pre-launch PID recording and process validation in `app_launch`
  - [x] Reject unrelated existing session files (e.g., `chrome.session.json`) when launching `notepad.exe`
  - [x] Enforce process whitelist and validate `ApplicationFrameHost` window titles for Calculator
  - [x] Explicit per-application session files (`notepad.session.json`, `calculator.session.json`)
  - [x] Return `LAUNCH_VALIDATION_FAILED` (success=false) instead of false success on mismatch
- [x] BUG 2 Fix: ToolRegistry dispatch parameter collision resolved
  - [x] Renamed routing parameter in `ToolRegistry.execute(self, tool_name: str, **kwargs)`
  - [x] Allowed `ui_find(control_type="Button", name="2")` without argument collision
- [x] BUG 3 Fix: Calculator semantic lookup & alias mapping in `ui_find`
  - [x] Added `SEMANTIC_ALIASES` mapping digits (`0`-`9`) and operators (`+`, `-`, `*`, `/`, `=`, `.`) to UIA automation IDs (`num2Button`, `plusButton`, `equalButton`, etc.) and canonical English names (`Two`, `Plus`, `Equals`, etc.)
  - [x] Added transparent fallback for editor controls (`Edit` <-> `Document`)
  - [x] Eliminated raw element ID guessing by Qwen
- [x] Regression Test Suite (`AI/tests/test_regression.py`)
  - [x] Verified 12 regression test cases covering session isolation, registry dispatch, semantic lookup, and anti-thrashing
  - [x] 17/17 Python tests passing, 12/12 C# tests passing (29/29 total tests passing)

## Phase 5: Web View & `app.py` Server
- [x] Pocket AI Web UI Redesign (`AI/web/`):
  - [x] Complete brand re-theming to Pocket AI (SVG logo, wordmark, page titles, metadata)
  - [x] Removed unwanted Colibri engine workspaces (`brio`, `brain`, `profiling`)
  - [x] Streamlined Settings tabs: General, Connection, and GhostHand Automation tools
  - [x] Configured Windows automation prompt suggestions (Notepad, Calculator, Window Inspection)
  - [x] Built optimized distribution bundle (`AI/web/dist`) with Vite + TailwindCSS
- [x] Pocket AI Web Server (`AI/app.py`):
  - [x] Serves SPA frontend from `AI/web/dist` on port 8000 with proper MIME types
  - [x] `/health` and `/v1/models` endpoints for Pocket AI engine discovery
  - [x] `/api/tools` exposing all 14 GhostHand tool schemas
  - [x] Real-time streaming `/v1/chat/completions` with SSE (Server-Sent Events) orchestrating Qwen + GhostHand tool loop
- [x] Test Coverage & Verification:
  - [x] Added `AI/tests/test_app.py` verifying endpoints, static serving, and SSE streaming
  - [x] 22/22 Python tests passing, 12/12 C# tests passing (34/34 total tests passing)

## Documentation & Cleanup
- [x] Create and maintain documentation in `docs/ghosthand/` (`architecture.md`, `tools.md`, `capabilities.md`)
- [x] Keep documentation and task list synchronized

