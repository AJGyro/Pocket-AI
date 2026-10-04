using System.Diagnostics;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Definitions;
using FlaUI.Core.Input;
using FlaUI.Core.WindowsAPI;
using FlaUI.UIA3;
using GhostHand.Core.Abstractions;
using GhostHand.Core.Core;
using GhostHand.Core.Errors;
using GhostHand.Core.Models;

namespace GhostHand.Core.FlaUI;

/// <summary>
/// Concrete implementation of IGhostHandAutomation using FlaUI + UIA3 directly.
/// 
/// All interactions go through UIA control patterns — never screen coordinates.
/// Click prefers InvokePattern, Type prefers ValuePattern, etc.
/// 
/// This wraps the logic proven in FlaUI.Cli's AutomationEngine but with:
///   - Typed GhostHandError returns instead of raw exceptions
///   - Post-action verification
///   - Session-scoped element ID management via ElementResolver
///   - Structured logging via GhostHandLogger
/// </summary>
public sealed class FlaUiAutomation : IGhostHandAutomation
{
    private readonly UIA3Automation _automation;
    private readonly GhostHandLogger _logger;
    private readonly int _defaultTimeoutMs;
    private readonly int _verificationDelayMs;

    private Application? _application;
    private ElementResolver? _resolver;
    private GhostHandSession? _session;

    public FlaUiAutomation(
        GhostHandLogger? logger = null,
        int defaultTimeoutMs = 10_000,
        int verificationDelayMs = 150)
    {
        _automation = new UIA3Automation();
        _logger = logger ?? new GhostHandLogger();
        _defaultTimeoutMs = defaultTimeoutMs;
        _verificationDelayMs = verificationDelayMs;
    }

    // ─── Session Management ──────────────────────────────────────────────────

    public Task<ActionResult> AttachByNameAsync(string processName, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("session_attach").WithMethod("ProcessName");
            try
            {
                var processes = Process.GetProcessesByName(processName);
                if (processes.Length == 0)
                {
                    log.Fail($"No process found: '{processName}'", "SESSION_NOT_FOUND");
                    return ActionResult.Fail("session_attach", GhostHandError.SessionNotFound(processName));
                }
                return AttachToProcess(processes[0].Id, processName, log).Item2;
            }
            catch (Exception ex)
            {
                log.Fail(ex.Message);
                return ActionResult.Fail("session_attach", GhostHandError.ActionFailed("session_attach", ex.Message));
            }
        }, ct);
    }

    public Task<ActionResult> AttachByPidAsync(int pid, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("session_attach").WithMethod("PID");
            try
            {
                var proc = Process.GetProcessById(pid);
                return AttachToProcess(pid, proc.ProcessName, log).Item2;
            }
            catch (Exception ex)
            {
                log.Fail(ex.Message);
                return ActionResult.Fail("session_attach", GhostHandError.ActionFailed("session_attach", ex.Message));
            }
        }, ct);
    }

    public Task<ActionResult> AttachByTitleAsync(string titleSubstring, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("session_attach").WithMethod("WindowTitle");
            try
            {
                var match = Process.GetProcesses().FirstOrDefault(p =>
                {
                    try { return p.MainWindowTitle.Contains(titleSubstring, StringComparison.OrdinalIgnoreCase); }
                    catch { return false; }
                });

                if (match is null)
                {
                    log.Fail($"No process with window title containing '{titleSubstring}'");
                    return ActionResult.Fail("session_attach", GhostHandError.WindowNotFound(titleSubstring));
                }

                return AttachToProcess(match.Id, match.ProcessName, log).Item2;
            }
            catch (Exception ex)
            {
                log.Fail(ex.Message);
                return ActionResult.Fail("session_attach", GhostHandError.ActionFailed("session_attach", ex.Message));
            }
        }, ct);
    }

    public Task<SessionStatusResult> GetSessionStatusAsync(CancellationToken ct = default)
    {
        return Task.FromResult(BuildSessionStatus());
    }

    public Task<ActionResult> EndSessionAsync(CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("session_end");
            _resolver?.InvalidateAll();
            _session = null;
            _application = null;
            log.Succeed();
            return ActionResult.Ok("session_end");
        }, ct);
    }

    // ─── Observation ─────────────────────────────────────────────────────────

    public Task<ObservationResult> ObserveAsync(
        ObservationLevel level = ObservationLevel.Normal,
        string? windowHandle = null,
        CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            EnsureSession();
            var window = ResolveWindowElement(windowHandle);
            var resolver = _resolver!;

            var windowSummary = new WindowSummary(
                Title: window.Properties.Name.ValueOrDefault,
                ControlType: window.Properties.ControlType.ValueOrDefault.ToString(),
                Handle: $"{window.Properties.NativeWindowHandle.ValueOrDefault.ToInt64():X}",
                IsModal: window.Patterns.Window.IsSupported && window.Patterns.Window.Pattern.IsModal.Value,
                IsTopmost: window.Patterns.Window.IsSupported && window.Patterns.Window.Pattern.IsTopmost.Value);

            // Build element list: minimal/normal = top-level children only
            // detailed = recursive (via ElementResolver.BuildElementInfo)
            var elements = new List<ElementInfo>();

            try
            {
                var children = level == ObservationLevel.Minimal
                    ? window.FindAllChildren()
                    : window.FindAllDescendants();

                // Context limit protection: cap at 200 elements for minimal/normal
                var limit = level switch
                {
                    ObservationLevel.Minimal => 50,
                    ObservationLevel.Normal => 150,
                    ObservationLevel.Detailed => 300,
                    _ => 150,
                };

                int count = 0;
                foreach (var child in children)
                {
                    if (count++ >= limit) break;
                    try
                    {
                        var elementId = resolver.Register(child);
                        elements.Add(resolver.BuildElementInfo(elementId, child, level));
                    }
                    catch { /* skip elements that fail to describe */ }
                }
            }
            catch { /* elements enumeration failed */ }

            return new ObservationResult
            {
                Window = windowSummary,
                Elements = elements.AsReadOnly(),
                Level = level,
                SessionId = _session?.SessionId ?? "",
            };
        }, ct);
    }

    public Task<FindResult> FindElementAsync(
        ElementSelector selector,
        string? parentElementId = null,
        CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("ui_find");
            try
            {
                EnsureSession();
                if (selector.IsEmpty)
                    return Fail(log, GhostHandError.InvalidSelector("At least one selector field must be provided."));

                AutomationElement parent;
                if (parentElementId is not null)
                {
                    var parentEl = _resolver!.ResolveById(parentElementId);
                    if (parentEl is null)
                        return Fail(log, GhostHandError.ElementStale(parentElementId));
                    parent = parentEl;
                }
                else
                {
                    parent = GetMainWindow();
                }

                var (elementId, element) = _resolver!.FindElement(parent, selector, selector.TimeoutMs);
                if (element is null)
                    return Fail(log, GhostHandError.ElementNotFound(selector.ToString()));

                log.WithMethod(_resolver!.GetStrategyForId(elementId!) ?? "Unknown").Succeed();
                var info = _resolver!.BuildElementInfo(elementId!, element, ObservationLevel.Normal);
                return new FindResult(Success: true, Element: info, Error: null);
            }
            catch (Exception ex)
            {
                return Fail(log, GhostHandError.Unknown(ex.Message));
            }

            FindResult Fail(LogContext log, GhostHandError err)
            {
                log.Fail(err.Message, err.Code.ToString());
                return new FindResult(Success: false, Element: null, Error: err);
            }
        }, ct);
    }

    public Task<ElementInfo?> GetElementPropertiesAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            EnsureSession();
            var element = _resolver!.ResolveById(elementId);
            if (element is null) return null;
            return _resolver.BuildElementInfo(elementId, element, ObservationLevel.Detailed);
        }, ct);
    }

    public Task<CapabilityInfo?> GetCapabilitiesAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            EnsureSession();
            var element = _resolver!.ResolveById(elementId);
            if (element is null) return null;
            return CapabilityResolver.Resolve(elementId, element);
        }, ct);
    }

    // ─── Window Management ───────────────────────────────────────────────────

    public Task<WindowListResult> ListWindowsAsync(CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            EnsureSession();
            var handles = GetProcessWindowHandles(_application!.ProcessId);
            var windows = new List<WindowInfo>();
            foreach (var handle in handles)
            {
                try
                {
                    var el = _automation.FromHandle(handle).AsWindow();
                    if (el is not null)
                    {
                        windows.Add(new WindowInfo(
                            Handle: $"{handle.ToInt64():X}",
                            Title: el.Properties.Name.ValueOrDefault,
                            IsModal: el.Patterns.Window.IsSupported && el.Patterns.Window.Pattern.IsModal.Value,
                            ClassName: el.Properties.ClassName.ValueOrDefault));
                    }
                }
                catch { }
            }
            return new WindowListResult(Success: true, Windows: windows.AsReadOnly(), Error: null);
        }, ct);
    }

    public Task<ActionResult> FocusWindowAsync(string windowHandle, CancellationToken ct = default)
        => WindowPatternActionAsync("window_focus", windowHandle, (_, w) => BringWindowToFront(w), ct);

    public Task<ActionResult> CloseWindowAsync(string windowHandle, CancellationToken ct = default)
        => WindowPatternActionAsync("window_close", windowHandle, (_, w) =>
        {
            if (w.Patterns.Window.IsSupported)
                w.Patterns.Window.Pattern.Close();
            else
                PostClose(w);
        }, ct);

    public Task<WindowStateResult> GetWindowStateAsync(string? windowHandle = null, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            EnsureSession();
            var window = ResolveWindowElement(windowHandle);
            if (!window.Patterns.Window.IsSupported)
                return new WindowStateResult(false, null, null, null, false, false, false, false,
                    GhostHandError.PatternNotSupported("window", "Window"));

            var pattern = window.Patterns.Window.Pattern;
            return new WindowStateResult(
                Success: true,
                Handle: $"{window.Properties.NativeWindowHandle.ValueOrDefault.ToInt64():X}",
                Title: window.Properties.Name.ValueOrDefault,
                VisualState: pattern.WindowVisualState.Value.ToString(),
                CanMaximize: pattern.CanMaximize.Value,
                CanMinimize: pattern.CanMinimize.Value,
                IsModal: pattern.IsModal.Value,
                IsTopmost: pattern.IsTopmost.Value,
                Error: null);
        }, ct);
    }

    public Task<ActionResult> MinimizeWindowAsync(string? windowHandle = null, CancellationToken ct = default)
        => SetWindowStateAsync("window_minimize", windowHandle, WindowVisualState.Minimized, ct);

    public Task<ActionResult> MaximizeWindowAsync(string? windowHandle = null, CancellationToken ct = default)
        => SetWindowStateAsync("window_maximize", windowHandle, WindowVisualState.Maximized, ct);

    public Task<ActionResult> RestoreWindowAsync(string? windowHandle = null, CancellationToken ct = default)
        => SetWindowStateAsync("window_restore", windowHandle, WindowVisualState.Normal, ct);

    // ─── Element Actions ─────────────────────────────────────────────────────

    public Task<ActionResult> InvokeAsync(string elementId, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_invoke", elementId, (log, element) =>
        {
            EnsureInteractable(element);
            if (!element.Patterns.Invoke.IsSupported)
                return ActionResult.Fail("ui_invoke", GhostHandError.PatternNotSupported(elementId, "Invoke"));

            var sw = Stopwatch.StartNew();
            element.Patterns.Invoke.Pattern.Invoke();
            Thread.Sleep(_verificationDelayMs);
            sw.Stop();

            log.WithMethod("InvokePattern").Succeed();
            return ActionResult.Ok("ui_invoke",
                target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault),
                execution: new ExecutionInfo("InvokePattern", sw.ElapsedMilliseconds),
                verification: VerificationInfo.NotAttempted());
        }, ct);
    }

    public Task<ActionResult> ClickAsync(string elementId, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_click", elementId, (log, element) =>
        {
            EnsureInteractable(element);
            var sw = Stopwatch.StartNew();
            string method;

            // Prefer semantic patterns over physical click
            if (element.Patterns.Invoke.IsSupported &&
                element.ControlType is ControlType.Button or ControlType.Hyperlink
                    or ControlType.SplitButton or ControlType.MenuItem)
            {
                element.Patterns.Invoke.Pattern.Invoke();
                method = "InvokePattern";
            }
            else if (element.Patterns.ExpandCollapse.IsSupported)
            {
                var state = element.Patterns.ExpandCollapse.Pattern.ExpandCollapseState.Value;
                if (state == ExpandCollapseState.Expanded)
                    element.Patterns.ExpandCollapse.Pattern.Collapse();
                else
                    element.Patterns.ExpandCollapse.Pattern.Expand();
                method = "ExpandCollapsePattern";
            }
            else if (element.Patterns.Toggle.IsSupported)
            {
                element.Patterns.Toggle.Pattern.Toggle();
                method = "TogglePattern";
            }
            else
            {
                // Fallback: UIA-based click (FlaUI centers on element bounding rect)
                element.Click();
                method = "UIAClick";
            }

            Thread.Sleep(_verificationDelayMs);
            sw.Stop();

            log.WithMethod(method).Succeed();
            return ActionResult.Ok("ui_click",
                target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault),
                execution: new ExecutionInfo(method, sw.ElapsedMilliseconds));
        }, ct);
    }

    public Task<ActionResult> TypeAsync(string elementId, string text, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_type", elementId, (log, element) =>
        {
            if (!element.IsEnabled)
                return ActionResult.Fail("ui_type", GhostHandError.ElementDisabled(elementId));

            EnsureInteractable(element);
            element.Focus();
            Thread.Sleep(50);

            var sw = Stopwatch.StartNew();
            string method;

            if (element.Patterns.Value.IsSupported)
            {
                element.Patterns.Value.Pattern.SetValue(text);
                method = "ValuePattern";
            }
            else
            {
                // Fallback: FlaUI keyboard input
                element.AsTextBox().Text = text;
                method = "TextBoxInput";
            }

            Thread.Sleep(_verificationDelayMs);
            sw.Stop();

            // Verification: read back text/value
            var verification = VerifyTextContent(elementId, element, text);
            log.WithMethod(method).Succeed(verificationMethod: verification.Method ?? "none", verified: verification.Success);

            return ActionResult.Ok("ui_type",
                target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault),
                execution: new ExecutionInfo(method, sw.ElapsedMilliseconds),
                verification: verification);
        }, ct);
    }

    public Task<ActionResult> SetValueAsync(string elementId, string value, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_set_value", elementId, (log, element) =>
        {
            if (!element.Patterns.Value.IsSupported)
                return ActionResult.Fail("ui_set_value", GhostHandError.PatternNotSupported(elementId, "Value"));

            if (!element.IsEnabled)
                return ActionResult.Fail("ui_set_value", GhostHandError.ElementDisabled(elementId));

            EnsureInteractable(element);
            var sw = Stopwatch.StartNew();
            element.Patterns.Value.Pattern.SetValue(value);
            Thread.Sleep(_verificationDelayMs);
            sw.Stop();

            // Verify
            var actual = element.Patterns.Value.Pattern.Value.Value;
            var verified = actual == value;
            var verif = verified
                ? VerificationInfo.Passed("ValuePattern.Value", actual)
                : VerificationInfo.Failed("ValuePattern.Value", $"Expected '{value}', got '{actual}'");

            log.WithMethod("ValuePattern").Succeed("ValuePattern.Value", verified);
            return ActionResult.Ok("ui_set_value",
                target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault),
                execution: new ExecutionInfo("ValuePattern", sw.ElapsedMilliseconds),
                verification: verif);
        }, ct);
    }

    public Task<GetValueResult> GetValueAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("ui_get_value").WithMethod("auto");
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);

                string? value = null;
                if (element.Patterns.Value.IsSupported)
                    value = element.Patterns.Value.Pattern.Value.Value;
                else if (element.Patterns.Selection.IsSupported)
                    value = element.Patterns.Selection.Pattern.Selection.Value.FirstOrDefault()?.Name;
                else
                {
                    try { value = element.AsTextBox().Text; } catch { }
                    if (value is null) { try { value = element.AsLabel().Text; } catch { } }
                    if (value is null) value = element.Name;
                }

                log.Succeed();
                return new GetValueResult(Success: true, Value: value, Error: null);
            }
            catch (ElementNotFoundException ex)
            {
                log.Fail(ex.Message);
                return new GetValueResult(false, null, ex.Error);
            }
            catch (Exception ex)
            {
                log.Fail(ex.Message);
                return new GetValueResult(false, null, GhostHandError.Unknown(ex.Message));
            }
        }, ct);
    }

    public Task<GetTextResult> GetTextAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("ui_get_text");
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.Text.IsSupported)
                    return new GetTextResult(false, null, GhostHandError.PatternNotSupported(elementId, "Text"));

                var text = element.Patterns.Text.Pattern.DocumentRange.GetText(-1);
                log.WithMethod("TextPattern").Succeed();
                return new GetTextResult(Success: true, Text: text, Error: null);
            }
            catch (ElementNotFoundException ex)
            {
                log.Fail(ex.Message);
                return new GetTextResult(false, null, ex.Error);
            }
            catch (Exception ex)
            {
                log.Fail(ex.Message);
                return new GetTextResult(false, null, GhostHandError.Unknown(ex.Message));
            }
        }, ct);
    }

    public Task<ActionResult> ClearAsync(string elementId, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_clear", elementId, (log, element) =>
        {
            EnsureInteractable(element);
            if (element.Patterns.Value.IsSupported)
            {
                element.Patterns.Value.Pattern.SetValue(string.Empty);
                log.WithMethod("ValuePattern").Succeed();
            }
            else
            {
                element.Focus();
                Thread.Sleep(50);
                Keyboard.TypeSimultaneously(VirtualKeyShort.CONTROL, VirtualKeyShort.KEY_A);
                Thread.Sleep(50);
                Keyboard.TypeSimultaneously(VirtualKeyShort.DELETE);
                log.WithMethod("Keyboard(Ctrl+A+Del)").Succeed();
            }
            Thread.Sleep(_verificationDelayMs);
            return ActionResult.Ok("ui_clear", target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault));
        }, ct);
    }

    public Task<ActionResult> SelectAsync(string elementId, string itemName, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_select", elementId, (log, element) =>
        {
            EnsureInteractable(element);
            if (element.Patterns.ExpandCollapse.IsSupported)
                element.Patterns.ExpandCollapse.Pattern.Expand();

            AutomationElement? itemEl = null;
            var sw = Stopwatch.StartNew();
            while (sw.ElapsedMilliseconds < 2000)
            {
                Thread.Sleep(200);
                itemEl = element.FindFirstDescendant(_automation.ConditionFactory.ByName(itemName));
                if (itemEl is not null) break;
            }

            // Fallback: ItemContainer for virtualized lists
            if (itemEl is null && element.Patterns.ItemContainer.IsSupported)
            {
                var container = element.Patterns.ItemContainer.Pattern;
                var virtualized = container.FindItemByProperty(null, _automation.PropertyLibrary.Element.Name, itemName);
                if (virtualized is not null)
                {
                    if (virtualized.Patterns.VirtualizedItem.IsSupported)
                        virtualized.Patterns.VirtualizedItem.Pattern.Realize();
                    Thread.Sleep(100);
                    itemEl = virtualized;
                }
            }

            if (itemEl is null)
                return ActionResult.Fail("ui_select",
                    GhostHandError.ElementNotFound($"Item '{itemName}' in container '{elementId}'"));

            if (itemEl.Patterns.SelectionItem.IsSupported)
                itemEl.Patterns.SelectionItem.Pattern.Select();
            else
                itemEl.Click();

            if (element.Patterns.ExpandCollapse.IsSupported)
                element.Patterns.ExpandCollapse.Pattern.Collapse();

            Thread.Sleep(_verificationDelayMs);
            log.WithMethod("SelectionItemPattern").Succeed();
            return ActionResult.Ok("ui_select",
                target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault));
        }, ct);
    }

    public Task<ToggleResult> ToggleAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("ui_toggle").WithMethod("TogglePattern");
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.Toggle.IsSupported)
                    return new ToggleResult(false, null, null, false,
                        GhostHandError.PatternNotSupported(elementId, "Toggle"));

                EnsureInteractable(element);
                var prevState = element.Patterns.Toggle.Pattern.ToggleState.Value.ToString();
                element.Patterns.Toggle.Pattern.Toggle();
                Thread.Sleep(_verificationDelayMs);
                var newState = element.Patterns.Toggle.Pattern.ToggleState.Value.ToString();
                var verified = newState != prevState;

                log.Succeed("TogglePattern.ToggleState", verified);
                return new ToggleResult(Success: true, PreviousState: prevState, NewState: newState, Verified: verified, Error: null);
            }
            catch (ElementNotFoundException ex) { log.Fail(ex.Message); return new ToggleResult(false, null, null, false, ex.Error); }
            catch (Exception ex) { log.Fail(ex.Message); return new ToggleResult(false, null, null, false, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<ElementStateResult> GetStateAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                string? toggleState = element.Patterns.Toggle.IsSupported
                    ? element.Patterns.Toggle.Pattern.ToggleState.Value.ToString() : null;
                string? expandState = element.Patterns.ExpandCollapse.IsSupported
                    ? element.Patterns.ExpandCollapse.Pattern.ExpandCollapseState.Value.ToString() : null;

                return new ElementStateResult(
                    Success: true,
                    IsEnabled: element.IsEnabled,
                    IsOffscreen: element.IsOffscreen,
                    HasFocus: element.Properties.HasKeyboardFocus.ValueOrDefault,
                    ToggleState: toggleState,
                    ExpandState: expandState,
                    Error: null);
            }
            catch (ElementNotFoundException ex)
                { return new ElementStateResult(false, false, false, false, null, null, ex.Error); }
            catch (Exception ex)
                { return new ElementStateResult(false, false, false, false, null, null, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<ActionResult> ExpandAsync(string elementId, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_expand", elementId, (log, element) =>
        {
            if (!element.Patterns.ExpandCollapse.IsSupported)
                return ActionResult.Fail("ui_expand", GhostHandError.PatternNotSupported(elementId, "ExpandCollapse"));
            EnsureInteractable(element);
            element.Patterns.ExpandCollapse.Pattern.Expand();
            Thread.Sleep(_verificationDelayMs);
            var newState = element.Patterns.ExpandCollapse.Pattern.ExpandCollapseState.Value;
            var verified = newState == ExpandCollapseState.Expanded;
            log.WithMethod("ExpandCollapsePattern").Succeed("ExpandCollapseState", verified);
            return ActionResult.Ok("ui_expand",
                target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault),
                verification: verified ? VerificationInfo.Passed("ExpandCollapseState") : VerificationInfo.Failed("ExpandCollapseState"));
        }, ct);
    }

    public Task<ActionResult> CollapseAsync(string elementId, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_collapse", elementId, (log, element) =>
        {
            if (!element.Patterns.ExpandCollapse.IsSupported)
                return ActionResult.Fail("ui_collapse", GhostHandError.PatternNotSupported(elementId, "ExpandCollapse"));
            EnsureInteractable(element);
            element.Patterns.ExpandCollapse.Pattern.Collapse();
            Thread.Sleep(_verificationDelayMs);
            var newState = element.Patterns.ExpandCollapse.Pattern.ExpandCollapseState.Value;
            var verified = newState == ExpandCollapseState.Collapsed;
            log.WithMethod("ExpandCollapsePattern").Succeed("ExpandCollapseState", verified);
            return ActionResult.Ok("ui_collapse",
                target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault),
                verification: verified ? VerificationInfo.Passed("ExpandCollapseState") : VerificationInfo.Failed("ExpandCollapseState"));
        }, ct);
    }

    public Task<ActionResult> SendKeysAsync(string keys, string? elementId = null, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("ui_send_keys").WithMethod("Keyboard");
            try
            {
                EnsureSession();
                var parsed = KeyParser.Parse(keys);

                if (elementId is not null)
                {
                    var element = RequireElement(elementId);
                    if (!element.Properties.HasKeyboardFocus.ValueOrDefault)
                    {
                        EnsureInteractable(element);
                        element.Focus();
                        Thread.Sleep(50);
                    }
                }
                else
                {
                    BringSessionWindowToFront();
                }

                Keyboard.TypeSimultaneously(parsed);
                Thread.Sleep(_verificationDelayMs);
                log.Succeed();
                return ActionResult.Ok("ui_send_keys");
            }
            catch (ElementNotFoundException ex) { log.Fail(ex.Message); return ActionResult.Fail("ui_send_keys", ex.Error); }
            catch (Exception ex) { log.Fail(ex.Message); return ActionResult.Fail("ui_send_keys", GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<ActionResult> NavigateMenuAsync(string menuPath, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction("ui_menu").WithMethod("MenuPattern");
            try
            {
                EnsureSession();
                var window = GetMainWindow();
                var segments = menuPath.Split('>').Select(s => s.Trim()).ToArray();
                if (segments.Length == 0)
                    return ActionResult.Fail("ui_menu", GhostHandError.InvalidArgument("menu_path", "Menu path is empty."));

                var cf = _automation.ConditionFactory;
                AutomationElement? currentScope = window;

                var menuBar = window.FindFirstDescendant(cf.ByControlType(ControlType.MenuBar));
                if (menuBar is not null) currentScope = menuBar;

                for (int i = 0; i < segments.Length; i++)
                {
                    var seg = segments[i];
                    var isLast = i == segments.Length - 1;
                    var item = FindMenuItem(currentScope!, seg);

                    if (item is null)
                    {
                        // Search popup windows
                        foreach (var handle in GetProcessWindowHandles(_application!.ProcessId))
                        {
                            try
                            {
                                var topWin = _automation.FromHandle(handle).AsWindow();
                                item = FindMenuItem(topWin, seg);
                                if (item is not null) break;
                            }
                            catch { }
                        }
                    }

                    if (item is null)
                        return ActionResult.Fail("ui_menu",
                            GhostHandError.ElementNotFound($"Menu item '{seg}'"));

                    if (isLast)
                    {
                        if (item.Patterns.Invoke.IsSupported)
                            item.Patterns.Invoke.Pattern.Invoke();
                        else
                            item.Click();
                    }
                    else
                    {
                        if (item.Patterns.ExpandCollapse.IsSupported)
                            item.Patterns.ExpandCollapse.Pattern.Expand();
                        else
                            item.Click();
                        Thread.Sleep(200);
                        currentScope = item;
                    }
                }

                Thread.Sleep(_verificationDelayMs);
                log.Succeed();
                return ActionResult.Ok("ui_menu");
            }
            catch (Exception ex) { log.Fail(ex.Message); return ActionResult.Fail("ui_menu", GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<ActionResult> ScrollAsync(string elementId, double? horizontal = null, double? vertical = null, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_scroll", elementId, (log, element) =>
        {
            if (!element.Patterns.Scroll.IsSupported)
                return ActionResult.Fail("ui_scroll", GhostHandError.PatternNotSupported(elementId, "Scroll"));
            var pattern = element.Patterns.Scroll.Pattern;
            pattern.SetScrollPercent(horizontal ?? -1.0, vertical ?? -1.0);
            Thread.Sleep(_verificationDelayMs);
            log.WithMethod("ScrollPattern").Succeed();
            return ActionResult.Ok("ui_scroll", target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault));
        }, ct);
    }

    public Task<ActionResult> ScrollIntoViewAsync(string elementId, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_scroll_into_view", elementId, (log, element) =>
        {
            bool scrolled;
            if (element.Patterns.ScrollItem.IsSupported)
            {
                element.Patterns.ScrollItem.Pattern.ScrollIntoView();
                scrolled = true;
                log.WithMethod("ScrollItemPattern");
            }
            else
            {
                scrolled = ScrollIntoViewViaAncestors(element);
                log.WithMethod("AncestorScrollFallback");
            }
            Thread.Sleep(_verificationDelayMs);
            var offscreen = element.IsOffscreen;
            var verified = !offscreen;
            log.Succeed("IsOffscreen", verified);
            return ActionResult.Ok("ui_scroll_into_view",
                target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault),
                verification: verified ? VerificationInfo.Passed("offscreen=false") : VerificationInfo.Failed("offscreen=true"));
        }, ct);
    }

    public Task<ScrollInfoResult> GetScrollInfoAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.Scroll.IsSupported)
                    return new ScrollInfoResult(false, 0, 0, 0, 0, false, false,
                        GhostHandError.PatternNotSupported(elementId, "Scroll"));
                var p = element.Patterns.Scroll.Pattern;
                return new ScrollInfoResult(true,
                    p.HorizontalScrollPercent.Value, p.VerticalScrollPercent.Value,
                    p.HorizontalViewSize.Value, p.VerticalViewSize.Value,
                    p.HorizontallyScrollable.Value, p.VerticallyScrollable.Value, null);
            }
            catch (Exception ex) { return new ScrollInfoResult(false, 0, 0, 0, 0, false, false, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    // ─── Range Controls ──────────────────────────────────────────────────────

    public Task<RangeValueResult> GetRangeAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.RangeValue.IsSupported)
                    return new RangeValueResult(false, 0, 0, 0, 0, 0, GhostHandError.PatternNotSupported(elementId, "RangeValue"));
                var p = element.Patterns.RangeValue.Pattern;
                return new RangeValueResult(true, p.Value.Value, p.Minimum.Value, p.Maximum.Value, p.SmallChange.Value, p.LargeChange.Value, null);
            }
            catch (Exception ex) { return new RangeValueResult(false, 0, 0, 0, 0, 0, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<ActionResult> SetRangeAsync(string elementId, double value, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_set_range", elementId, (log, element) =>
        {
            if (!element.Patterns.RangeValue.IsSupported)
                return ActionResult.Fail("ui_set_range", GhostHandError.PatternNotSupported(elementId, "RangeValue"));
            var p = element.Patterns.RangeValue.Pattern;
            var min = p.Minimum.Value; var max = p.Maximum.Value;
            if (value < min || value > max)
                return ActionResult.Fail("ui_set_range", GhostHandError.ValueOutOfRange(elementId, value, min, max));
            EnsureInteractable(element);
            p.SetValue(value);
            Thread.Sleep(_verificationDelayMs);
            var actual = p.Value.Value;
            var verified = Math.Abs(actual - value) < 0.001;
            log.WithMethod("RangeValuePattern").Succeed("RangeValue.Value", verified);
            return ActionResult.Ok("ui_set_range",
                target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault),
                verification: verified ? VerificationInfo.Passed("RangeValue.Value") : VerificationInfo.Failed("RangeValue.Value", $"Expected {value}, got {actual}"));
        }, ct);
    }

    // ─── Grid / Table ────────────────────────────────────────────────────────

    public Task<GridInfoResult> GetGridInfoAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.Grid.IsSupported)
                    return new GridInfoResult(false, 0, 0, null, GhostHandError.PatternNotSupported(elementId, "Grid"));
                var grid = element.Patterns.Grid.Pattern;
                string[]? headers = null;
                if (element.Patterns.Table.IsSupported)
                    headers = element.Patterns.Table.Pattern.ColumnHeaders.Value?.Select(h => h.Name).ToArray();
                return new GridInfoResult(true, grid.RowCount.Value, grid.ColumnCount.Value, headers, null);
            }
            catch (Exception ex) { return new GridInfoResult(false, 0, 0, null, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<GridCellResult> GetGridCellAsync(string elementId, int row, int column, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.Grid.IsSupported)
                    return new GridCellResult(false, row, column, null, GhostHandError.PatternNotSupported(elementId, "Grid"));
                var cell = element.Patterns.Grid.Pattern.GetItem(row, column);
                if (cell is null)
                    return new GridCellResult(false, row, column, null, GhostHandError.ElementNotFound($"cell[{row},{column}]"));
                var value = GetElementValue(cell);
                return new GridCellResult(true, row, column, value, null);
            }
            catch (Exception ex) { return new GridCellResult(false, row, column, null, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<GridItemInfoResult> GetGridItemInfoAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.GridItem.IsSupported)
                    return new GridItemInfoResult(false, 0, 0, 0, 0, GhostHandError.PatternNotSupported(elementId, "GridItem"));
                var p = element.Patterns.GridItem.Pattern;
                return new GridItemInfoResult(true, p.Row.Value, p.Column.Value, p.RowSpan.Value, p.ColumnSpan.Value, null);
            }
            catch (Exception ex) { return new GridItemInfoResult(false, 0, 0, 0, 0, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<TableItemInfoResult> GetTableItemInfoAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.TableItem.IsSupported)
                    return new TableItemInfoResult(false, null, null, GhostHandError.PatternNotSupported(elementId, "TableItem"));
                var p = element.Patterns.TableItem.Pattern;
                return new TableItemInfoResult(true,
                    p.RowHeaderItems.Value?.Select(h => h.Name).ToArray(),
                    p.ColumnHeaderItems.Value?.Select(h => h.Name).ToArray(), null);
            }
            catch (Exception ex) { return new TableItemInfoResult(false, null, null, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    // ─── Structured Controls ─────────────────────────────────────────────────

    public Task<MultipleViewResult> GetViewsAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.MultipleView.IsSupported)
                    return new MultipleViewResult(false, 0, null, null, null, GhostHandError.PatternNotSupported(elementId, "MultipleView"));
                var p = element.Patterns.MultipleView.Pattern;
                var currentId = p.CurrentView.Value;
                var supportedIds = p.SupportedViews.Value;
                return new MultipleViewResult(true, currentId, p.GetViewName(currentId),
                    supportedIds, supportedIds?.Select(p.GetViewName).ToArray(), null);
            }
            catch (Exception ex) { return new MultipleViewResult(false, 0, null, null, null, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<ActionResult> SetViewAsync(string elementId, int viewId, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_set_view", elementId, (log, element) =>
        {
            if (!element.Patterns.MultipleView.IsSupported)
                return ActionResult.Fail("ui_set_view", GhostHandError.PatternNotSupported(elementId, "MultipleView"));
            element.Patterns.MultipleView.Pattern.SetCurrentView(viewId);
            Thread.Sleep(_verificationDelayMs);
            log.WithMethod("MultipleViewPattern").Succeed();
            return ActionResult.Ok("ui_set_view", target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault));
        }, ct);
    }

    public Task<DockPositionResult> GetDockAsync(string elementId, CancellationToken ct = default)
    {
        return Task.Run(() =>
        {
            try
            {
                EnsureSession();
                var element = RequireElement(elementId);
                if (!element.Patterns.Dock.IsSupported)
                    return new DockPositionResult(false, null, GhostHandError.PatternNotSupported(elementId, "Dock"));
                return new DockPositionResult(true, element.Patterns.Dock.Pattern.DockPosition.Value.ToString(), null);
            }
            catch (Exception ex) { return new DockPositionResult(false, null, GhostHandError.Unknown(ex.Message)); }
        }, ct);
    }

    public Task<ActionResult> SetDockAsync(string elementId, string position, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_set_dock", elementId, (log, element) =>
        {
            if (!element.Patterns.Dock.IsSupported)
                return ActionResult.Fail("ui_set_dock", GhostHandError.PatternNotSupported(elementId, "Dock"));
            if (!Enum.TryParse<DockPosition>(position, true, out var dockPos))
                return ActionResult.Fail("ui_set_dock", GhostHandError.InvalidArgument("position", $"'{position}' is not a valid DockPosition."));
            element.Patterns.Dock.Pattern.SetDockPosition(dockPos);
            Thread.Sleep(_verificationDelayMs);
            log.WithMethod("DockPattern").Succeed();
            return ActionResult.Ok("ui_set_dock", target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault));
        }, ct);
    }

    public Task<ActionResult> TransformAsync(string elementId, double? x = null, double? y = null,
        double? width = null, double? height = null, double? degrees = null, CancellationToken ct = default)
    {
        return ElementActionAsync("ui_transform", elementId, (log, element) =>
        {
            if (!element.Patterns.Transform.IsSupported)
                return ActionResult.Fail("ui_transform", GhostHandError.PatternNotSupported(elementId, "Transform"));
            var p = element.Patterns.Transform.Pattern;
            if ((x.HasValue || y.HasValue) && !p.CanMove.Value)
                return ActionResult.Fail("ui_transform", GhostHandError.ActionFailed("ui_transform", "Element does not support moving."));
            if ((width.HasValue || height.HasValue) && !p.CanResize.Value)
                return ActionResult.Fail("ui_transform", GhostHandError.ActionFailed("ui_transform", "Element does not support resizing."));
            if (degrees.HasValue && !p.CanRotate.Value)
                return ActionResult.Fail("ui_transform", GhostHandError.ActionFailed("ui_transform", "Element does not support rotation."));

            if (x.HasValue || y.HasValue) p.Move(x ?? 0, y ?? 0);
            if (width.HasValue || height.HasValue) p.Resize(width ?? 0, height ?? 0);
            if (degrees.HasValue) p.Rotate(degrees.Value);
            Thread.Sleep(_verificationDelayMs);
            log.WithMethod("TransformPattern").Succeed();
            return ActionResult.Ok("ui_transform", target: new ElementTarget(elementId, element.Properties.Name.ValueOrDefault));
        }, ct);
    }

    // ─── Dispose ─────────────────────────────────────────────────────────────

    public void Dispose()
    {
        _application?.Dispose();
        _automation.Dispose();
    }

    // ─── Private Helpers ─────────────────────────────────────────────────────

    private (LogEntry, ActionResult) AttachToProcess(int pid, string processName, LogContext log)
    {
        _application = Application.Attach(pid);
        _resolver = new ElementResolver(_automation);
        var mainWindow = _application.GetMainWindow(_automation, TimeSpan.FromSeconds(10));
        if (mainWindow is null)
            return (log.Fail("Could not find main window."), ActionResult.Fail("session_attach", GhostHandError.ActionFailed("session_attach", "Could not find main window.")));

        var sessionId = $"gh-{pid}-{DateTime.UtcNow:HHmmss}";
        _session = new GhostHandSession(sessionId, pid, processName)
        {
            MainWindowTitle = mainWindow.Properties.Name.ValueOrDefault,
            MainWindowHandle = $"{mainWindow.Properties.NativeWindowHandle.ValueOrDefault.ToInt64():X}",
        };

        log.Succeed();
        return (log.Succeed(), ActionResult.Ok("session_attach"));
    }

    private SessionStatusResult BuildSessionStatus()
    {
        if (_session is null)
            return new SessionStatusResult(false, false, false, 0, null, GhostHandError.SessionNotFound("none"));

        bool processAlive;
        try { var p = Process.GetProcessById(_session.Pid); processAlive = !p.HasExited; }
        catch { processAlive = false; }

        bool windowValid = false;
        if (processAlive && _session.MainWindowHandle is not null &&
            long.TryParse(_session.MainWindowHandle, System.Globalization.NumberStyles.HexNumber, null, out var hwnd))
        {
            windowValid = NativeInterop.IsWindow(new IntPtr(hwnd));
        }

        return new SessionStatusResult(true, processAlive, windowValid,
            _resolver?.CacheCount ?? 0, _session.MainWindowTitle, null);
    }

    private void EnsureSession()
    {
        if (_session is null || _application is null)
            throw new InvalidOperationException("No active session. Call session_attach first.");
    }

    private AutomationElement GetMainWindow()
    {
        EnsureSession();
        return _application!.GetMainWindow(_automation, TimeSpan.FromSeconds(10))
               ?? throw new InvalidOperationException("Cannot find main window.");
    }

    private AutomationElement ResolveWindowElement(string? windowHandle)
    {
        if (windowHandle is null) return GetMainWindow();
        if (!long.TryParse(windowHandle, System.Globalization.NumberStyles.HexNumber, null, out var hwnd))
            throw new ArgumentException($"Invalid window handle: '{windowHandle}'");
        return _automation.FromHandle(new IntPtr(hwnd)).AsWindow()
               ?? throw new InvalidOperationException($"Window 0x{hwnd:X} not found.");
    }

    private AutomationElement RequireElement(string elementId)
    {
        var el = _resolver?.ResolveById(elementId)
                 ?? throw new ElementNotFoundException(elementId);
        return el;
    }

    private Task<ActionResult> ElementActionAsync(string action, string elementId,
        Func<LogContext, AutomationElement, ActionResult> body, CancellationToken ct)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction(action, elementId);
            try
            {
                EnsureSession();
                var element = _resolver!.ResolveById(elementId);
                if (element is null)
                {
                    log.Fail("Element stale or not found.", ErrorCode.ELEMENT_STALE.ToString());
                    return ActionResult.Fail(action, GhostHandError.ElementStale(elementId));
                }
                return body(log, element);
            }
            catch (ElementNotFoundException ex)
            {
                log.Fail(ex.Message, ex.Error.Code.ToString());
                return ActionResult.Fail(action, ex.Error);
            }
            catch (Exception ex)
            {
                log.Fail(ex.Message, ErrorCode.ACTION_FAILED.ToString());
                return ActionResult.Fail(action, GhostHandError.ActionFailed(action, ex.Message));
            }
        }, ct);
    }

    private Task<ActionResult> WindowPatternActionAsync(string action, string windowHandle,
        Action<LogContext, AutomationElement> body, CancellationToken ct)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction(action).WithMethod("WindowPattern");
            try
            {
                EnsureSession();
                var window = ResolveWindowElement(windowHandle);
                body(log, window);
                Thread.Sleep(_verificationDelayMs);
                log.Succeed();
                return ActionResult.Ok(action);
            }
            catch (Exception ex)
            {
                log.Fail(ex.Message);
                return ActionResult.Fail(action, GhostHandError.ActionFailed(action, ex.Message));
            }
        }, ct);
    }

    private Task<ActionResult> SetWindowStateAsync(string action, string? windowHandle,
        WindowVisualState targetState, CancellationToken ct)
    {
        return Task.Run(() =>
        {
            var log = _logger.BeginAction(action).WithMethod("WindowPattern");
            try
            {
                EnsureSession();
                var window = ResolveWindowElement(windowHandle);
                if (!window.Patterns.Window.IsSupported)
                    return ActionResult.Fail(action, GhostHandError.PatternNotSupported("window", "Window"));
                window.Patterns.Window.Pattern.SetWindowVisualState(targetState);
                Thread.Sleep(200);
                var newState = window.Patterns.Window.Pattern.WindowVisualState.Value;
                var verified = newState == targetState;
                log.Succeed("WindowVisualState", verified);
                return ActionResult.Ok(action,
                    verification: verified ? VerificationInfo.Passed("WindowVisualState") : VerificationInfo.Failed("WindowVisualState", $"Expected {targetState}, got {newState}"));
            }
            catch (Exception ex)
            {
                log.Fail(ex.Message);
                return ActionResult.Fail(action, GhostHandError.ActionFailed(action, ex.Message));
            }
        }, ct);
    }

    private static void EnsureInteractable(AutomationElement element)
    {
        var handle = GetParentWindowHandle(element);
        if (handle != IntPtr.Zero)
        {
            NativeInterop.BringToFront(handle);
            Thread.Sleep(80);
        }
        if (element.IsOffscreen)
            ScrollIntoViewViaAncestors(element);
    }

    private static IntPtr GetParentWindowHandle(AutomationElement element)
    {
        var current = element;
        while (current is not null)
        {
            if (current.Properties.ControlType.ValueOrDefault == ControlType.Window)
                return current.Properties.NativeWindowHandle.ValueOrDefault;
            try { current = current.Parent; } catch { return IntPtr.Zero; }
        }
        return IntPtr.Zero;
    }

    private static bool ScrollIntoViewViaAncestors(AutomationElement element)
    {
        if (element.Patterns.ScrollItem.IsSupported)
        {
            element.Patterns.ScrollItem.Pattern.ScrollIntoView();
            Thread.Sleep(100);
            return true;
        }

        var targetRect = element.BoundingRectangle;
        if (targetRect.IsEmpty) return false;

        var current = element;
        bool scrolled = false;
        while (current is not null)
        {
            try { current = current.Parent; } catch { break; }
            if (current is null || current.Properties.ControlType.ValueOrDefault == ControlType.Window) break;
            if (!current.Patterns.Scroll.IsSupported) continue;

            var scroll = current.Patterns.Scroll.Pattern;
            var viewportRect = current.BoundingRectangle;
            if (viewportRect.IsEmpty) continue;

            targetRect = element.BoundingRectangle;
            var needsVertical = scroll.VerticallyScrollable.Value &&
                (targetRect.Bottom > viewportRect.Bottom || targetRect.Top < viewportRect.Top);
            var needsHorizontal = scroll.HorizontallyScrollable.Value &&
                (targetRect.Right > viewportRect.Right || targetRect.Left < viewportRect.Left);

            if (!needsVertical && !needsHorizontal) continue;

            var vPct = -1.0;
            if (needsVertical && scroll.VerticalViewSize.Value is > 0 and < 100)
            {
                var h = viewportRect.Height;
                var ctr = targetRect.Top + targetRect.Height / 2.0;
                var ch = h / (scroll.VerticalViewSize.Value / 100.0);
                var co = scroll.VerticalScrollPercent.Value / 100.0 * (ch - h);
                vPct = Math.Clamp((co + ctr - viewportRect.Top - h / 2.0) / (ch - h) * 100.0, 0, 100);
            }

            var hPct = -1.0;
            if (needsHorizontal && scroll.HorizontalViewSize.Value is > 0 and < 100)
            {
                var w = viewportRect.Width;
                var ctr = targetRect.Left + targetRect.Width / 2.0;
                var cw = w / (scroll.HorizontalViewSize.Value / 100.0);
                var co = scroll.HorizontalScrollPercent.Value / 100.0 * (cw - w);
                hPct = Math.Clamp((co + ctr - viewportRect.Left - w / 2.0) / (cw - w) * 100.0, 0, 100);
            }

            scroll.SetScrollPercent(hPct, vPct);
            Thread.Sleep(100);
            scrolled = true;
        }
        return scrolled;
    }

    private void BringSessionWindowToFront()
    {
        try
        {
            var window = GetMainWindow();
            var handle = window.Properties.NativeWindowHandle.ValueOrDefault;
            if (handle != IntPtr.Zero) NativeInterop.BringToFront(handle);
        }
        catch { }
    }

    private static void BringWindowToFront(AutomationElement window)
    {
        if (window.Patterns.Window.IsSupported &&
            window.Patterns.Window.Pattern.WindowVisualState.Value == WindowVisualState.Minimized)
            window.Patterns.Window.Pattern.SetWindowVisualState(WindowVisualState.Normal);

        var handle = window.Properties.NativeWindowHandle.ValueOrDefault;
        if (handle != IntPtr.Zero) NativeInterop.BringToFront(handle);
        Thread.Sleep(100);
    }

    private static void PostClose(AutomationElement window)
    {
        const int WM_CLOSE = 0x0010;
        var handle = window.Properties.NativeWindowHandle.ValueOrDefault;
        if (handle != IntPtr.Zero)
            NativeInterop.PostMessage(handle, WM_CLOSE);
    }

    private AutomationElement? FindMenuItem(AutomationElement scope, string name)
    {
        var condition = _automation.ConditionFactory.ByControlType(ControlType.MenuItem)
            .And(_automation.ConditionFactory.ByName(name));
        return scope.FindFirstDescendant(condition);
    }

    private static string? GetElementValue(AutomationElement element)
    {
        if (element.Patterns.Value.IsSupported) return element.Patterns.Value.Pattern.Value.Value;
        if (element.Patterns.Selection.IsSupported)
            return element.Patterns.Selection.Pattern.Selection.Value.FirstOrDefault()?.Name;
        try { return element.AsTextBox().Text; } catch { }
        try { return element.AsLabel().Text; } catch { }
        return element.Name;
    }

    private VerificationInfo VerifyTextContent(string elementId, AutomationElement element, string expected)
    {
        try
        {
            if (element.Patterns.Value.IsSupported)
            {
                var actual = element.Patterns.Value.Pattern.Value.Value;
                return actual.Contains(expected, StringComparison.Ordinal)
                    ? VerificationInfo.Passed("ValuePattern.Value")
                    : VerificationInfo.Failed("ValuePattern.Value", $"Expected to contain '{expected}', got '{actual}'");
            }
            if (element.Patterns.Text.IsSupported)
            {
                var actual = element.Patterns.Text.Pattern.DocumentRange.GetText(-1);
                return actual.Contains(expected, StringComparison.Ordinal)
                    ? VerificationInfo.Passed("TextPattern")
                    : VerificationInfo.Failed("TextPattern", $"Expected to contain '{expected}'");
            }
        }
        catch { }
        return VerificationInfo.NotAttempted();
    }

    private static IEnumerable<IntPtr> GetProcessWindowHandles(int pid)
    {
        return NativeInterop.GetProcessWindowHandles(pid);
    }
}

// ─── Internal Exceptions ──────────────────────────────────────────────────────

internal sealed class ElementNotFoundException : Exception
{
    public GhostHandError Error { get; }
    public ElementNotFoundException(string elementId)
        : base($"Element '{elementId}' not found in cache. It may be stale or was never registered.")
    {
        Error = GhostHandError.ElementStale(elementId);
    }
}
