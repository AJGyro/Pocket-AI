using GhostHand.Core.Errors;

namespace GhostHand.Core.Models;

/// <summary>
/// Structured error object returned by all GhostHand operations on failure.
/// Provides machine-readable codes so the agent can apply appropriate recovery strategies.
/// </summary>
public record GhostHandError(
    ErrorCode Code,
    string Message,
    bool Recoverable,
    string? Detail = null)
{
    public static GhostHandError ElementNotFound(string selector) =>
        new(ErrorCode.ELEMENT_NOT_FOUND,
            $"Element not found using selector: {selector}",
            Recoverable: true);

    public static GhostHandError ElementStale(string elementId) =>
        new(ErrorCode.ELEMENT_STALE,
            $"Element '{elementId}' is stale. Re-find the element before retrying.",
            Recoverable: true);

    public static GhostHandError ElementDisabled(string elementId) =>
        new(ErrorCode.ELEMENT_DISABLED,
            $"Element '{elementId}' is disabled and cannot be interacted with.",
            Recoverable: false);

    public static GhostHandError ElementOffscreen(string elementId) =>
        new(ErrorCode.ELEMENT_OFFSCREEN,
            $"Element '{elementId}' is offscreen. Use ui_scroll_into_view first.",
            Recoverable: true);

    public static GhostHandError PatternNotSupported(string elementId, string patternName) =>
        new(ErrorCode.PATTERN_NOT_SUPPORTED,
            $"Element '{elementId}' does not support the {patternName} pattern.",
            Recoverable: false);

    public static GhostHandError InvalidArgument(string paramName, string reason) =>
        new(ErrorCode.INVALID_ARGUMENT,
            $"Invalid argument '{paramName}': {reason}",
            Recoverable: false);

    public static GhostHandError ValueOutOfRange(string elementId, double requested, double min, double max) =>
        new(ErrorCode.VALUE_OUT_OF_RANGE,
            $"Requested value {requested} is outside the valid range [{min}, {max}] for element '{elementId}'.",
            Recoverable: false);

    public static GhostHandError WindowNotFound(string title) =>
        new(ErrorCode.WINDOW_NOT_FOUND,
            $"No window found matching '{title}'. Use window_list to see available windows.",
            Recoverable: true);

    public static GhostHandError SessionNotFound(string sessionId) =>
        new(ErrorCode.SESSION_NOT_FOUND,
            $"Session '{sessionId}' not found. Use session_attach to create a session.",
            Recoverable: true);

    public static GhostHandError SessionExpired(string sessionId) =>
        new(ErrorCode.SESSION_EXPIRED,
            $"Session '{sessionId}' has expired (process no longer running). Use session_attach to reattach.",
            Recoverable: true);

    public static GhostHandError ActionFailed(string action, string reason) =>
        new(ErrorCode.ACTION_FAILED,
            $"Action '{action}' failed: {reason}",
            Recoverable: true);

    public static GhostHandError VerificationFailed(string action, string expected, string? actual) =>
        new(ErrorCode.VERIFICATION_FAILED,
            $"Verification failed for '{action}'. Expected: {expected}. Actual: {actual ?? "unknown"}.",
            Recoverable: true);

    public static GhostHandError Timeout(string operation, int timeoutMs) =>
        new(ErrorCode.TIMEOUT,
            $"Operation '{operation}' timed out after {timeoutMs}ms.",
            Recoverable: true);

    public static GhostHandError InvalidSelector(string reason) =>
        new(ErrorCode.INVALID_SELECTOR,
            $"Invalid selector: {reason}",
            Recoverable: false);

    public static GhostHandError Unknown(string message) =>
        new(ErrorCode.UNKNOWN, message, Recoverable: false);
}
