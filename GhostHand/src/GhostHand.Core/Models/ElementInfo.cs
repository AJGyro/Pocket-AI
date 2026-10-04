namespace GhostHand.Core.Models;

/// <summary>
/// Canonical semantic representation of a Windows UI element.
/// This is what GhostHand exposes to the agent — never raw FlaUI objects.
/// </summary>
public class ElementInfo
{
    /// <summary>Session-scoped opaque identifier. Valid only within the current session window.</summary>
    public required string ElementId { get; init; }

    /// <summary>Human-readable name (UIA Name property).</summary>
    public string? Name { get; init; }

    /// <summary>Stable automation identifier (UIA AutomationId property). Preferred selector.</summary>
    public string? AutomationId { get; init; }

    /// <summary>UIA control type (e.g. "Button", "Document", "MenuItem").</summary>
    public required string ControlType { get; init; }

    /// <summary>Win32 class name. Fragile — avoid using as primary selector.</summary>
    public string? ClassName { get; init; }

    /// <summary>Whether the element is enabled for interaction.</summary>
    public bool Enabled { get; init; }

    /// <summary>Whether the element is currently visible (not offscreen).</summary>
    public bool Visible { get; init; }

    /// <summary>Whether the element is rendered offscreen (virtualized or scrolled out).</summary>
    public bool Offscreen { get; init; }

    /// <summary>Bounding rectangle of the element. Null if not determinable.</summary>
    public BoundsInfo? Bounds { get; init; }

    /// <summary>List of supported UIA control pattern names (e.g. "Invoke", "Value", "Text").</summary>
    public IReadOnlyList<string> Patterns { get; init; } = [];

    /// <summary>Selector quality classification for this element.</summary>
    public SelectorQuality SelectorQuality { get; init; }

    /// <summary>Direct child elements — populated only in detailed observation mode.</summary>
    public IReadOnlyList<ElementInfo>? Children { get; init; }

    /// <summary>Help text from the UIA HelpText property, if available.</summary>
    public string? HelpText { get; init; }
}

/// <summary>Bounding rectangle of a UI element in screen coordinates.</summary>
public record BoundsInfo(double X, double Y, double Width, double Height);

/// <summary>
/// Selector quality rating — how reliably a selector can re-find this element.
/// </summary>
public enum SelectorQuality
{
    /// <summary>AutomationId present — most stable, use as primary selector.</summary>
    Stable,

    /// <summary>Name + ControlType combination — good but name can change on localization.</summary>
    Acceptable,

    /// <summary>ClassName-based — fragile, may change between app versions.</summary>
    Fragile,

    /// <summary>No usable selector properties — cannot reliably re-find this element.</summary>
    Unresolvable,
}

/// <summary>
/// Level of detail for UI observation. Controls how much data is sent to the agent.
/// Use Minimal/Normal to conserve model context. Use Detailed only when required.
/// </summary>
public enum ObservationLevel
{
    /// <summary>Window + top-level controls, names, control types only.</summary>
    Minimal,

    /// <summary>Minimal + automation IDs, enabled/offscreen states, supported patterns.</summary>
    Normal,

    /// <summary>Normal + properties, children, bounds, pattern-specific information.</summary>
    Detailed,
}
