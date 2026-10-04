namespace GhostHand.Core.Models;

/// <summary>
/// GhostHand session — maintains state across a multi-step agent task.
/// A session corresponds to one attached Windows application process.
/// </summary>
public class GhostHandSession
{
    /// <summary>Unique session identifier.</summary>
    public string SessionId { get; init; }

    /// <summary>Process ID of the attached application.</summary>
    public int Pid { get; init; }

    /// <summary>Human-readable process name (e.g. "notepad").</summary>
    public string ProcessName { get; init; }

    /// <summary>Main window title at attach time.</summary>
    public string? MainWindowTitle { get; set; }

    /// <summary>Native window handle (hex string) of the main window.</summary>
    public string? MainWindowHandle { get; set; }

    /// <summary>Path to the underlying flaui.exe session file, if using CLI mode.</summary>
    public string? SessionFilePath { get; set; }

    /// <summary>When the session was created.</summary>
    public DateTimeOffset CreatedAt { get; init; } = DateTimeOffset.UtcNow;

    /// <summary>When the session was last used.</summary>
    public DateTimeOffset LastUsedAt { get; set; } = DateTimeOffset.UtcNow;

    /// <summary>Currently focused window handle within this session (may differ from main).</summary>
    public string? ActiveWindowHandle { get; set; }

    /// <summary>
    /// Element cache: session-scoped element IDs mapped to their selector for re-resolution.
    /// This cache is invalidated when a stale element is detected.
    /// </summary>
    public Dictionary<string, ElementSelector> ElementCache { get; } = new();

    /// <summary>Whether this session is still valid (process alive + main window exists).</summary>
    public bool IsAlive { get; set; } = true;

    public GhostHandSession(string sessionId, int pid, string processName)
    {
        SessionId = sessionId;
        Pid = pid;
        ProcessName = processName;
    }

    public void Touch() => LastUsedAt = DateTimeOffset.UtcNow;
}
