using GhostHand.Core.Models;

namespace GhostHand.Core.Abstractions;

/// <summary>
/// Core abstraction for all Windows UI Automation operations in GhostHand.
/// 
/// Implementations:
///   - FlaUiAutomation  — direct FlaUI + UIA3 integration (preferred, in-process)
///   - FlaUiCliAutomation — delegates to flaui.exe subprocess (fallback mode)
/// 
/// This interface ensures the agent layer is completely decoupled from
/// the underlying automation mechanism.
/// </summary>
public interface IGhostHandAutomation : IDisposable
{
    // ─── Session Management ──────────────────────────────────────────────────

    /// <summary>Attach to an existing running application by process name.</summary>
    Task<ActionResult> AttachByNameAsync(string processName, CancellationToken ct = default);

    /// <summary>Attach to an existing running application by PID.</summary>
    Task<ActionResult> AttachByPidAsync(int pid, CancellationToken ct = default);

    /// <summary>Attach to an existing running application by window title substring.</summary>
    Task<ActionResult> AttachByTitleAsync(string titleSubstring, CancellationToken ct = default);

    /// <summary>Check session status: process alive, main window valid, element count.</summary>
    Task<SessionStatusResult> GetSessionStatusAsync(CancellationToken ct = default);

    /// <summary>End the current session without killing the application.</summary>
    Task<ActionResult> EndSessionAsync(CancellationToken ct = default);

    // ─── Observation ─────────────────────────────────────────────────────────

    /// <summary>
    /// Observe the current UI state. Returns a structured, level-filtered observation.
    /// Never dumps a raw 500-element tree to the agent.
    /// </summary>
    Task<ObservationResult> ObserveAsync(
        ObservationLevel level = ObservationLevel.Normal,
        string? windowHandle = null,
        CancellationToken ct = default);

    /// <summary>Find an element using a semantic selector.</summary>
    Task<FindResult> FindElementAsync(
        ElementSelector selector,
        string? parentElementId = null,
        CancellationToken ct = default);

    /// <summary>Get detailed properties of an element by ID.</summary>
    Task<ElementInfo?> GetElementPropertiesAsync(string elementId, CancellationToken ct = default);

    /// <summary>Get the capability information (supported UIA patterns) for an element.</summary>
    Task<CapabilityInfo?> GetCapabilitiesAsync(string elementId, CancellationToken ct = default);

    // ─── Window Management ───────────────────────────────────────────────────

    /// <summary>List all top-level windows belonging to the attached process.</summary>
    Task<WindowListResult> ListWindowsAsync(CancellationToken ct = default);

    /// <summary>Focus (bring to foreground) a window by handle.</summary>
    Task<ActionResult> FocusWindowAsync(string windowHandle, CancellationToken ct = default);

    /// <summary>Close a window by handle (sends WM_CLOSE via Window pattern).</summary>
    Task<ActionResult> CloseWindowAsync(string windowHandle, CancellationToken ct = default);

    /// <summary>Get the visual state of a window (Normal/Minimized/Maximized).</summary>
    Task<WindowStateResult> GetWindowStateAsync(string? windowHandle = null, CancellationToken ct = default);

    /// <summary>Minimize a window.</summary>
    Task<ActionResult> MinimizeWindowAsync(string? windowHandle = null, CancellationToken ct = default);

    /// <summary>Maximize a window.</summary>
    Task<ActionResult> MaximizeWindowAsync(string? windowHandle = null, CancellationToken ct = default);

    /// <summary>Restore a window to normal state.</summary>
    Task<ActionResult> RestoreWindowAsync(string? windowHandle = null, CancellationToken ct = default);

    // ─── Element Actions ─────────────────────────────────────────────────────

    /// <summary>
    /// Invoke an element using InvokePattern. Preferred for buttons, links, menu items.
    /// </summary>
    Task<ActionResult> InvokeAsync(string elementId, CancellationToken ct = default);

    /// <summary>
    /// Click an element semantically.
    /// Prefers InvokePattern, falls back to UIA-aware click.
    /// Does NOT use screen coordinates.
    /// </summary>
    Task<ActionResult> ClickAsync(string elementId, CancellationToken ct = default);

    /// <summary>
    /// Type text into an element.
    /// Prefers ValuePattern.SetValue; falls back to FlaUI keyboard input.
    /// </summary>
    Task<ActionResult> TypeAsync(string elementId, string text, CancellationToken ct = default);

    /// <summary>
    /// Set the value of an element using ValuePattern.
    /// Throws PATTERN_NOT_SUPPORTED if ValuePattern is not available.
    /// </summary>
    Task<ActionResult> SetValueAsync(string elementId, string value, CancellationToken ct = default);

    /// <summary>Get the current value of an element.</summary>
    Task<GetValueResult> GetValueAsync(string elementId, CancellationToken ct = default);

    /// <summary>Get the full text content of an element using TextPattern.</summary>
    Task<GetTextResult> GetTextAsync(string elementId, CancellationToken ct = default);

    /// <summary>Clear the value/text of an element.</summary>
    Task<ActionResult> ClearAsync(string elementId, CancellationToken ct = default);

    /// <summary>Select an item within a container (ComboBox, List, Tab, Tree).</summary>
    Task<ActionResult> SelectAsync(string elementId, string itemName, CancellationToken ct = default);

    /// <summary>Toggle an element using TogglePattern.</summary>
    Task<ToggleResult> ToggleAsync(string elementId, CancellationToken ct = default);

    /// <summary>Get the current toggle/expand state of an element.</summary>
    Task<ElementStateResult> GetStateAsync(string elementId, CancellationToken ct = default);

    /// <summary>Expand an element using ExpandCollapsePattern.</summary>
    Task<ActionResult> ExpandAsync(string elementId, CancellationToken ct = default);

    /// <summary>Collapse an element using ExpandCollapsePattern.</summary>
    Task<ActionResult> CollapseAsync(string elementId, CancellationToken ct = default);

    /// <summary>Send keyboard keys to an element or the active window.</summary>
    Task<ActionResult> SendKeysAsync(string keys, string? elementId = null, CancellationToken ct = default);

    /// <summary>Navigate a menu path semantically (e.g. "File > Save As").</summary>
    Task<ActionResult> NavigateMenuAsync(string menuPath, CancellationToken ct = default);

    /// <summary>Scroll an element using ScrollPattern.</summary>
    Task<ActionResult> ScrollAsync(string elementId, double? horizontal = null, double? vertical = null, CancellationToken ct = default);

    /// <summary>Scroll an element into view using ScrollItemPattern.</summary>
    Task<ActionResult> ScrollIntoViewAsync(string elementId, CancellationToken ct = default);

    /// <summary>Get scroll state of an element.</summary>
    Task<ScrollInfoResult> GetScrollInfoAsync(string elementId, CancellationToken ct = default);

    // ─── Range Controls ──────────────────────────────────────────────────────

    /// <summary>Get the current value and bounds of a RangeValue element (slider, etc.).</summary>
    Task<RangeValueResult> GetRangeAsync(string elementId, CancellationToken ct = default);

    /// <summary>Set the value of a RangeValue element. Validates against min/max.</summary>
    Task<ActionResult> SetRangeAsync(string elementId, double value, CancellationToken ct = default);

    // ─── Grid / Table ────────────────────────────────────────────────────────

    /// <summary>Get grid metadata (row count, column count, headers).</summary>
    Task<GridInfoResult> GetGridInfoAsync(string elementId, CancellationToken ct = default);

    /// <summary>Get the value of a specific grid cell.</summary>
    Task<GridCellResult> GetGridCellAsync(string elementId, int row, int column, CancellationToken ct = default);

    /// <summary>Get the position info of a grid item element.</summary>
    Task<GridItemInfoResult> GetGridItemInfoAsync(string elementId, CancellationToken ct = default);

    /// <summary>Get the header info of a table item element.</summary>
    Task<TableItemInfoResult> GetTableItemInfoAsync(string elementId, CancellationToken ct = default);

    // ─── Structured Controls ─────────────────────────────────────────────────

    /// <summary>Get available views for a MultipleView element.</summary>
    Task<MultipleViewResult> GetViewsAsync(string elementId, CancellationToken ct = default);

    /// <summary>Set the view of a MultipleView element.</summary>
    Task<ActionResult> SetViewAsync(string elementId, int viewId, CancellationToken ct = default);

    /// <summary>Get the dock position of an element.</summary>
    Task<DockPositionResult> GetDockAsync(string elementId, CancellationToken ct = default);

    /// <summary>Set the dock position of an element.</summary>
    Task<ActionResult> SetDockAsync(string elementId, string position, CancellationToken ct = default);

    /// <summary>Apply a transform (move/resize/rotate) to an element using TransformPattern.</summary>
    Task<ActionResult> TransformAsync(string elementId, double? x = null, double? y = null,
        double? width = null, double? height = null, double? degrees = null,
        CancellationToken ct = default);
}

// ─── Result Types ─────────────────────────────────────────────────────────────

public record FindResult(bool Success, ElementInfo? Element, GhostHandError? Error);
public record GetValueResult(bool Success, string? Value, GhostHandError? Error);
public record GetTextResult(bool Success, string? Text, GhostHandError? Error);
public record SessionStatusResult(bool Success, bool ProcessAlive, bool WindowValid, int ElementCount, string? MainWindowTitle, GhostHandError? Error);
public record WindowListResult(bool Success, IReadOnlyList<WindowInfo>? Windows, GhostHandError? Error);
public record WindowInfo(string Handle, string? Title, bool IsModal, string? ClassName);
public record WindowStateResult(bool Success, string? Handle, string? Title, string? VisualState, bool CanMaximize, bool CanMinimize, bool IsModal, bool IsTopmost, GhostHandError? Error);
public record ToggleResult(bool Success, string? PreviousState, string? NewState, bool Verified, GhostHandError? Error);
public record ElementStateResult(bool Success, bool IsEnabled, bool IsOffscreen, bool HasFocus, string? ToggleState, string? ExpandState, GhostHandError? Error);
public record ScrollInfoResult(bool Success, double HorizontalPercent, double VerticalPercent, double HorizontalViewSize, double VerticalViewSize, bool HorizontallyScrollable, bool VerticallyScrollable, GhostHandError? Error);
public record RangeValueResult(bool Success, double Value, double Minimum, double Maximum, double SmallChange, double LargeChange, GhostHandError? Error);
public record GridInfoResult(bool Success, int RowCount, int ColumnCount, string[]? ColumnHeaders, GhostHandError? Error);
public record GridCellResult(bool Success, int Row, int Column, string? Value, GhostHandError? Error);
public record GridItemInfoResult(bool Success, int Row, int Column, int RowSpan, int ColumnSpan, GhostHandError? Error);
public record TableItemInfoResult(bool Success, string[]? RowHeaders, string[]? ColumnHeaders, GhostHandError? Error);
public record MultipleViewResult(bool Success, int CurrentViewId, string? CurrentViewName, int[]? SupportedViewIds, string[]? SupportedViewNames, GhostHandError? Error);
public record DockPositionResult(bool Success, string? Position, GhostHandError? Error);
