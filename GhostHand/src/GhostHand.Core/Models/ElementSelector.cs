namespace GhostHand.Core.Models;

/// <summary>
/// Semantic selector for finding a UI element. All fields are optional; at least one must be provided.
/// Priority order: AutomationId > Name+ControlType > Name > ControlType+ClassName > ClassName
/// </summary>
public class ElementSelector
{
    /// <summary>UIA AutomationId — most stable, highest priority.</summary>
    public string? AutomationId { get; init; }

    /// <summary>UIA Name — human-readable label of the element.</summary>
    public string? Name { get; init; }

    /// <summary>UIA ControlType — e.g. "Button", "Document", "MenuItem", "CheckBox".</summary>
    public string? ControlType { get; init; }

    /// <summary>Win32 ClassName — fragile, lowest priority.</summary>
    public string? ClassName { get; init; }

    /// <summary>
    /// Optional: scope the search to within a specific window handle.
    /// If null, searches within the session's main window.
    /// </summary>
    public string? WindowHandle { get; init; }

    /// <summary>Timeout in milliseconds for element discovery. Default: 10000ms.</summary>
    public int TimeoutMs { get; init; } = 10_000;

    public bool IsEmpty =>
        string.IsNullOrEmpty(AutomationId) &&
        string.IsNullOrEmpty(Name) &&
        string.IsNullOrEmpty(ControlType) &&
        string.IsNullOrEmpty(ClassName);

    public override string ToString()
    {
        var parts = new List<string>();
        if (!string.IsNullOrEmpty(AutomationId)) parts.Add($"automation_id='{AutomationId}'");
        if (!string.IsNullOrEmpty(Name)) parts.Add($"name='{Name}'");
        if (!string.IsNullOrEmpty(ControlType)) parts.Add($"control_type='{ControlType}'");
        if (!string.IsNullOrEmpty(ClassName)) parts.Add($"class_name='{ClassName}'");
        return parts.Count > 0 ? string.Join(", ", parts) : "(empty selector)";
    }
}
