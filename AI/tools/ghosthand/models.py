from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional
from .errors import ErrorCode

@dataclass
class BoundsInfo:
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

@dataclass
class ElementInfo:
    id: str
    name: Optional[str] = None
    control_type: Optional[str] = None
    automation_id: Optional[str] = None
    class_name: Optional[str] = None
    bounds: Optional[BoundsInfo] = None
    is_enabled: bool = True
    is_offscreen: bool = False
    is_keyboard_focusable: bool = False
    supported_patterns: List[str] = field(default_factory=list)
    value: Optional[str] = None
    toggle_state: Optional[str] = None
    children: List["ElementInfo"] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class WindowInfo:
    handle: str
    title: str
    process_id: int
    process_name: Optional[str] = None
    is_minimized: bool = False
    is_maximized: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ObservationResult:
    window: Optional[WindowInfo]
    elements: List[ElementInfo]
    total_count: int
    truncated: bool = False
    observation_level: str = "normal"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window": self.window.to_dict() if self.window else None,
            "elements": [e.to_dict() for e in self.elements],
            "total_count": self.total_count,
            "truncated": self.truncated,
            "observation_level": self.observation_level,
        }

@dataclass
class ActionResult:
    success: bool
    action: str
    target: Optional[Dict[str, Any]] = None
    execution: Optional[Dict[str, Any]] = None
    verification: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
