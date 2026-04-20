using System.Reflection;

namespace FhirBridge.Tests;

internal static class Fixtures
{
    public static string LoadPedigreeDetailJson() => Load("sample-evagene-detail.json");

    public static string LoadFhirBundleJson() => Load("sample-fhir-bundle.json");

    private static string Load(string fileName)
    {
        var here = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location)!;
        var path = Path.GetFullPath(Path.Combine(here, "..", "..", "..", "..", "..", "..", "fixtures", fileName));
        return File.ReadAllText(path);
    }
}
