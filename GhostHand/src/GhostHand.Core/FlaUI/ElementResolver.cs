using System.Diagnostics;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Conditions;
using FlaUI.Core.Definitions;
using FlaUI.UIA3;
using GhostHand.Core.Core;
using GhostHand.Core.Models;

namespace GhostHand.Core.FlaUI;

/// <summary>
/// Resolves semantic ElementSelectors into live FlaUI AutomationElements.
/// Uses the same priority ordering as FlaUI.Cli's SelectorResolver:
///   AutomationId > Name+ControlType > Name > ControlType+ClassName > ClassName
/// 
/// Also manages the element cache: session-scoped ID → AutomationElement mapping
/// with stale-element detection.
/// </summary>
public class ElementResolver
{
    private readonly UIA3Automation _automation;
    private readonly Dictionary<string, CachedElement> _cache = new();

    public int CacheCount => _cache.Count;

    public string? GetStrategyForId(string elementId) =>
        _cache.TryGetValue(elementId, out var c) ? c.Strategy : null;

    public ElementResolver(UIA3Automation automation)
    {
        _automation = automation;
    }

    /// <summary>
    /// Resolve an element by its session-scoped ID.
    /// Returns null and clears the cache entry if the element is stale.
    /// </summary>
    public AutomationElement? ResolveById(string elementId)
    {
        if (!_cache.TryGetValue(elementId, out var cached))
            return null;

        // Stale check: attempt to read a basic property
        try
        {
            _ = cached.Element.Properties.ControlType.ValueOrDefault;
            return cached.Element;
        }
        catch
        {
            _cache.Remove(elementId);
            return null;
        }
    }

    /// <summary>
    /// Find an element within a parent scope using a semantic selector.
    /// Returns the element + a session-scoped ID for future re-use.
    /// </summary>
    public (string? ElementId, AutomationElement? Element) FindElement(
        AutomationElement parent,
        ElementSelector selector,
        int timeoutMs = 10_000)
    {
        if (selector.IsEmpty)
            return (null, null);

        var cf = _automation.ConditionFactory;
        AutomationElement? found = null;
        string? strategy = null;

        // Priority 1: AutomationId
        if (!string.IsNullOrEmpty(selector.AutomationId))
        {
            found = FindWithTimeout(parent, cf.ByAutomationId(selector.AutomationId), timeoutMs);
            strategy = "AutomationId";
        }

        // Priority 2: Name + ControlType
        if (found is null && !string.IsNullOrEmpty(selector.Name) && !string.IsNullOrEmpty(selector.ControlType)
            && Enum.TryParse<ControlType>(selector.ControlType, true, out var ct1))
        {
            found = FindWithTimeout(parent, cf.ByName(selector.Name).And(cf.ByControlType(ct1)), timeoutMs);
            strategy = "Name+ControlType";
        }

        // Priority 3: Name alone
        if (found is null && !string.IsNullOrEmpty(selector.Name))
        {
            found = FindWithTimeout(parent, cf.ByName(selector.Name), timeoutMs);
            strategy = "Name";
        }

        // Priority 4: ControlType + ClassName
        if (found is null && !string.IsNullOrEmpty(selector.ControlType) && !string.IsNullOrEmpty(selector.ClassName)
            && Enum.TryParse<ControlType>(selector.ControlType, true, out var ct2))
        {
            found = FindWithTimeout(parent, cf.ByControlType(ct2).And(cf.ByClassName(selector.ClassName)), timeoutMs);
            strategy = "ControlType+ClassName";
        }

        // Priority 5: ClassName alone
        if (found is null && !string.IsNullOrEmpty(selector.ClassName))
        {
            found = FindWithTimeout(parent, cf.ByClassName(selector.ClassName), timeoutMs);
            strategy = "ClassName";
        }

        if (found is null) return (null, null);

        // Register in cache
        var elementId = GenerateElementId();
        _cache[elementId] = new CachedElement(found, selector, strategy!);
        return (elementId, found);
    }

    /// <summary>
    /// Register an already-found element and return its session-scoped ID.
    /// </summary>
    public string Register(AutomationElement element, ElementSelector? selector = null)
    {
        var elementId = GenerateElementId();
        _cache[elementId] = new CachedElement(element, selector ?? new ElementSelector(), "Direct");
        return elementId;
    }

    /// <summary>
    /// Try to re-find a stale element using its original selector.
    /// Returns the new element ID if successful.
    /// </summary>
    public (string? NewId, AutomationElement? Element) ReResolve(
        string staleId,
        AutomationElement parent,
        int timeoutMs = 5_000)
    {
        if (!_cache.TryGetValue(staleId, out var cached))
            return (null, null);

        _cache.Remove(staleId);
        return FindElement(parent, cached.OriginalSelector, timeoutMs);
    }

    /// <summary>Build an ElementInfo DTO from an element and its cache ID.</summary>
    public ElementInfo BuildElementInfo(string elementId, AutomationElement element, ObservationLevel level)
    {
        var bounds = element.BoundingRectangle;
        var patterns = level >= ObservationLevel.Normal
            ? CapabilityResolver.GetPatternNames(element)
            : (IReadOnlyList<string>)[]; // Minimal: skip pattern detection

        IReadOnlyList<ElementInfo>? children = null;
        if (level == ObservationLevel.Detailed)
        {
            try
            {
                children = element.FindAllChildren()
                    .Select(c => BuildElementInfo(Register(c), c, level))
                    .ToList()
                    .AsReadOnly();
            }
            catch { /* some elements don't allow children enumeration */ }
        }

        return new ElementInfo
        {
            ElementId = elementId,
            Name = element.Properties.Name.ValueOrDefault,
            AutomationId = element.Properties.AutomationId.ValueOrDefault,
            ControlType = element.Properties.ControlType.ValueOrDefault.ToString(),
            ClassName = level >= ObservationLevel.Normal ? element.Properties.ClassName.ValueOrDefault : null,
            Enabled = element.IsEnabled,
            Visible = !element.IsOffscreen,
            Offscreen = element.IsOffscreen,
            Bounds = level == ObservationLevel.Detailed && !bounds.IsEmpty
                ? new BoundsInfo(bounds.X, bounds.Y, bounds.Width, bounds.Height)
                : null,
            Patterns = patterns,
            SelectorQuality = ClassifySelectorQuality(element),
            Children = children,
            HelpText = level == ObservationLevel.Detailed
                ? element.Properties.HelpText.ValueOrDefault
                : null,
        };
    }

    public void InvalidateAll() => _cache.Clear();

    private static AutomationElement? FindWithTimeout(AutomationElement parent, ConditionBase condition, int timeoutMs)
    {
        var sw = Stopwatch.StartNew();
        while (sw.ElapsedMilliseconds < timeoutMs)
        {
            var el = parent.FindFirstDescendant(condition);
            if (el is not null) return el;
            Thread.Sleep(100);
        }
        return null;
    }

    private static SelectorQuality ClassifySelectorQuality(AutomationElement element)
    {
        if (!string.IsNullOrEmpty(element.Properties.AutomationId.ValueOrDefault))
            return SelectorQuality.Stable;
        if (!string.IsNullOrEmpty(element.Properties.Name.ValueOrDefault))
            return SelectorQuality.Acceptable;
        if (!string.IsNullOrEmpty(element.Properties.ClassName.ValueOrDefault))
            return SelectorQuality.Fragile;
        return SelectorQuality.Unresolvable;
    }

    private static string GenerateElementId() => Guid.NewGuid().ToString("N")[..8];

    private sealed record CachedElement(
        AutomationElement Element,
        ElementSelector OriginalSelector,
        string Strategy);
}
