using System.Text.Json;

using Xunit;

namespace XegUpgrader.Tests;

public sealed class SummaryPrinterTests
{
    [Fact]
    public void Simple_pedigree_rendering_matches_expected_snapshot()
    {
        var parsed = Fixtures.Json("sample-simple-parsed.json");
        var expected = Normalise(Fixtures.Text("expected-summary.txt"));

        var summary = SummaryPrinter.Summarise(parsed, "sample-simple.xeg");
        var rendered = Normalise(SummaryPrinter.Render(summary, RunMode.Preview));

        Assert.Equal(expected, rendered);
    }

    [Fact]
    public void Counts_individuals_relationships_eggs_diseases_and_events()
    {
        var parsed = Fixtures.Json("sample-simple-parsed.json");

        var summary = SummaryPrinter.Summarise(parsed, "sample-simple.xeg");

        Assert.Equal(5, summary.Individuals);
        Assert.Equal(2, summary.Relationships);
        Assert.Equal(2, summary.Eggs);
        Assert.Equal(1, summary.Diseases);
        Assert.Equal(6, summary.Events);
    }

    [Fact]
    public void Flags_individuals_with_unknown_biological_sex()
    {
        var payload = JsonDocument.Parse("""
        {
          "individuals": [
            {"display_name": "A", "biological_sex": "female"},
            {"display_name": "B", "biological_sex": "unknown"},
            {"display_name": "C"}
          ],
          "relationships": [],
          "eggs": [],
          "diseases": []
        }
        """).RootElement;

        var summary = SummaryPrinter.Summarise(payload, "x.xeg");

        Assert.Contains(summary.Warnings, w => w.Contains("unknown biological sex"));
    }

    [Fact]
    public void Flags_eggs_without_a_parent_relationship()
    {
        var payload = JsonDocument.Parse("""
        {
          "individuals": [],
          "relationships": [],
          "eggs": [{"individual_id": "abc", "relationship_id": null}],
          "diseases": []
        }
        """).RootElement;

        var summary = SummaryPrinter.Summarise(payload, "x.xeg");

        Assert.Contains(summary.Warnings, w => w.Contains("no resolvable parent relationship"));
    }

    [Fact]
    public void Flags_manifestations_with_unknown_disease_id()
    {
        var payload = JsonDocument.Parse("""
        {
          "individuals": [
            {"display_name": "A", "biological_sex": "female",
             "diseases": [{"disease_id": "ghost"}]}
          ],
          "relationships": [],
          "eggs": [],
          "diseases": []
        }
        """).RootElement;

        var summary = SummaryPrinter.Summarise(payload, "x.xeg");

        Assert.Contains(summary.Warnings, w => w.Contains("unknown disease_id"));
    }

    [Fact]
    public void Create_mode_renders_as_create_line()
    {
        var parsed = Fixtures.Json("sample-simple-parsed.json");
        var summary = SummaryPrinter.Summarise(parsed, "x.xeg");

        var rendered = SummaryPrinter.Render(summary, RunMode.Create);

        Assert.Contains("Mode: create (pedigree imported)", rendered, StringComparison.Ordinal);
    }

    private static string Normalise(string text) => text.Replace("\r\n", "\n", StringComparison.Ordinal).TrimEnd('\n');
}
