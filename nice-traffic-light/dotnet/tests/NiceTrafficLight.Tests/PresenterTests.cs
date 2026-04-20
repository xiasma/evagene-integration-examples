using Xunit;

namespace NiceTrafficLight.Tests;

public sealed class PresenterTests
{
    [Fact]
    public void Writes_colour_label_and_headline_on_first_line()
    {
        using var sink = new StringWriter();

        Presenter.Present(Report(Array.Empty<string>()), sink);

        var firstLine = sink.ToString().Split('\n')[0];
        Assert.StartsWith("RED", firstLine, StringComparison.Ordinal);
        Assert.Contains("Jane Doe", firstLine, StringComparison.Ordinal);
    }

    [Fact]
    public void Writes_each_trigger_on_its_own_indented_line()
    {
        using var sink = new StringWriter();

        Presenter.Present(Report(new[] { "Trigger A", "Trigger B" }), sink);

        var lines = sink.ToString().Split('\n');
        Assert.Equal("  - Trigger A", lines[1]);
        Assert.Equal("  - Trigger B", lines[2]);
    }

    [Fact]
    public void Writes_only_headline_when_no_triggers()
    {
        using var sink = new StringWriter();

        Presenter.Present(Report(Array.Empty<string>()), sink);

        Assert.DoesNotContain("  - ", sink.ToString(), StringComparison.Ordinal);
    }

    private static TrafficLightReport Report(IReadOnlyList<string> triggers) => new(
        Colour: TrafficLightColour.Red,
        Headline: "High risk for Jane Doe \u2014 refer for genetics assessment.",
        Outcome: new NiceOutcome(
            CounseleeName: "Jane Doe",
            Category: RiskCategory.High,
            ReferForGeneticsAssessment: true,
            Triggers: triggers,
            Notes: Array.Empty<string>()));
}
