using System.Runtime.InteropServices;

namespace GhostHand.Core.FlaUI;

/// <summary>
/// Minimal Win32 interop for GhostHand — window focus and handle enumeration.
/// Keeps native calls isolated in one place with named imports.
/// </summary>
internal static class NativeInterop
{
    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern bool IsIconic(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [DllImport("user32.dll")]
    private static extern bool AttachThreadInput(uint idAttach, uint idAttachTo, bool fAttach);

    [DllImport("user32.dll")]
    private static extern bool BringWindowToTop(IntPtr hWnd);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    private static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll")]
    [return: MarshalAs(UnmanagedType.Bool)]
    internal static extern bool IsWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

    [DllImport("user32.dll")]
    private static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, IntPtr lpdwProcessId);

    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    private const int SW_RESTORE = 9;
    private const int SW_SHOWNOACTIVATE = 4;

    /// <summary>
    /// Bring a window to the foreground using the proven multi-step approach
    /// from FlaUI.Cli's NativeInterop.
    /// </summary>
    internal static void BringToFront(IntPtr handle)
    {
        if (IsIconic(handle))
            ShowWindow(handle, SW_RESTORE);

        var foreHwnd = GetForegroundWindow();
        var curThread = (uint)Environment.CurrentManagedThreadId;
        var foreThread = GetWindowThreadProcessId(foreHwnd, out _);
        GetWindowThreadProcessId(handle, out var targetThread);

        if (foreThread != targetThread)
            AttachThreadInput(foreThread, targetThread, true);
        if (curThread != targetThread)
            AttachThreadInput(curThread, targetThread, true);

        SetForegroundWindow(handle);
        BringWindowToTop(handle);

        if (foreThread != targetThread)
            AttachThreadInput(foreThread, targetThread, false);
        if (curThread != targetThread)
            AttachThreadInput(curThread, targetThread, false);
    }

    /// <summary>Post WM_CLOSE (0x0010) to a window handle.</summary>
    internal static void PostMessage(IntPtr handle, int msg)
    {
        PostMessage(handle, (uint)msg, IntPtr.Zero, IntPtr.Zero);
    }

    /// <summary>Get all window handles belonging to a process ID.</summary>
    internal static IEnumerable<IntPtr> GetProcessWindowHandles(int pid)
    {
        var handles = new List<IntPtr>();
        EnumWindows((hWnd, _) =>
        {
            GetWindowThreadProcessId(hWnd, out var winPid);
            if (winPid == (uint)pid && IsWindowVisible(hWnd))
                handles.Add(hWnd);
            return true;
        }, IntPtr.Zero);
        return handles;
    }
}
