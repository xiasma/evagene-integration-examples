using System.Text.Json;

namespace XegUpgrader.Tests;

internal static class Fixtures
{
    public static string Path(string name)
    {
        return System.IO.Path.Combine(AppContext.BaseDirectory, "fixtures", name);
    }

    public static string Text(string name)
    {
        return File.ReadAllText(Path(name));
    }

    public static JsonElement Json(string name)
    {
        using var stream = File.OpenRead(Path(name));
        using var document = JsonDocument.Parse(stream);
        return document.RootElement.Clone();
    }
}
