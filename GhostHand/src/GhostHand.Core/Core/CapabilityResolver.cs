using FlaUI.Core.AutomationElements;
using GhostHand.Core.Models;

namespace GhostHand.Core.Core;

/// <summary>
/// Inspects a FlaUI AutomationElement and discovers which UIA control patterns
/// it supports, returning a structured CapabilityInfo for the agent.
/// 
/// This is the bridge between "raw UIA COM patterns" and "what the agent can do".
/// </summary>
public static class CapabilityResolver
{
    // All standard UIA patterns we surface to the agent
    private static readonly (string Name, Func<AutomationElement, bool> Check)[] PatternChecks =
    [
        ("Invoke",          e => e.Patterns.Invoke.IsSupported),
        ("Value",           e => e.Patterns.Value.IsSupported),
        ("Text",            e => e.Patterns.Text.IsSupported),
        ("Toggle",          e => e.Patterns.Toggle.IsSupported),
        ("ExpandCollapse",  e => e.Patterns.ExpandCollapse.IsSupported),
        ("Scroll",          e => e.Patterns.Scroll.IsSupported),
        ("ScrollItem",      e => e.Patterns.ScrollItem.IsSupported),
        ("Selection",       e => e.Patterns.Selection.IsSupported),
        ("SelectionItem",   e => e.Patterns.SelectionItem.IsSupported),
        ("RangeValue",      e => e.Patterns.RangeValue.IsSupported),
        ("Grid",            e => e.Patterns.Grid.IsSupported),
        ("GridItem",        e => e.Patterns.GridItem.IsSupported),
        ("Table",           e => e.Patterns.Table.IsSupported),
        ("TableItem",       e => e.Patterns.TableItem.IsSupported),
        ("MultipleView",    e => e.Patterns.MultipleView.IsSupported),
        ("Transform",       e => e.Patterns.Transform.IsSupported),
        ("Dock",            e => e.Patterns.Dock.IsSupported),
        ("Window",          e => e.Patterns.Window.IsSupported),
        ("ItemContainer",   e => e.Patterns.ItemContainer.IsSupported),
        ("VirtualizedItem", e => e.Patterns.VirtualizedItem.IsSupported),
    ];

    /// <summary>
    /// Discover all supported UIA patterns for the given element.
    /// Never throws — returns an empty list if pattern discovery fails.
    /// </summary>
    public static CapabilityInfo Resolve(string elementId, AutomationElement element)
    {
        var supported = new List<string>();

        foreach (var (name, check) in PatternChecks)
        {
            try
            {
                if (check(element))
                    supported.Add(name);
            }
            catch
            {
                // Pattern check may fail on stale/COM-exception elements
            }
        }

        return new CapabilityInfo
        {
            ElementId = elementId,
            SupportedPatterns = supported.AsReadOnly(),
        };
    }

    /// <summary>
    /// Build a pattern name list from a CapabilityInfo for inclusion in ElementInfo.
    /// </summary>
    public static IReadOnlyList<string> GetPatternNames(AutomationElement element)
    {
        var supported = new List<string>();
        foreach (var (name, check) in PatternChecks)
        {
            try { if (check(element)) supported.Add(name); }
            catch { }
        }
        return supported.AsReadOnly();
    }
}
