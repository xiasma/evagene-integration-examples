using Microsoft.AspNetCore.Builder;

namespace FamilyIntake;

public static class ExitCodes
{
    public const int Usage = 64;
}

/// <summary>
/// Composition root: binds concretes to abstractions and hands back a
/// started web application, or a usage-error exit code if configuration
/// is invalid.
/// </summary>
public static class App
{
    public static async Task<int> RunAsync(
        IReadOnlyDictionary<string, string?> env,
        TextWriter stdout,
        TextWriter stderr,
        IHttpGateway? gateway = null,
        CancellationToken cancellationToken = default)
    {
        Config config;
        try
        {
            config = ConfigLoader.Load(env);
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
            await using var application = BuildWebApplication(config, activeGateway);
            await stdout.WriteLineAsync(
                $"Family-history intake form listening on http://localhost:{config.Port}/").ConfigureAwait(false);
            await application.RunAsync(cancellationToken).ConfigureAwait(false);
            return 0;
        }
        finally
        {
            if (ownsGateway && activeGateway is IDisposable disposable)
            {
                disposable.Dispose();
            }
        }
    }

    private static WebApplication BuildWebApplication(Config config, IHttpGateway gateway)
    {
        var client = new EvageneClient(config.BaseUrl, config.ApiKey, gateway);
        var service = new IntakeService(client);
        return Server.Build(new ServerOptions(service, config.BaseUrl), config.Port);
    }
}
