using Xunit;

namespace NiceTrafficLight.Tests;

public sealed class TrafficLightTests
{
    [Theory]
    [InlineData(RiskCategory.NearPopulation, TrafficLightColour.Green)]
    [InlineData(RiskCategory.Moderate, TrafficLightColour.Amber)]
    [InlineData(RiskCategory.High, TrafficLightColour.Red)]
    public void Category_maps_to_expected_colour(RiskCategory category, TrafficLightColour expected)
    {
        var report = TrafficLightMapper.Map(Outcome(category));

        Assert.Equal(expected, report.Colour);
    }

    [Fact]
    public void Headline_contains_counselee_name()
    {
        var report = TrafficLightMapper.Map(Outcome(RiskCategory.Moderate));

        Assert.Contains("Jane Doe", report.Headline, StringComparison.Ordinal);
    }

    [Fact]
    public void Headline_falls_back_when_counselee_name_is_empty()
    {
        var report = TrafficLightMapper.Map(new NiceOutcome(
            CounseleeName: string.Empty,
            Category: RiskCategory.High,
            ReferForGeneticsAssessment: true,
            Triggers: Array.Empty<string>(),
            Notes: Array.Empty<string>()));

        Assert.Contains("counselee", report.Headline, StringComparison.Ordinal);
    }

    private static NiceOutcome Outcome(RiskCategory category) => new(
        CounseleeName: "Jane Doe",
        Category: category,
        ReferForGeneticsAssessment: category != RiskCategory.NearPopulation,
        Triggers: Array.Empty<string>(),
        Notes: Array.Empty<string>());
}
