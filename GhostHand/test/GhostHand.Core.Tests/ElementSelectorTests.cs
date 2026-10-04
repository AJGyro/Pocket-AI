using GhostHand.Core.Models;
using Xunit;

namespace GhostHand.Core.Tests;

public class ElementSelectorTests
{
    [Fact]
    public void EmptySelector_IsEmptyReturnsTrue()
    {
        var selector = new ElementSelector();
        Assert.True(selector.IsEmpty);
    }

    [Fact]
    public void NonEmptySelector_IsEmptyReturnsFalse()
    {
        var selector = new ElementSelector { AutomationId = "btnSubmit" };
        Assert.False(selector.IsEmpty);
    }

    [Fact]
    public void ToString_FormatsDefinedProperties()
    {
        var selector = new ElementSelector
        {
            AutomationId = "btnSubmit",
            Name = "Submit",
            ControlType = "Button"
        };
        var str = selector.ToString();
        Assert.Contains("automation_id='btnSubmit'", str);
        Assert.Contains("name='Submit'", str);
        Assert.Contains("control_type='Button'", str);
    }
}
