using System.Text.Json;

namespace ArchiveTriage;

public sealed record TriageOptions(int Concurrency);

public sealed class TriageService
{
    private readonly IEvageneApi client;
    private readonly TriageOptions options;

    public TriageService(IEvageneApi client, TriageOptions options)
    {
        this.client = client;
        this.options = options;
    }

    public async IAsyncEnumerable<RowResult> TriageAsync(
        IReadOnlyList<GedcomFile> files,
        [System.Runtime.CompilerServices.EnumeratorCancellation]
        CancellationToken cancellationToken = default)
    {
        using var throttle = new SemaphoreSlim(this.options.Concurrency);
        var tasks = files.Select(file => this.TriageOneAsync(file, throttle, cancellationToken)).ToList();

        foreach (var task in tasks)
        {
            yield return await task.ConfigureAwait(false);
        }
    }

    private async Task<RowResult> TriageOneAsync(
        GedcomFile file,
        SemaphoreSlim throttle,
        CancellationToken cancellationToken)
    {
        await throttle.WaitAsync(cancellationToken).ConfigureAwait(false);
        try
        {
            return await this.PipelineAsync(file, cancellationToken).ConfigureAwait(false);
        }
        finally
        {
            throttle.Release();
        }
    }

    private async Task<RowResult> PipelineAsync(GedcomFile file, CancellationToken cancellationToken)
    {
        var displayName = Path.GetFileNameWithoutExtension(file.Path);

        string pedigreeId;
        try
        {
            pedigreeId = await this.client.CreatePedigreeAsync(displayName, cancellationToken).ConfigureAwait(false);
        }
        catch (EvageneApiException ex)
        {
            return Failure(string.Empty, displayName, $"create_pedigree failed: {ex.Message}");
        }

        try
        {
            await this.client.ImportGedcomAsync(pedigreeId, file.Content, cancellationToken).ConfigureAwait(false);
        }
        catch (EvageneApiException ex)
        {
            return Failure(pedigreeId, displayName, $"import_gedcom failed: {ex.Message}");
        }

        try
        {
            var hasProband = await this.client.HasProbandAsync(pedigreeId, cancellationToken).ConfigureAwait(false);
            if (!hasProband)
            {
                return Failure(
                    pedigreeId,
                    displayName,
                    "no proband designated in GEDCOM — mark one with a _PROBAND 1 tag.");
            }
        }
        catch (EvageneApiException ex)
        {
            return Failure(pedigreeId, displayName, $"proband check failed: {ex.Message}");
        }

        JsonElement payload;
        try
        {
            payload = await this.client.CalculateNiceAsync(pedigreeId, cancellationToken).ConfigureAwait(false);
        }
        catch (EvageneApiException ex)
        {
            return Failure(pedigreeId, displayName, $"calculate_nice failed: {ex.Message}");
        }

        return RowFromPayload(pedigreeId, displayName, payload);
    }

    private static RowResult RowFromPayload(string pedigreeId, string fallbackName, JsonElement payload)
    {
        var probandName = OptionalString(payload, "counselee_name");
        if (probandName.Length == 0)
        {
            probandName = fallbackName;
        }

        if (!payload.TryGetProperty("cancer_risk", out var cancerRisk)
            || cancerRisk.ValueKind != JsonValueKind.Object)
        {
            return Failure(pedigreeId, probandName, "NICE response missing cancer_risk block.");
        }

        var category = OptionalString(cancerRisk, "nice_category");
        if (category.Length == 0)
        {
            return Failure(pedigreeId, probandName, "NICE response schema unexpected.");
        }

        var triggers = cancerRisk.TryGetProperty("nice_triggers", out var triggersElement)
            && triggersElement.ValueKind == JsonValueKind.Array
                ? triggersElement.GetArrayLength()
                : 0;

        bool? referForGenetics = null;
        if (cancerRisk.TryGetProperty("nice_refer_genetics", out var refer)
            && (refer.ValueKind == JsonValueKind.True || refer.ValueKind == JsonValueKind.False))
        {
            referForGenetics = refer.GetBoolean();
        }

        return new RowResult(
            pedigreeId,
            probandName,
            category,
            referForGenetics,
            triggers,
            string.Empty);
    }

    private static RowResult Failure(string pedigreeId, string probandName, string message) =>
        new(pedigreeId, probandName, string.Empty, null, 0, message);

    private static string OptionalString(JsonElement container, string key) =>
        container.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.String
            ? (value.GetString() ?? string.Empty)
            : string.Empty;
}
