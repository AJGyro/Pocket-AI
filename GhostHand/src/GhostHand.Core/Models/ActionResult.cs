namespace GhostHand.Core.Models;

/// <summary>
/// Universal action result wrapping success/failure for any GhostHand operation.
/// Includes structured verification information so the agent knows what was confirmed.
/// </summary>
public class ActionResult
{
    public bool Success { get; private init; }
    public string Action { get; private init; }
    public ElementTarget? Target { get; private init; }
    public ExecutionInfo? Execution { get; private init; }
    public VerificationInfo? Verification { get; private init; }
    public GhostHandError? Error { get; private init; }

    private ActionResult(string action)
    {
        Action = action;
    }

    public static ActionResult Ok(
        string action,
        ElementTarget? target = null,
        ExecutionInfo? execution = null,
        VerificationInfo? verification = null)
    {
        return new ActionResult(action)
        {
            Success = true,
            Target = target,
            Execution = execution,
            Verification = verification,
        };
    }

    public static ActionResult Fail(string action, GhostHandError error, ElementTarget? target = null)
    {
        return new ActionResult(action)
        {
            Success = false,
            Target = target,
            Error = error,
        };
    }
}

/// <summary>Identifies the target element involved in an action.</summary>
public record ElementTarget(string ElementId, string? Name = null, string? ControlType = null);

/// <summary>Describes how an action was executed.</summary>
public record ExecutionInfo(string Method, long DurationMs);

/// <summary>Result of post-action verification.</summary>
public record VerificationInfo(bool Attempted, bool Success, string? Method, string? Detail = null)
{
    public static VerificationInfo NotAttempted() => new(false, false, null);
    public static VerificationInfo Passed(string method, string? detail = null) => new(true, true, method, detail);
    public static VerificationInfo Failed(string method, string? detail = null) => new(true, false, method, detail);
}
