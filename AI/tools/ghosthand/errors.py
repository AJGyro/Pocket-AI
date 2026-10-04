from enum import Enum
from typing import Optional

class ErrorCode(str, Enum):
    ELEMENT_NOT_FOUND = "ELEMENT_NOT_FOUND"
    ELEMENT_STALE = "ELEMENT_STALE"
    ELEMENT_DISABLED = "ELEMENT_DISABLED"
    ELEMENT_OFFSCREEN = "ELEMENT_OFFSCREEN"
    PATTERN_NOT_SUPPORTED = "PATTERN_NOT_SUPPORTED"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    VALUE_OUT_OF_RANGE = "VALUE_OUT_OF_RANGE"
    WINDOW_NOT_FOUND = "WINDOW_NOT_FOUND"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    ACTION_FAILED = "ACTION_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    TIMEOUT = "TIMEOUT"
    INVALID_SELECTOR = "INVALID_SELECTOR"
    UNKNOWN = "UNKNOWN"

class GhostHandException(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        recoverable: bool = True,
        detail: Optional[str] = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.recoverable = recoverable
        self.detail = detail

    def to_dict(self):
        return {
            "code": self.code.value,
            "message": self.message,
            "recoverable": self.recoverable,
            "detail": self.detail,
        }
