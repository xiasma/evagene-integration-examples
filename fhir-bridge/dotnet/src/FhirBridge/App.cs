using System.Text.Json;

namespace FhirBridge;

public static class ExitCodes
{
    public const int Ok = 0;
    public const int Usage = 64;
    public const int Network = 69;
    public const int Mapping = 70;
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
            return await ExecuteSafelyAsync(config, activeGateway, stdout, stderr, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            if (ownsGateway && activeGateway is IDisposable disposable)
            {
                disposable.Dispose();
            }
        }
    }

    private static async Task<int> ExecuteSafelyAsync(
        Config config,
        IHttpGateway gateway,
        TextWriter stdout,
        TextWriter stderr,
        CancellationToken cancellationToken)
    {
        var evagene = new EvageneClient(config.EvageneBaseUrl, config.EvageneApiKey, gateway);
        var fhir = new FhirClient(config.FhirBaseUrl, gateway, config.FhirAuthHeader);
        var intake = new IntakeService(evagene);

        try
        {
            if (config.Mode == Mode.Push)
            {
                await PushAsync(config.Subject, evagene, fhir, stdout, cancellationToken).ConfigureAwait(false);
            }
            else
            {
                await PullAsync(config.Subject, fhir, intake, stdout, cancellationToken).ConfigureAwait(false);
            }
            return ExitCodes.Ok;
        }
        catch (EvageneApiException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Network;
        }
        catch (FhirApiException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Network;
        }
        catch (MappingException e)
        {
            await stderr.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
            return ExitCodes.Mapping;
        }
    }

    private static async Task PushAsync(
        string pedigreeId,
        EvageneClient evagene,
        FhirClient fhir,
        TextWriter stdout,
        CancellationToken cancellationToken)
    {
        var raw = await evagene.GetPedigreeDetailAsync(pedigreeId, cancellationToken).ConfigureAwait(false);
        var detail = PedigreeDetailParser.Parse(raw);
        var mapping = PedigreeToFhir.ToFhirBundle(detail);

        foreach (var warning in mapping.Warnings)
        {
            await stdout.WriteLineAsync($"warning: {warning}").ConfigureAwait(false);
        }

        var response = await fhir.PostTransactionBundleAsync(mapping.BundleJson, cancellationToken).ConfigureAwait(false);
        var responseEntries = response.TryGetProperty("entry", out var e) && e.ValueKind == JsonValueKind.Array
            ? e
            : default;

        var responseCount = responseEntries.ValueKind == JsonValueKind.Array ? responseEntries.GetArrayLength() : 0;
        await stdout.WriteLineAsync($"POST Bundle -> {responseCount} response entries").ConfigureAwait(false);
        if (responseEntries.ValueKind == JsonValueKind.Array)
        {
            foreach (var entry in responseEntries.EnumerateArray())
            {
                if (entry.ValueKind == JsonValueKind.Object &&
                    entry.TryGetProperty("response", out var resp) &&
                    resp.ValueKind == JsonValueKind.Object &&
                    resp.TryGetProperty("location", out var loc) &&
                    loc.ValueKind == JsonValueKind.String)
                {
                    await stdout.WriteLineAsync(loc.GetString() ?? string.Empty).ConfigureAwait(false);
                }
            }
        }
        await stdout.WriteLineAsync(
            $"wrote {mapping.MappedResourceCount} FamilyMemberHistory resources").ConfigureAwait(false);
    }

    private static async Task PullAsync(
        string patientId,
        FhirClient fhir,
        IntakeService intake,
        TextWriter stdout,
        CancellationToken cancellationToken)
    {
        var bundle = await fhir.FetchFamilyHistoryForPatientAsync(patientId, cancellationToken).ConfigureAwait(false);
        var entryCount = bundle.TryGetProperty("entry", out var entries) && entries.ValueKind == JsonValueKind.Array
            ? entries.GetArrayLength()
            : 0;
        await stdout.WriteLineAsync(
            $"GET FamilyMemberHistory?patient={patientId} -> {entryCount} entries").ConfigureAwait(false);

        var mapping = FhirToIntake.ToIntakeFamily(bundle, new FhirToIntakeOptions(patientId));
        foreach (var warning in mapping.Warnings)
        {
            await stdout.WriteLineAsync($"warning: {warning}").ConfigureAwait(false);
        }

        var result = await intake.CreateAsync(mapping.Family, cancellationToken).ConfigureAwait(false);
        await stdout.WriteLineAsync($"pedigree created: {result.PedigreeId}").ConfigureAwait(false);
        await stdout.WriteLineAsync($"proband:          {result.ProbandId}").ConfigureAwait(false);
        await stdout.WriteLineAsync($"relatives added:  {result.RelativesAdded}").ConfigureAwait(false);
    }
}
