using GhostHand.Core.Errors;
using GhostHand.Core.Models;
using Xunit;

namespace GhostHand.Core.Tests;

public class ErrorCodesTests
{
    [Fact]
    public void ElementNotFound_CreatesExpectedError()
    {
        var err = GhostHandError.ElementNotFound("SaveButton");
        Assert.Equal(ErrorCode.ELEMENT_NOT_FOUND, err.Code);
        Assert.True(err.Recoverable);
        Assert.Contains("SaveButton", err.Message);
    }

    [Fact]
    public void ElementStale_CreatesExpectedError()
    {
        var err = GhostHandError.ElementStale("e1234567");
        Assert.Equal(ErrorCode.ELEMENT_STALE, err.Code);
        Assert.True(err.Recoverable);
        Assert.Contains("e1234567", err.Message);
    }

    [Fact]
    public void VerificationFailed_CreatesExpectedError()
    {
        var err = GhostHandError.VerificationFailed("click", "Checked", "Unchecked");
        Assert.Equal(ErrorCode.VERIFICATION_FAILED, err.Code);
        Assert.True(err.Recoverable);
        Assert.Contains("click", err.Message);
    }

    [Fact]
    public void WindowNotFound_CreatesExpectedError()
    {
        var err = GhostHandError.WindowNotFound("notepad");
        Assert.Equal(ErrorCode.WINDOW_NOT_FOUND, err.Code);
        Assert.True(err.Recoverable);
    }
}
