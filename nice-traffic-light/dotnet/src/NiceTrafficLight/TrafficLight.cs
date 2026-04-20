namespace NiceTrafficLight;

public enum TrafficLightColour
{
    Green,
    Amber,
    Red,
}

public sealed record TrafficLightReport(
    TrafficLightColour Colour,
    string Headline,
    NiceOutcome Outcome);

public static class TrafficLightMapper
{
    public static TrafficLightReport Map(NiceOutcome outcome)
    {
        var name = string.IsNullOrEmpty(outcome.CounseleeName) ? "counselee" : outcome.CounseleeName;
        return new TrafficLightReport(
            Colour: ColourFor(outcome.Category),
            Headline: HeadlineFor(outcome.Category, name),
            Outcome: outcome);
    }

    private static TrafficLightColour ColourFor(RiskCategory category) => category switch
    {
        RiskCategory.NearPopulation => TrafficLightColour.Green,
        RiskCategory.Moderate => TrafficLightColour.Amber,
        RiskCategory.High => TrafficLightColour.Red,
        _ => throw new ArgumentOutOfRangeException(nameof(category)),
    };

    private static string HeadlineFor(RiskCategory category, string name) => category switch
    {
        RiskCategory.NearPopulation
            => $"Near-population risk for {name} \u2014 no enhanced surveillance required.",
        RiskCategory.Moderate
            => $"Moderate risk for {name} \u2014 refer if further history emerges.",
        RiskCategory.High
            => $"High risk for {name} \u2014 refer for genetics assessment.",
        _ => throw new ArgumentOutOfRangeException(nameof(category)),
    };
}
