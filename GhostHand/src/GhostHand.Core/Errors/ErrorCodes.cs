namespace GhostHand.Core.Errors;

/// <summary>
/// Machine-readable error code taxonomy for GhostHand operations.
/// Every error returned to the agent must carry one of these codes.
/// </summary>
public enum ErrorCode
{
    // Element resolution
    ELEMENT_NOT_FOUND,
    ELEMENT_STALE,
    ELEMENT_DISABLED,
    ELEMENT_OFFSCREEN,
    INVALID_SELECTOR,

    // Pattern / capability
    PATTERN_NOT_SUPPORTED,
    UNSUPPORTED_OPERATION,

    // Argument / input
    INVALID_ARGUMENT,
    VALUE_OUT_OF_RANGE,

    // Window / session
    WINDOW_NOT_FOUND,
    SESSION_NOT_FOUND,
    SESSION_EXPIRED,

    // Action failures
    ACTION_FAILED,
    VERIFICATION_FAILED,
    TIMEOUT,

    // Application state
    APPLICATION_BUSY,
    APPLICATION_CLOSED,

    // System / security
    PERMISSION_DENIED,

    // Recovery
    RECOVERY_FAILED,

    // Unknown
    UNKNOWN,
}
