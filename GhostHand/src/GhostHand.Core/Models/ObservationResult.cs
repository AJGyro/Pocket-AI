namespace GhostHand.Core.Models;

/// <summary>
/// Structured observation of the current UI state at a chosen level of detail.
/// This is what ui_observe returns to the agent.
/// </summary>
public class ObservationResult
{
    public required WindowSummary Window { get; init; }
    public required IReadOnlyList<ElementInfo> Elements { get; init; }
    public ObservationLevel Level { get; init; }
    public string SessionId { get; init; } = string.Empty;
    public DateTimeOffset ObservedAt { get; init; } = DateTimeOffset.UtcNow;
}

/// <summary>Summary information about the observed window.</summary>
public record WindowSummary(
    string? Title,
    string? ControlType,
    string? Handle,
    bool IsModal = false,
    bool IsTopmost = false);

/// <summary>
/// Detected UIA patterns and their capabilities for an element.
/// Allows the agent to determine which actions are semantically valid.
/// </summary>
public class CapabilityInfo
{
    public required string ElementId { get; init; }
    public IReadOnlyList<string> SupportedPatterns { get; init; } = [];

    // Per-pattern capability details
    public bool CanInvoke => SupportedPatterns.Contains("Invoke");
    public bool CanSetValue => SupportedPatterns.Contains("Value");
    public bool CanGetText => SupportedPatterns.Contains("Text");
    public bool CanToggle => SupportedPatterns.Contains("Toggle");
    public bool CanExpandCollapse => SupportedPatterns.Contains("ExpandCollapse");
    public bool CanScroll => SupportedPatterns.Contains("Scroll");
    public bool CanScrollItem => SupportedPatterns.Contains("ScrollItem");
    public bool CanSelect => SupportedPatterns.Contains("Selection");
    public bool CanSelectItem => SupportedPatterns.Contains("SelectionItem");
    public bool CanRangeValue => SupportedPatterns.Contains("RangeValue");
    public bool CanGrid => SupportedPatterns.Contains("Grid");
    public bool CanGridItem => SupportedPatterns.Contains("GridItem");
    public bool CanTable => SupportedPatterns.Contains("Table");
    public bool CanTableItem => SupportedPatterns.Contains("TableItem");
    public bool CanMultipleView => SupportedPatterns.Contains("MultipleView");
    public bool CanTransform => SupportedPatterns.Contains("Transform");
    public bool CanDock => SupportedPatterns.Contains("Dock");
    public bool CanWindow => SupportedPatterns.Contains("Window");

    /// <summary>
    /// Return the recommended action method for setting text on this element.
    /// </summary>
    public string RecommendedTextInputMethod =>
        CanSetValue ? "SetValue" :
        CanGetText ? "TypeText" :
        "KeyboardFallback";

    /// <summary>
    /// Return the recommended action method for activating a button/control.
    /// </summary>
    public string RecommendedActivationMethod =>
        CanInvoke ? "Invoke" :
        CanToggle ? "Toggle" :
        CanExpandCollapse ? "ExpandCollapse" :
        "SemanticClick";
}
