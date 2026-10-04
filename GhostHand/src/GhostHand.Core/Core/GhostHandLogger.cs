using System.Diagnostics;
using System.Text.Json;

namespace GhostHand.Core.Core;

/// <summary>
/// Structured logger for GhostHand operations.
/// 
/// Each log entry captures: timestamp, session, action, element, method,
/// arguments, result, verification, duration, error, retry count.
/// 
/// Output formats: console (human-readable), JSON (machine-readable for
/// future log aggregation).
/// </summary>
public class GhostHandLogger
{
    private readonly bool _jsonMode;
    private readonly string? _sessionId;

    public GhostHandLogger(bool jsonMode = false, string? sessionId = null)
    {
        _jsonMode = jsonMode;
        _sessionId = sessionId;
    }

    public void LogAction(LogEntry entry)
    {
        if (_jsonMode)
        {
            Console.WriteLine(JsonSerializer.Serialize(entry, _jsonOptions));
        }
        else
        {
            var ts = entry.Timestamp.ToString("HH:mm:ss.fff");
            var status = entry.Success ? "SUCCESS" : "FAILED";
            var verif = entry.Verification?.Success == true ? "VERIFIED" :
                        entry.Verification?.Attempted == true ? "VERIFY_FAIL" : "";
            var verStr = verif.Length > 0 ? $" [{verif}]" : "";
            var durStr = entry.DurationMs.HasValue ? $" {entry.DurationMs}ms" : "";
            var errStr = entry.Error != null ? $"\n         ERROR={entry.Error}" : "";

            Console.WriteLine(
                $"[{ts}] {entry.Action,-22} " +
                $"ELEM={entry.ElementName ?? entry.ElementId ?? "-",-25} " +
                $"METHOD={entry.Method ?? "-",-18} " +
                $"{status}{verStr}{durStr}{errStr}");
        }
    }

    public LogContext BeginAction(string action, string? elementId = null, string? elementName = null)
    {
        return new LogContext(this, action, elementId, elementName, _sessionId);
    }

    public void LogInfo(string message, string? detail = null)
    {
        if (!_jsonMode)
        {
            var ts = DateTime.Now.ToString("HH:mm:ss.fff");
            Console.WriteLine($"[{ts}] INFO  {message}{(detail != null ? $": {detail}" : "")}");
        }
    }

    public void LogWarning(string message)
    {
        if (!_jsonMode)
        {
            var ts = DateTime.Now.ToString("HH:mm:ss.fff");
            Console.Error.WriteLine($"[{ts}] WARN  {message}");
        }
    }

    public void LogError(string message, Exception? ex = null)
    {
        if (!_jsonMode)
        {
            var ts = DateTime.Now.ToString("HH:mm:ss.fff");
            Console.Error.WriteLine($"[{ts}] ERROR {message}{(ex != null ? $": {ex.Message}" : "")}");
        }
    }

    private static readonly JsonSerializerOptions _jsonOptions = new()
    {
        WriteIndented = false,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };
}

/// <summary>
/// Scoped logging context for a single action. Records start time and completes
/// the log entry when Succeed() or Fail() is called.
/// </summary>
public class LogContext
{
    private readonly GhostHandLogger _logger;
    private readonly Stopwatch _sw = Stopwatch.StartNew();
    private readonly LogEntry _entry;
    private int _retryCount;

    internal LogContext(GhostHandLogger logger, string action, string? elementId, string? elementName, string? sessionId)
    {
        _logger = logger;
        _entry = new LogEntry
        {
            Timestamp = DateTimeOffset.Now,
            SessionId = sessionId,
            Action = action,
            ElementId = elementId,
            ElementName = elementName,
        };
    }

    public LogContext WithMethod(string method) { _entry.Method = method; return this; }
    public LogContext WithRetry(int count) { _retryCount = count; _entry.RetryCount = count; return this; }

    public LogEntry Succeed(string? verificationMethod = null, bool verified = true)
    {
        _sw.Stop();
        _entry.Success = true;
        _entry.DurationMs = _sw.ElapsedMilliseconds;
        if (verificationMethod != null)
        {
            _entry.Verification = new LogVerification(Attempted: true, Success: verified, Method: verificationMethod);
        }
        _logger.LogAction(_entry);
        return _entry;
    }

    public LogEntry Fail(string error, string? errorCode = null)
    {
        _sw.Stop();
        _entry.Success = false;
        _entry.DurationMs = _sw.ElapsedMilliseconds;
        _entry.Error = error;
        _entry.ErrorCode = errorCode;
        _logger.LogAction(_entry);
        return _entry;
    }
}

/// <summary>Structured log entry for a single GhostHand operation.</summary>
public class LogEntry
{
    public DateTimeOffset Timestamp { get; set; }
    public string? SessionId { get; set; }
    public string? WindowHandle { get; set; }
    public string? ElementId { get; set; }
    public string? ElementName { get; set; }
    public required string Action { get; set; }
    public string? Method { get; set; }
    public bool Success { get; set; }
    public long? DurationMs { get; set; }
    public LogVerification? Verification { get; set; }
    public string? Error { get; set; }
    public string? ErrorCode { get; set; }
    public int RetryCount { get; set; }
}

public record LogVerification(bool Attempted, bool Success, string? Method);
