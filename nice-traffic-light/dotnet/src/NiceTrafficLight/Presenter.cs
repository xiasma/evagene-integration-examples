namespace NiceTrafficLight;

public static class Presenter
{
    public static void Present(TrafficLightReport report, TextWriter sink)
    {
        sink.Write($"{LabelOf(report.Colour),-6} {report.Headline}\n");
        foreach (var trigger in report.Outcome.Triggers)
        {
            sink.Write($"  - {trigger}\n");
        }
    }

    private static string LabelOf(TrafficLightColour colour) => colour switch
    {
        TrafficLightColour.Green => "GREEN",
        TrafficLightColour.Amber => "AMBER",
        TrafficLightColour.Red => "RED",
        _ => throw new ArgumentOutOfRangeException(nameof(colour)),
    };
}
