using System.Text.Json;

namespace XegUpgrader;

public static class ExitCodes
{
    public const int Success = 0;
    public const int Usage = 64;
    public const int Api = 69;
    public const int InvalidXeg = 70;
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

        XegDocument xeg;
        try
        {
            xeg = XegReader.ReadFromFile(config.InputPath);
        }
        catch (InvalidXegException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.InvalidXeg;
        }

        var ownsGateway = gateway is null;
        var activeGateway = gateway ?? new HttpClientGateway();
        try
        {
            var api = new EvageneClient(config.BaseUrl, config.ApiKey, activeGateway);
            return await ExecuteAsync(config, xeg, api, stdout, stderr, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            if (ownsGateway && activeGateway is IDisposable disposable)
            {
                disposable.Dispose();
            }
        }
    }

    private static Task<int> ExecuteAsync(
        Config config,
        XegDocument xeg,
        IEvageneApi api,
        TextWriter stdout,
        TextWriter stderr,
        CancellationToken cancellationToken)
    {
        return config.Mode switch
        {
            RunMode.Preview => PreviewAsync(config, xeg, api, stdout, stderr, cancellationToken),
            RunMode.Create => CreateAsync(config, xeg, api, stdout, stderr, cancellationToken),
            _ => throw new ArgumentOutOfRangeException(nameof(config)),
        };
    }

    private static async Task<int> PreviewAsync(
        Config config,
        XegDocument xeg,
        IEvageneApi api,
        TextWriter stdout,
        TextWriter stderr,
        CancellationToken cancellationToken)
    {
        string? scratchId = null;
        try
        {
            scratchId = await api.CreatePedigreeAsync(
                $"xeg-upgrader preview ({config.DisplayName})",
                cancellationToken).ConfigureAwait(false);

            var parsed = await api.ImportXegParseOnlyAsync(
                scratchId, xeg.RawText, cancellationToken).ConfigureAwait(false);

            var summary = SummaryPrinter.Summarise(parsed, Path.GetFileName(config.InputPath));
            await stdout.WriteAsync(SummaryPrinter.Render(summary, RunMode.Preview))
                .ConfigureAwait(false);
            return ExitCodes.Success;
        }
        catch (EvageneApiException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Api;
        }
        finally
        {
            if (scratchId is not null)
            {
                await CleanupScratchAsync(api, scratchId, stderr, cancellationToken).ConfigureAwait(false);
            }
        }
    }

    private static async Task<int> CreateAsync(
        Config config,
        XegDocument xeg,
        IEvageneApi api,
        TextWriter stdout,
        TextWriter stderr,
        CancellationToken cancellationToken)
    {
        try
        {
            var pedigreeId = await api.CreatePedigreeAsync(
                config.DisplayName, cancellationToken).ConfigureAwait(false);

            var parsed = await api.ImportXegParseOnlyAsync(
                pedigreeId, xeg.RawText, cancellationToken).ConfigureAwait(false);

            await api.ImportXegAsync(pedigreeId, xeg.RawText, cancellationToken).ConfigureAwait(false);

            var summary = SummaryPrinter.Summarise(parsed, Path.GetFileName(config.InputPath));
            await stdout.WriteAsync(SummaryPrinter.Render(summary, RunMode.Create)).ConfigureAwait(false);
            await stdout.WriteLineAsync().ConfigureAwait(false);
            await stdout.WriteLineAsync($"Pedigree created: {pedigreeId}").ConfigureAwait(false);
            await stdout.WriteLineAsync($"URL: {PedigreeUrl(config.BaseUrl, pedigreeId)}").ConfigureAwait(false);
            return ExitCodes.Success;
        }
        catch (EvageneApiException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Api;
        }
    }

    private static async Task CleanupScratchAsync(
        IEvageneApi api,
        string pedigreeId,
        TextWriter stderr,
        CancellationToken cancellationToken)
    {
        try
        {
            await api.DeletePedigreeAsync(pedigreeId, cancellationToken).ConfigureAwait(false);
        }
        catch (EvageneApiException e)
        {
            await stderr.WriteLineAsync(
                $"warning: failed to delete scratch pedigree {pedigreeId}: {e.Message}")
                .ConfigureAwait(false);
        }
    }

    private static string PedigreeUrl(string baseUrl, string pedigreeId)
    {
        return $"{baseUrl.TrimEnd('/')}/pedigrees/{pedigreeId}";
    }
}
