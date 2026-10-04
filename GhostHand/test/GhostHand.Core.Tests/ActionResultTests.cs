using GhostHand.Core.Errors;
using GhostHand.Core.Models;
using Xunit;

namespace GhostHand.Core.Tests;

public class ActionResultTests
{
    [Fact]
    public void Ok_CreatesSuccessfulResult()
    {
        var target = new ElementTarget("btn_1", "Save", "Button");
        var execution = new ExecutionInfo("InvokePattern", 12);
        var verification = VerificationInfo.Passed("UIA_ToggleState");

        var result = ActionResult.Ok("click", target, execution, verification);
        Assert.True(result.Success);
        Assert.Equal("click", result.Action);
        Assert.Equal("btn_1", result.Target?.ElementId);
        Assert.Equal("Save", result.Target?.Name);
        Assert.Null(result.Error);
        Assert.True(result.Verification?.Success);
    }

    [Fact]
    public void Fail_CreatesFailedResultWithError()
    {
        var error = GhostHandError.ElementNotFound("btnSubmit");
        var result = ActionResult.Fail("click", error);
        Assert.False(result.Success);
        Assert.Equal("click", result.Action);
        Assert.NotNull(result.Error);
        Assert.Equal(ErrorCode.ELEMENT_NOT_FOUND, result.Error!.Code);
    }
}
