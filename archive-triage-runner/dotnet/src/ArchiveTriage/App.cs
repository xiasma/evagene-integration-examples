namespace ArchiveTriage;

public static class ExitCodes
{
    public const int Ok = 0;
    public const int Usage = 64;
    public const int Unavailable = 69;
    public const int InvalidInput = 70;
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

        List<GedcomFile> files;
        try
        {
            files = new GedcomScanner(config.InputDir).Scan().ToList();
        }
        catch (ScannerException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.InvalidInput;
        }

        var ownsGateway = gateway is null;
        var activeGateway = gateway ?? new HttpClientGateway();
        try
        {
            var rows = await CollectRowsAsync(config, files, activeGateway, cancellationToken)
                .ConfigureAwait(false);
            await WriteRowsAsync(config.OutputPath, stdout, rows).ConfigureAwait(false);
            return EveryCreateFailed(rows) ? ExitCodes.Unavailable : ExitCodes.Ok;
        }
        finally
        {
            if (ownsGateway && activeGateway is IDisposable disposable)
            {
                disposable.Dispose();
            }
        }
    }

    private static async Task<List<RowResult>> CollectRowsAsync(
        Config config,
        IReadOnlyList<GedcomFile> files,
        IHttpGateway gateway,
        CancellationToken cancellationToken)
    {
        var client = new EvageneClient(config.BaseUrl, config.ApiKey, gateway);
        var service = new TriageService(client, new TriageOptions(config.Concurrency));

        var rows = new List<RowResult>();
        await foreach (var row in service.TriageAsync(files, cancellationToken).ConfigureAwait(false))
        {
            rows.Add(row);
        }
        return rows;
    }

    private static async Task WriteRowsAsync(
        string? outputPath,
        TextWriter stdout,
        IReadOnlyList<RowResult> rows)
    {
        if (outputPath is null)
        {
            await new CsvWriter(stdout).WriteAsync(ToAsync(rows)).ConfigureAwait(false);
            return;
        }
        await using var file = new StreamWriter(outputPath, append: false, new System.Text.UTF8Encoding(false));
        await new CsvWriter(file).WriteAsync(ToAsync(rows)).ConfigureAwait(false);
    }

    private static bool EveryCreateFailed(List<RowResult> rows) =>
        rows.Count > 0 && rows.TrueForAll(row => row.PedigreeId.Length == 0);

    private static async IAsyncEnumerable<RowResult> ToAsync(IEnumerable<RowResult> rows)
    {
        foreach (var row in rows)
        {
            yield return row;
        }
        await Task.CompletedTask.ConfigureAwait(false);
    }
}
