using FlaUI.Core.WindowsAPI;
using GhostHand.Core.FlaUI;
using Xunit;

namespace GhostHand.Core.Tests;

public class KeyParserTests
{
    [Fact]
    public void Parse_SingleKey_ReturnsKey()
    {
        var keys = KeyParser.Parse("enter");
        Assert.Single(keys);
        Assert.Equal(VirtualKeyShort.ENTER, keys[0]);
    }

    [Fact]
    public void Parse_Combination_ReturnsAllKeys()
    {
        var keys = KeyParser.Parse("ctrl+alt+delete");
        Assert.Equal(3, keys.Length);
        Assert.Equal(VirtualKeyShort.CONTROL, keys[0]);
        Assert.Equal(VirtualKeyShort.ALT, keys[1]);
        Assert.Equal(VirtualKeyShort.DELETE, keys[2]);
    }

    [Fact]
    public void Parse_InvalidKey_ThrowsArgumentException()
    {
        Assert.Throws<ArgumentException>(() => KeyParser.Parse("ctrl+unknown_key"));
    }
}
