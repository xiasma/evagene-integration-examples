using System.Text.Json;

using Xunit;

namespace NiceTrafficLight.Tests;

public sealed class ClassifierTests
{
    [Fact]
    public void NearPopulation_parses_to_enum_with_no_triggers()
    {
        var outcome = NiceClassifier.Classify(Fixtures.Load("near_population"));

        Assert.Equal(RiskCategory.NearPopulation, outcome.Category);
        Assert.False(outcome.ReferForGeneticsAssessment);
        Assert.Empty(outcome.Triggers);
    }

    [Fact]
    public void Moderate_exposes_single_trigger()
    {
        var outcome = NiceClassifier.Classify(Fixtures.Load("moderate"));

        Assert.Equal(RiskCategory.Moderate, outcome.Category);
        Assert.True(outcome.ReferForGeneticsAssessment);
        Assert.Single(outcome.Triggers);
    }

    [Fact]
    public void High_exposes_all_triggers()
    {
        var outcome = NiceClassifier.Classify(Fixtures.Load("high"));

        Assert.Equal(RiskCategory.High, outcome.Category);
        Assert.True(outcome.ReferForGeneticsAssessment);
        Assert.Equal(2, outcome.Triggers.Count);
    }

    [Fact]
    public void Missing_cancer_risk_block_throws()
    {
        using var doc = JsonDocument.Parse("""{ "model": "NICE" }""");

        Assert.Throws<ResponseSchemaException>(() => NiceClassifier.Classify(doc.RootElement));
    }

    [Fact]
    public void Unknown_category_throws()
    {
        using var doc = JsonDocument.Parse("""
            {
                "cancer_risk": {
                    "nice_category": "catastrophic",
                    "nice_refer_genetics": true,
                    "nice_triggers": [],
                    "notes": []
                }
            }
            """);

        Assert.Throws<ResponseSchemaException>(() => NiceClassifier.Classify(doc.RootElement));
    }

    [Fact]
    public void Non_string_trigger_throws()
    {
        using var doc = JsonDocument.Parse("""
            {
                "cancer_risk": {
                    "nice_category": "moderate",
                    "nice_refer_genetics": true,
                    "nice_triggers": ["ok", 42],
                    "notes": []
                }
            }
            """);

        Assert.Throws<ResponseSchemaException>(() => NiceClassifier.Classify(doc.RootElement));
    }
}
