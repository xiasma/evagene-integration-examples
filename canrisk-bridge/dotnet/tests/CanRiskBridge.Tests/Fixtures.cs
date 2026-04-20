namespace CanRiskBridge.Tests;

internal static class Fixtures
{
    public static string LoadSampleCanRisk()
    {
        var path = Path.Combine(AppContext.BaseDirectory, "fixtures", "sample-canrisk.txt");
        return File.ReadAllText(path);
    }
}
