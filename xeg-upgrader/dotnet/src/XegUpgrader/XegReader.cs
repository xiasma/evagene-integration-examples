using System.Xml;
using System.Xml.Linq;

namespace XegUpgrader;

public sealed class InvalidXegException : Exception
{
    public InvalidXegException(string message) : base(message) { }

    public InvalidXegException(string message, Exception inner) : base(message, inner) { }
}

public sealed record XegDocument(string RawText);

/// <summary>
/// Loads an Evagene v1 .xeg file from disk and validates that it is
/// well-formed XML rooted at a <c>&lt;Pedigree&gt;</c> element before the
/// upload attempts it.  Pure: no network, no side-effects beyond reading
/// the file handed in.
/// </summary>
public static class XegReader
{
    private const string ExpectedRoot = "Pedigree";

    public static XegDocument ReadFromFile(string path)
    {
        if (!File.Exists(path))
        {
            throw new InvalidXegException($"file not found: {path}");
        }

        string text;
        try
        {
            text = File.ReadAllText(path);
        }
        catch (IOException e)
        {
            throw new InvalidXegException($"could not read {path}: {e.Message}", e);
        }

        return Parse(text);
    }

    public static XegDocument Parse(string text)
    {
        var stripped = StripBom(text);
        XDocument document;
        try
        {
            document = XDocument.Parse(stripped);
        }
        catch (XmlException e)
        {
            throw new InvalidXegException(
                $"not well-formed XML: {e.Message} — check the file is a genuine Evagene v1 .xeg",
                e);
        }

        var root = document.Root
            ?? throw new InvalidXegException("XML document has no root element");
        if (root.Name.LocalName != ExpectedRoot)
        {
            throw new InvalidXegException(
                $"root element is <{root.Name.LocalName}>, expected <{ExpectedRoot}> — is this an Evagene v1 .xeg file?");
        }

        return new XegDocument(stripped);
    }

    private static string StripBom(string text)
    {
        return text.Length > 0 && text[0] == '\uFEFF' ? text[1..] : text;
    }
}
