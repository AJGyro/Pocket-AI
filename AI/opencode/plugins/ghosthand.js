import { execFile } from "child_process"
import { promisify } from "util"
import path from "path"
import fs from "fs"

const execFileAsync = promisify(execFile)

// Load tool helper from @opencode-ai/plugin if available (inside OpenCode runtime)
let tool
try {
  const pluginMod = await import("@opencode-ai/plugin")
  tool = pluginMod.tool
} catch {
  tool = (def) => def
  tool.schema = {
    string: () => ({
      describe: (d) => ({ ...tool.schema.string(), description: d }),
      optional: () => ({ ...tool.schema.string(), isOptional: true }),
    }),
    number: () => ({
      describe: (d) => ({ ...tool.schema.number(), description: d }),
      optional: () => ({ ...tool.schema.number(), isOptional: true }),
    }),
    enum: (vals) => ({
      describe: (d) => ({ ...tool.schema.enum(vals), description: d }),
      optional: () => ({ ...tool.schema.enum(vals), isOptional: true }),
    }),
  }
}

// Resolve Python executable and GhostHand bridge path
function resolvePythonPath() {
  const candidates = [
    "E:\\Python\\python.exe",
    path.resolve(process.cwd(), "../Python/python.exe"),
    path.resolve(process.cwd(), "Python/python.exe"),
    process.env.PYTHON,
    "python",
  ]
  for (const c of candidates) {
    if (c && fs.existsSync(c)) return c
  }
  return "python"
}

function resolveBridgePath() {
  const candidates = [
    "E:\\AI\\tools\\ghosthand_bridge.py",
    path.resolve(process.cwd(), "tools/ghosthand_bridge.py"),
    path.resolve(process.cwd(), "AI/tools/ghosthand_bridge.py"),
  ]
  for (const c of candidates) {
    if (c && fs.existsSync(c)) return c
  }
  return "E:\\AI\\tools\\ghosthand_bridge.py"
}

const PYTHON_PATH = resolvePythonPath()
const BRIDGE_PATH = resolveBridgePath()

async function runGhostHand(action, params = {}) {
  try {
    const { stdout, stderr } = await execFileAsync(PYTHON_PATH, [BRIDGE_PATH, action, JSON.stringify(params)], {
      windowsHide: true,
      encoding: "utf-8",
      maxBuffer: 10 * 1024 * 1024,
      timeout: 45000,
    })

    const output = (stdout || "").trim()
    if (!output) {
      if (stderr) {
        return JSON.stringify({
          success: false,
          error_code: "EXECUTION_ERROR",
          message: stderr.trim(),
          recoverable: true,
          recovery_hint: "Verify Python environment and GhostHand bridge status.",
        }, null, 2)
      }
      return JSON.stringify({ success: true })
    }

    try {
      const parsed = JSON.parse(output)
      return JSON.stringify(parsed, null, 2)
    } catch {
      return output
    }
  } catch (err) {
    const stdout = err.stdout ? err.stdout.trim() : ""
    if (stdout) {
      try {
        const parsed = JSON.parse(stdout)
        return JSON.stringify(parsed, null, 2)
      } catch {}
    }
    return JSON.stringify({
      success: false,
      error_code: "BRIDGE_ERROR",
      message: err.message || String(err),
      recoverable: true,
      recovery_hint: "Check ghosthand_session_status and verify the Windows application is open.",
    }, null, 2)
  }
}

// 1. App Launch
const app_launch = tool({
  description:
    "Launch a Windows desktop application (e.g. 'notepad.exe', 'calc.exe') and automatically initialize and attach an active GhostHand automation session. Step 1 of the deterministic automation workflow. Do NOT call session_attach immediately after a successful app_launch.",
  args: {
    app_path: tool.schema.string().describe("Application executable name or full path (e.g. 'notepad.exe', 'calc.exe')."),
    args: tool.schema.string().optional().describe("Optional command-line arguments to pass to the executable."),
    wait_title: tool.schema.string().optional().describe("Optional window title text to wait for."),
    timeout_ms: tool.schema.number().optional().describe("Timeout in milliseconds (default 15000)."),
  },
  async execute(args) {
    return await runGhostHand("app_launch", args)
  },
})

// 2. Session Attach
const session_attach = tool({
  description:
    "Attach GhostHand to an already running Windows application by process name, PID, or window title. Use this only when the application is already running and was not started via app_launch.",
  args: {
    process_name: tool.schema.string().optional().describe("Process name without .exe (e.g. 'notepad', 'calculatorapp')."),
    pid: tool.schema.number().optional().describe("Process ID to attach to."),
    window_title: tool.schema.string().optional().describe("Main window title text to match (e.g. 'Untitled - Notepad')."),
    timeout_ms: tool.schema.number().optional().describe("Timeout in milliseconds (default 10000)."),
  },
  async execute(args) {
    return await runGhostHand("session_attach", args)
  },
})

// 3. Session Status
const session_status = tool({
  description:
    "Check the status of the active GhostHand session (whether the process is alive, window handle is valid, cached elements).",
  args: {},
  async execute(args) {
    return await runGhostHand("session_status", args)
  },
})

// 4. Session End
const session_end = tool({
  description:
    "End the active GhostHand automation session and clean up cached handles and session files.",
  args: {},
  async execute(args) {
    return await runGhostHand("session_end", args)
  },
})

// 5. Window List
const window_list = tool({
  description:
    "List all top-level windows belonging to the application in the active GhostHand session.",
  args: {},
  async execute(args) {
    return await runGhostHand("window_list", args)
  },
})

// 6. Window Focus
const window_focus = tool({
  description:
    "Bring a specific window to the foreground by its hex handle (obtained from window_list).",
  args: {
    window_handle: tool.schema.string().describe("Hex window handle (e.g. '0x1A2B') from window_list."),
  },
  async execute(args) {
    return await runGhostHand("window_focus", args)
  },
})

// 7. Window Close
const window_close = tool({
  description:
    "Close a specific window by its hex handle.",
  args: {
    window_handle: tool.schema.string().describe("Hex window handle to close."),
  },
  async execute(args) {
    return await runGhostHand("window_close", args)
  },
})

// 8. UI Observe (Step 2 in deterministic workflow)
const ui_observe = tool({
  description:
    "Observe UI elements in the active window. Mandatory Step 2 of the deterministic workflow: ALWAYS call ui_observe first to discover element IDs, names, and control types before attempting to click or type. Returns a structured semantic tree with element IDs.",
  args: {
    depth: tool.schema.number().optional().describe("Tree exploration depth (1-5, default 3)."),
    level: tool.schema.enum(["minimal", "normal", "detailed"]).optional().describe("Detail level: 'minimal' (interactive controls only), 'normal' (standard hierarchy, recommended), or 'detailed'."),
    root_id: tool.schema.string().optional().describe("Element ID to scope observation to. Omit for main window."),
    window_handle: tool.schema.string().optional().describe("Hex window handle from window_list to observe."),
  },
  async execute(args) {
    return await runGhostHand("ui_observe", args)
  },
})

// 9. UI Find
const ui_find = tool({
  description:
    "Find a specific UI element using semantic UIA properties (automation_id, name, control_type, class_name). Returns element ID.",
  args: {
    automation_id: tool.schema.string().optional().describe("UIA AutomationId (preferred, most stable identifier)."),
    name: tool.schema.string().optional().describe("Element label / name text."),
    control_type: tool.schema.string().optional().describe("UIA ControlType (e.g. 'Button', 'Edit', 'Document', 'ComboBox')."),
    class_name: tool.schema.string().optional().describe("Window/control class name."),
    timeout_ms: tool.schema.number().optional().describe("Discovery timeout in milliseconds (default 10000)."),
    window_handle: tool.schema.string().optional().describe("Scope search to a specific window hex handle."),
  },
  async execute(args) {
    return await runGhostHand("ui_find", args)
  },
})

// 10. UI Get Properties
const ui_get_properties = tool({
  description:
    "Get detailed UIA properties and supported patterns for an element by ID.",
  args: {
    element_id: tool.schema.string().describe("Element ID obtained from ui_observe or ui_find."),
  },
  async execute(args) {
    return await runGhostHand("ui_get_properties", args)
  },
})

// 11. UI Click
const ui_click = tool({
  description:
    "Click a UI element by ID using its UIA Invoke or Toggle pattern. Never uses mouse coordinates.",
  args: {
    element_id: tool.schema.string().describe("Element ID obtained from ui_observe or ui_find."),
  },
  async execute(args) {
    return await runGhostHand("ui_click", args)
  },
})

// 12. UI Type
const ui_type = tool({
  description:
    "Type text into an editable element using keyboard simulation. Requires an observed element ID.",
  args: {
    element_id: tool.schema.string().describe("Element ID of the text field (obtained from ui_observe or ui_find)."),
    text: tool.schema.string().describe("Text string to type into the element."),
  },
  async execute(args) {
    return await runGhostHand("ui_type", args)
  },
})

// 13. UI Set Value
const ui_set_value = tool({
  description:
    "Set an element's text value directly via UIA ValuePattern (faster and more reliable than typing for text boxes).",
  args: {
    element_id: tool.schema.string().describe("Element ID to set value on."),
    value: tool.schema.string().describe("Value string to set."),
  },
  async execute(args) {
    return await runGhostHand("ui_set_value", args)
  },
})

// 14. UI Keys
const ui_keys = tool({
  description:
    "Send key shortcuts or sequences to a UI element (e.g. 'ctrl+s', 'enter', 'alt+f4', 'tab').",
  args: {
    element_id: tool.schema.string().describe("Element ID to send keys to."),
    keys: tool.schema.string().describe("Key combination string (e.g. 'ctrl+s', 'enter', 'tab')."),
  },
  async execute(args) {
    return await runGhostHand("ui_keys", args)
  },
})

// OpenCode V1 Plugin Export Specification
export default {
  id: "ghosthand",
  async server(input, options) {
    return {
      tool: {
        ghosthand_app_launch: app_launch,
        ghosthand_session_attach: session_attach,
        ghosthand_session_status: session_status,
        ghosthand_session_end: session_end,
        ghosthand_window_list: window_list,
        ghosthand_window_focus: window_focus,
        ghosthand_window_close: window_close,
        ghosthand_ui_observe: ui_observe,
        ghosthand_ui_find: ui_find,
        ghosthand_ui_get_properties: ui_get_properties,
        ghosthand_ui_click: ui_click,
        ghosthand_ui_type: ui_type,
        ghosthand_ui_set_value: ui_set_value,
        ghosthand_ui_keys: ui_keys,
      },
    }
  },
}
