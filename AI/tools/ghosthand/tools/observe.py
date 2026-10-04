from typing import Any, Dict, List, Optional
from ..client import GhostHandClient
from ...base import BaseTool

def _flatten_and_filter_tree(node: Dict[str, Any], level: str = "normal", max_count: int = 150) -> List[Dict[str, Any]]:
    results = []
    stack = [node]

    interactive_types = {
        "Button", "Edit", "Document", "CheckBox", "RadioButton",
        "ComboBox", "MenuItem", "Hyperlink", "TabItem", "TreeItem",
        "ListItem", "ScrollBar", "Slider", "Custom", "Window"
    }

    while stack and len(results) < max_count:
        curr = stack.pop(0)

        ctype = curr.get("controlType") or curr.get("control_type") or curr.get("type") or ""
        name = curr.get("name") or curr.get("Name") or ""
        aid = curr.get("automationId") or curr.get("automation_id") or curr.get("aid") or ""
        el_id = curr.get("elementId") or curr.get("element_id") or curr.get("id")
        cname = curr.get("className") or curr.get("class_name") or curr.get("class") or ""

        include = False
        if el_id:
            if level == "minimal":
                include = (ctype in interactive_types and bool(name or aid)) or ctype in {"Document", "Edit", "Button"}
            elif level == "normal":
                include = (ctype != "Pane") or bool(name or aid)
            else:
                include = True

        if include:
            results.append({
                "id": el_id,
                "name": name,
                "control_type": ctype,
                "automation_id": aid,
                "class_name": cname,
                "bounds": curr.get("bounds") or curr.get("Bounds"),
                "is_enabled": curr.get("isEnabled", curr.get("is_enabled", True)),
                "is_offscreen": curr.get("isOffscreen", curr.get("is_offscreen", False)),
                "value": curr.get("value"),
            })

        children = curr.get("children") or curr.get("Children") or []
        stack.extend(children)

    return results

class UiObserveTool(BaseTool):
    name = "ui_observe"
    description = "Observe UI elements in the active window. Returns a structured semantic list of controls with their 'id', 'name', 'control_type', and 'automation_id'."
    parameters = {
        "type": "object",
        "properties": {
            "depth": {
                "type": "integer",
                "description": "Tree exploration depth (1-5, default 3).",
                "default": 3,
            },
            "level": {
                "type": "string",
                "description": "Detail level: 'minimal' (interactive controls only), 'normal' (standard hierarchy, recommended), or 'detailed'.",
                "enum": ["minimal", "normal", "detailed"],
                "default": "normal",
            },
            "root_id": {
                "type": "string",
                "description": "Element ID to scope observation to. Omit for main window.",
            },
            "window_handle": {
                "type": "string",
                "description": "Hex window handle from window_list to observe.",
            },
        },
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(
        self,
        depth: int = 3,
        level: str = "normal",
        root_id: Optional[str] = None,
        window_handle: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        raw = self.client.elem_tree(depth=depth, root_id=root_id, window_handle=window_handle)
        if not raw.get("success", False) and "children" not in raw and "root" not in raw and "Root" not in raw:
            return raw

        cap_map = {"minimal": 50, "normal": 150, "detailed": 300}
        max_items = cap_map.get(level, 150)

        tree_root = raw.get("root") or raw.get("Root") or raw
        elements = _flatten_and_filter_tree(tree_root, level=level, max_count=max_items)

        return {
            "success": True,
            "observation_level": level,
            "element_count": len(elements),
            "truncated": len(elements) >= max_items,
            "elements": elements,
        }

SEMANTIC_ALIASES = {
    "0": {"names": ["Zero", "0"], "aids": ["num0Button"]},
    "1": {"names": ["One", "1"], "aids": ["num1Button"]},
    "2": {"names": ["Two", "2"], "aids": ["num2Button"]},
    "3": {"names": ["Three", "3"], "aids": ["num3Button"]},
    "4": {"names": ["Four", "4"], "aids": ["num4Button"]},
    "5": {"names": ["Five", "5"], "aids": ["num5Button"]},
    "6": {"names": ["Six", "6"], "aids": ["num6Button"]},
    "7": {"names": ["Seven", "7"], "aids": ["num7Button"]},
    "8": {"names": ["Eight", "8"], "aids": ["num8Button"]},
    "9": {"names": ["Nine", "9"], "aids": ["num9Button"]},
    "+": {"names": ["Plus", "+", "Add"], "aids": ["plusButton"]},
    "-": {"names": ["Minus", "-", "Subtract"], "aids": ["minusButton"]},
    "*": {"names": ["Multiply by", "Multiply", "*", "x"], "aids": ["multiplyButton"]},
    "/": {"names": ["Divide by", "Divide", "/"], "aids": ["divideButton"]},
    "=": {"names": ["Equals", "Equal", "="], "aids": ["equalButton"]},
    ".": {"names": ["Decimal separator", "."], "aids": ["decimalSeparatorButton"]},
}

class UiFindTool(BaseTool):
    name = "ui_find"
    description = "Find a specific UI element using semantic properties (automation_id, name, control_type, class_name)."
    parameters = {
        "type": "object",
        "properties": {
            "automation_id": {
                "type": "string",
                "description": "UIA AutomationId (preferred, most stable).",
            },
            "name": {
                "type": "string",
                "description": "Element text name/label.",
            },
            "control_type": {
                "type": "string",
                "description": "UIA ControlType (e.g. 'Button', 'Edit', 'Document', 'ComboBox').",
            },
            "class_name": {
                "type": "string",
                "description": "Class name (e.g. 'TextBox').",
            },
            "timeout_ms": {
                "type": "integer",
                "description": "Discovery timeout in milliseconds (default 10000).",
                "default": 10000,
            },
            "window_handle": {
                "type": "string",
                "description": "Scope search to a specific window hex handle.",
            },
        },
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(
        self,
        automation_id: Optional[str] = None,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        class_name: Optional[str] = None,
        timeout_ms: int = 10000,
        window_handle: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        res = self.client.elem_find(
            aid=automation_id,
            name=name,
            control_type=control_type,
            class_name=class_name,
            timeout_ms=timeout_ms,
            window_handle=window_handle,
        )

        # Fallback 1: Semantic aliases for common symbols and digit buttons (e.g. '2' -> 'num2Button' / 'Two')
        if not res.get("success") and name and name in SEMANTIC_ALIASES:
            alias_info = SEMANTIC_ALIASES[name]
            for aid in alias_info.get("aids", []):
                alias_res = self.client.elem_find(
                    aid=aid,
                    control_type=control_type,
                    class_name=class_name,
                    timeout_ms=min(2000, timeout_ms),
                    window_handle=window_handle,
                )
                if alias_res.get("success"):
                    return alias_res

            for alt_name in alias_info.get("names", []):
                if alt_name == name:
                    continue
                alias_res = self.client.elem_find(
                    aid=automation_id,
                    name=alt_name,
                    control_type=control_type,
                    class_name=class_name,
                    timeout_ms=min(2000, timeout_ms),
                    window_handle=window_handle,
                )
                if alias_res.get("success"):
                    return alias_res

        # Fallback 2: Aliases for text fields (Edit <-> Document)
        if not res.get("success") and control_type:
            ctype_lower = control_type.lower()
            alias = None
            if ctype_lower in ("edit", "textbox"):
                alias = "Document"
            elif ctype_lower == "document":
                alias = "Edit"

            if alias:
                alias_res = self.client.elem_find(
                    aid=automation_id,
                    name=name,
                    control_type=alias,
                    class_name=class_name,
                    timeout_ms=min(3000, timeout_ms),
                    window_handle=window_handle,
                )
                if alias_res.get("success"):
                    return alias_res

        return res

class UiGetPropertiesTool(BaseTool):
    name = "ui_get_properties"
    description = "Get detailed UIA properties and supported patterns for an element by ID."
    parameters = {
        "type": "object",
        "properties": {
            "element_id": {
                "type": "string",
                "description": "Element ID obtained from ui_find or ui_observe.",
            },
        },
        "required": ["element_id"],
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, element_id: str, **kwargs) -> Dict[str, Any]:
        return self.client.elem_props(element_id=element_id)
