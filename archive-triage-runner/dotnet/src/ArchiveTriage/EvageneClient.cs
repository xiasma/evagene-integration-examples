using System.Net.Http;
using System.Text;
using System.Text.Json;

namespace ArchiveTriage;

public sealed class EvageneApiException : Exception
{
    public EvageneApiException(string message) : base(message) { }

    public EvageneApiException(string message, Exception inner) : base(message, inner) { }
}

public interface IEvageneApi
{
    Task<string> CreatePedigreeAsync(string displayName, CancellationToken cancellationToken);

    Task ImportGedcomAsync(string pedigreeId, string gedcomText, CancellationToken cancellationToken);

    Task<bool> HasProbandAsync(string pedigreeId, CancellationToken cancellationToken);

    Task<JsonElement> CalculateNiceAsync(string pedigreeId, CancellationToken cancellationToken);

    Task DeletePedigreeAsync(string pedigreeId, CancellationToken cancellationToken);
}

public sealed class EvageneClient : IEvageneApi
{
    private const int HttpOkLower = 200;
    private const int HttpOkUpper = 300;

    private readonly string baseUrl;
    private readonly string apiKey;
    private readonly IHttpGateway http;

    public EvageneClient(string baseUrl, string apiKey, IHttpGateway http)
    {
        this.baseUrl = baseUrl.TrimEnd('/');
        this.apiKey = apiKey;
        this.http = http;
    }

    public async Task<string> CreatePedigreeAsync(string displayName, CancellationToken cancellationToken)
    {
        var body = BuildObject(writer => writer.WriteString("display_name", displayName));
        var root = await this.RequestObjectAsync(HttpMethod.Post, "/api/pedigrees", body, cancellationToken)
            .ConfigureAwait(false);
        if (!root.TryGetProperty("id", out var idElement) || idElement.ValueKind != JsonValueKind.String)
        {
            throw new EvageneApiException("Evagene response is missing string field 'id'");
        }
        return idElement.GetString() ?? throw new EvageneApiException("Evagene response 'id' was null");
    }

    public async Task ImportGedcomAsync(
        string pedigreeId,
        string gedcomText,
        CancellationToken cancellationToken)
    {
        // NOTE: Evagene's GEDCOM import takes a JSON body with a "content"
        // field, not raw text/plain — see https://evagene.net/docs.
        var body = BuildObject(writer => writer.WriteString("content", gedcomText));
        await this.RequestAsync(
                HttpMethod.Post,
                $"/api/pedigrees/{pedigreeId}/import/gedcom",
                body,
                cancellationToken)
            .ConfigureAwait(false);
    }

    public async Task<bool> HasProbandAsync(string pedigreeId, CancellationToken cancellationToken)
    {
        var root = await this.RequestObjectAsync(
                HttpMethod.Get,
                $"/api/pedigrees/{pedigreeId}",
                body: null,
                cancellationToken)
            .ConfigureAwait(false);

        if (!root.TryGetProperty("individuals", out var individuals)
            || individuals.ValueKind != JsonValueKind.Array)
        {
            return false;
        }

        foreach (var member in individuals.EnumerateArray())
        {
            if (member.ValueKind != JsonValueKind.Object) continue;
            if (!member.TryGetProperty("proband", out var proband)) continue;
            if (proband.ValueKind == JsonValueKind.Number && proband.GetDouble() > 0)
            {
                return true;
            }
        }
        return false;
    }

    public Task<JsonElement> CalculateNiceAsync(string pedigreeId, CancellationToken cancellationToken)
    {
        var body = BuildObject(writer => writer.WriteString("model", "NICE"));
        return this.RequestObjectAsync(
            HttpMethod.Post,
            $"/api/pedigrees/{pedigreeId}/risk/calculate",
            body,
            cancellationToken);
    }

    public async Task DeletePedigreeAsync(string pedigreeId, CancellationToken cancellationToken)
    {
        await this.RequestAsync(
                HttpMethod.Delete,
                $"/api/pedigrees/{pedigreeId}",
                body: null,
                cancellationToken)
            .ConfigureAwait(false);
    }

    private async Task<JsonElement> RequestObjectAsync(
        HttpMethod method,
        string path,
        string? body,
        CancellationToken cancellationToken)
    {
        var response = await this.RequestAsync(method, path, body, cancellationToken).ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(response.JsonBody))
        {
            throw new EvageneApiException($"Evagene API returned empty body for {method} {path}");
        }

        JsonElement root;
        try
        {
            using var doc = JsonDocument.Parse(response.JsonBody);
            root = doc.RootElement.Clone();
        }
        catch (JsonException ex)
        {
            throw new EvageneApiException($"Evagene API returned invalid JSON for {method} {path}: {ex.Message}", ex);
        }
        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new EvageneApiException(
                $"Evagene API returned non-object JSON for {method} {path}: {root.ValueKind}");
        }
        return root;
    }

    private async Task<HttpResponsePayload> RequestAsync(
        HttpMethod method,
        string path,
        string? body,
        CancellationToken cancellationToken)
    {
        var url = $"{this.baseUrl}{path}";
        HttpResponsePayload response;
        try
        {
            response = await this.http.SendAsync(
                    method,
                    url,
                    this.Headers(),
                    body,
                    cancellationToken)
                .ConfigureAwait(false);
        }
        catch (HttpRequestException ex)
        {
            throw new EvageneApiException($"Evagene API unreachable for {method} {path}: {ex.Message}", ex);
        }
        catch (TaskCanceledException ex) when (!cancellationToken.IsCancellationRequested)
        {
            throw new EvageneApiException($"Evagene API timed out for {method} {path}", ex);
        }

        if (response.Status < HttpOkLower || response.Status >= HttpOkUpper)
        {
            throw new EvageneApiException(
                $"Evagene API returned HTTP {response.Status} for {method} {path}");
        }
        return response;
    }

    private Dictionary<string, string> Headers() => new(StringComparer.Ordinal)
    {
        ["X-API-Key"] = this.apiKey,
        ["Accept"] = "application/json",
    };

    private static string BuildObject(Action<Utf8JsonWriter> writeFields)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writeFields(writer);
            writer.WriteEndObject();
        }
        return Encoding.UTF8.GetString(stream.ToArray());
    }
}
