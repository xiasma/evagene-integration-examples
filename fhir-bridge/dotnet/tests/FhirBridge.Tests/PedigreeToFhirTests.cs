using System.Text.Json;

using Xunit;

namespace FhirBridge.Tests;

public sealed class PedigreeToFhirTests
{
    [Fact]
    public void Maps_the_sample_pedigree_to_a_transaction_bundle()
    {
        using var doc = JsonDocument.Parse(Fixtures.LoadPedigreeDetailJson());
        var detail = PedigreeDetailParser.Parse(doc.RootElement);

        var result = PedigreeToFhir.ToFhirBundle(detail);

        Assert.Equal("Patient/p-proband", result.ProbandReference);
        Assert.Equal(6, result.MappedResourceCount);
        Assert.Single(result.Warnings);
        Assert.Contains("Sam Park", result.Warnings[0]);

        using var bundleDoc = JsonDocument.Parse(result.BundleJson);
        var root = bundleDoc.RootElement;
        Assert.Equal("Bundle", root.GetProperty("resourceType").GetString());
        Assert.Equal("transaction", root.GetProperty("type").GetString());
        var entries = root.GetProperty("entry");
        Assert.Equal(6, entries.GetArrayLength());

        var codesByName = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var entry in entries.EnumerateArray())
        {
            var resource = entry.GetProperty("resource");
            var name = resource.GetProperty("name").GetString() ?? string.Empty;
            var code = resource.GetProperty("relationship").GetProperty("coding")[0].GetProperty("code").GetString() ?? string.Empty;
            codesByName[name] = code;
        }
        Assert.Equal("MTH", codesByName["Linda Chen"]);
        Assert.Equal("FTH", codesByName["David Chen"]);
        Assert.Equal("MGRMTH", codesByName["Mary Chen"]);
        Assert.Equal("MGRFTH", codesByName["Robert Chen"]);
        Assert.Equal("BRO", codesByName["James Chen"]);
        Assert.Equal("SON", codesByName["Noah Chen"]);
    }

    [Fact]
    public void Pedigree_without_proband_is_rejected()
    {
        var json = """
        {
          "id": "ped",
          "display_name": "no proband",
          "individuals": [
            { "id": "p", "display_name": "P", "biological_sex": "female", "proband": 0, "events": [] }
          ],
          "relationships": [],
          "eggs": []
        }
        """;
        using var doc = JsonDocument.Parse(json);
        var detail = PedigreeDetailParser.Parse(doc.RootElement);

        Assert.Throws<MappingException>(() => PedigreeToFhir.ToFhirBundle(detail));
    }

    [Fact]
    public void Lone_proband_produces_empty_bundle()
    {
        var json = """
        {
          "id": "ped",
          "display_name": "lone",
          "individuals": [
            { "id": "p", "display_name": "P", "biological_sex": "female", "proband": 1, "events": [] }
          ],
          "relationships": [],
          "eggs": []
        }
        """;
        using var doc = JsonDocument.Parse(json);
        var detail = PedigreeDetailParser.Parse(doc.RootElement);

        var result = PedigreeToFhir.ToFhirBundle(detail);

        Assert.Equal(0, result.MappedResourceCount);
        Assert.Empty(result.Warnings);
    }
}
