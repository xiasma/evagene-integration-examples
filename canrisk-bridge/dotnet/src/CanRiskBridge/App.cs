namespace CanRiskBridge;

public static class ExitCodes
{
    public const int Ok = 0;
    public const int Usage = 64;
    public const int Unavailable = 69;
    public const int Format = 70;
}

public static class App
{
    public static async Task<int> RunAsync(
        string[] args,
        IReadOnlyDictionary<string, string?> env,
        TextWriter stdout,
        TextWriter stderr,
        IHttpGateway? gateway = null,
        IBrowserLauncher? browser = null,
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
        var activeBrowser = browser ?? new ProcessBrowserLauncher();
        try
        {
            return await BridgeAsync(config, activeGateway, activeBrowser, stdout, stderr, cancellationToken)
                .ConfigureAwait(false);
        }
        finally
        {
            if (ownsGateway && activeGateway is IDisposable disposable)
            {
                disposable.Dispose();
            }
        }
    }

    private static async Task<int> BridgeAsync(
        Config config,
        IHttpGateway gateway,
        IBrowserLauncher browser,
        TextWriter stdout,
        TextWriter stderr,
        CancellationToken cancellationToken)
    {
        var client = new CanRiskClient(config.BaseUrl, config.ApiKey, gateway);

        string payload;
        try
        {
            payload = await client.FetchAsync(config.PedigreeId, cancellationToken).ConfigureAwait(false);
        }
        catch (ApiException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Unavailable;
        }
        catch (CanRiskFormatException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Format;
        }

        var sink = new OutputSink(config.OutputDir, browser);
        var savedPath = sink.Save(config.PedigreeId, payload);
        await stdout.WriteLineAsync(savedPath).ConfigureAwait(false);

        if (config.OpenBrowser)
        {
            sink.OpenUploadPage();
        }
        return ExitCodes.Ok;
    }
}
