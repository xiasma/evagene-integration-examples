using System.Text.Json;

namespace NiceTrafficLight;

public static class ExitCodes
{
    public const int Green = 0;
    public const int Amber = 1;
    public const int Red = 2;
    public const int Usage = 64;
    public const int Unavailable = 69;
    public const int Schema = 70;
}

public static class App
{
    public static async Task<int> RunAsync(
        string[] args,
        IReadOnlyDictionary<string, string?> env,
        TextWriter stdout,
        TextWriter stderr,
        IHttpGateway? gateway = null,
        CancellationToken cancellationToken = default)
    {
        Config config;
        try
        {
            config = ConfigLoader.Load(args, env);
        }
        catch (ConfigException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Usage;
        }

        var ownsGateway = gateway is null;
        var activeGateway = gateway ?? new HttpClientGateway();
        try
        {
            return await ClassifyAsync(config, activeGateway, stdout, stderr, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            if (ownsGateway && activeGateway is IDisposable disposable)
            {
                disposable.Dispose();
            }
        }
    }

    private static async Task<int> ClassifyAsync(
        Config config,
        IHttpGateway gateway,
        TextWriter stdout,
        TextWriter stderr,
        CancellationToken cancellationToken)
    {
        var client = new RiskApiClient(config.BaseUrl, config.ApiKey, gateway);

        JsonElement payload;
        try
        {
            payload = await client.CalculateNiceAsync(
                new CalculateNiceArgs(config.PedigreeId, config.CounseleeId),
                cancellationToken).ConfigureAwait(false);
        }
        catch (ApiException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Unavailable;
        }

        try
        {
            var report = TrafficLightMapper.Map(NiceClassifier.Classify(payload));
            Presenter.Present(report, stdout);
            return ExitCodeFor(report.Colour);
        }
        catch (ResponseSchemaException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Schema;
        }
    }

    private static int ExitCodeFor(TrafficLightColour colour) => colour switch
    {
        TrafficLightColour.Green => ExitCodes.Green,
        TrafficLightColour.Amber => ExitCodes.Amber,
        TrafficLightColour.Red => ExitCodes.Red,
        _ => throw new ArgumentOutOfRangeException(nameof(colour)),
    };
}
