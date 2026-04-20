using Xunit;

namespace XegUpgrader.Tests;

public sealed class XegReaderTests
{
    [Fact]
    public void Accepts_well_formed_pedigree_xml()
    {
        var document = XegReader.Parse(Fixtures.Text("sample-simple.xeg"));

        Assert.False(string.IsNullOrEmpty(document.RawText));
        Assert.Contains("<Pedigree>", document.RawText, StringComparison.Ordinal);
    }

    [Fact]
    public void Rejects_malformed_xml_with_parse_error_message()
    {
        var error = Assert.Throws<InvalidXegException>(
            () => XegReader.Parse(Fixtures.Text("malformed.xeg")));

        Assert.Contains("not well-formed XML", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Rejects_xml_with_wrong_root_element()
    {
        const string foreign = "<?xml version=\"1.0\"?><Family><Individual/></Family>";

        var error = Assert.Throws<InvalidXegException>(() => XegReader.Parse(foreign));

        Assert.Contains("<Family>", error.Message, StringComparison.Ordinal);
        Assert.Contains("<Pedigree>", error.Message, StringComparison.Ordinal);
    }

    [Fact]
    public void Strips_utf8_bom_before_parsing()
    {
        var withBom = "\uFEFF" + "<?xml version=\"1.0\"?><Pedigree/>";

        var document = XegReader.Parse(withBom);

        Assert.False(document.RawText.StartsWith('\uFEFF'));
    }

    [Fact]
    public void Read_from_file_surfaces_missing_file_as_invalid_xeg()
    {
        var error = Assert.Throws<InvalidXegException>(
            () => XegReader.ReadFromFile(Fixtures.Path("does-not-exist.xeg")));

        Assert.Contains("file not found", error.Message, StringComparison.Ordinal);
    }
}
