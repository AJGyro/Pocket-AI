"""
GhostHand MCP Serializers.

Provides compact, model-friendly serialization to optimize context window usage.
Never returns giant UI trees or verbose internal debugging objects.
"""

from typing import Any, Dict, List, Optional
from ..errors import ErrorCode, GhostHandException


def serialize_element(elem: Any) -> Dict[str, Any]:
    """Serialize a UI element into a minimal, model-friendly dictionary."""
    if isinstance(elem, dict):
        return {
            "id": elem.get("id") or elem.get("elementId") or elem.get("element_id"),
            "name": elem.get("name") or elem.get("Name") or "",
            "control_type": elem.get("control_type") or elem.get("controlType") or elem.get("type") or "",
            "automation_id": elem.get("automation_id") or elem.get("automationId") or elem.get("aid") or "",
        }
    return {
        "id": getattr(elem, "id", None),
        "name": getattr(elem, "name", "") or "",
        "control_type": getattr(elem, "control_type", "") or "",
        "automation_id": getattr(elem, "automation_id", "") or "",
    }


def serialize_window(win: Any) -> Dict[str, Any]:
    """Serialize a Window into a compact dictionary."""
    if isinstance(win, dict):
        return {
            "handle": win.get("handle") or win.get("mainWindowHandle") or win.get("hexHandle") or "",
            "title": win.get("title") or win.get("mainWindowTitle") or win.get("name") or "",
            "pid": win.get("pid") or win.get("processId") or win.get("process_id"),
            "process_name": win.get("process_name") or win.get("processName") or "",
        }
    return {
        "handle": getattr(win, "handle", ""),
        "title": getattr(win, "title", ""),
        "pid": getattr(win, "process_id", None) or getattr(win, "pid", None),
        "process_name": getattr(win, "process_name", ""),
    }


def serialize_error(
    code: str,
    message: str,
    retryable: bool = True,
    recovery_hint: Optional[str] = None,
    detail: Optional[str] = None,
) -> Dict[str, Any]:
    """Serialize an error into a compact structured dictionary."""
    err_obj = {
        "code": code,
        "message": message,
        "retryable": retryable,
    }
    if recovery_hint:
        err_obj["recovery_hint"] = recovery_hint
    if detail:
        err_obj["detail"] = detail

    return {
        "success": False,
        "error": err_obj,
    }


def serialize_exception(exc: Exception, action: str = "") -> Dict[str, Any]:
    """Convert an exception into a compact structured error."""
    if isinstance(exc, GhostHandException):
        code_str = exc.code.value if hasattr(exc.code, "value") else str(exc.code)
        hint = get_recovery_hint(code_str, exc.message)
        return serialize_error(
            code=code_str,
            message=exc.message,
            retryable=exc.recoverable,
            recovery_hint=hint,
            detail=exc.detail,
        )

    msg = str(exc)
    hint = get_recovery_hint("EXCEPTION", msg)
    return serialize_error(
        code="EXECUTION_FAILED",
        message=msg,
        retryable=True,
        recovery_hint=hint,
    )


def serialize_success(message: str, **kwargs) -> Dict[str, Any]:
    """Format a successful operation result."""
    res = {
        "success": True,
        "message": message,
    }
    for k, v in kwargs.items():
        if v is not None:
            res[k] = v
    return res


def get_recovery_hint(error_code: str, error_msg: str) -> str:
    """Generate concise actionable recovery advice for the LLM."""
    code = (error_code or "").upper()
    msg = (error_msg or "").lower()

    if "not found" in msg or "element" in code:
        return "Call ghosthand_element_find with automation_id or name to verify the element."
    if "session" in msg or "session" in code:
        return "Call ghosthand_window_launch or ghosthand_session_attach before interacting with elements."
    if "window" in msg or "window" in code:
        return "Call ghosthand_window_list to inspect open windows or ghosthand_window_launch to start the application."
    if "timeout" in msg or "timeout" in code:
        return "Operation timed out. Verify the target application is running and responsive."
    if "disabled" in msg or "disabled" in code:
        return "The element is currently disabled in the UI."
    return "Check application state and verify element properties."
