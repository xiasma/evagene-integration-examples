using System.Text;
using System.Text.Json;

namespace XegUpgrader;

public sealed class EvageneApiException : Exception
{
    public EvageneApiException(string message) : base(message) { }
}

/// <summary>
/// The subset of the Evagene API that the .xeg upgrader depends on.  The
/// command layer talks to this interface so tests can supply a fake.
/// </summary>
public interface IEvageneApi
{
    Task<string> CreatePedigreeAsync(string displayName, CancellationToken cancellationToken = default);

    Task<JsonElement> ImportXegParseOnlyAsync(
        string pedigreeId,
        string xegXml,
        CancellationToken cancellationToken = default);

    Task ImportXegAsync(
        string pedigreeId,
        string xegXml,
        CancellationToken cancellationToken = default);

    Task DeletePedigreeAsync(string pedigreeId, CancellationToken cancellationToken = default);
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

    public async Task<string> CreatePedigreeAsync(
        string displayName,
        CancellationToken cancellationToken = default)
    {
        var body = WriteJson(writer =>
        {
            writer.WriteStartObject();
            writer.WriteString("display_name", displayName);
            writer.WriteEndObject();
        });
        var response = await this.SendAsync(
            HttpMethodKind.Post, "/api/pedigrees", body, cancellationToken).ConfigureAwait(false);
        var payload = ParseJson(response.Body);
        return RequireStringField(payload, "id");
    }

    public async Task<JsonElement> ImportXegParseOnlyAsync(
        string pedigreeId,
        string xegXml,
        CancellationToken cancellationToken = default)
    {
        var path = $"/api/pedigrees/{pedigreeId}/import/xeg?mode=parse";
        var body = BuildImportBody(xegXml);
        var response = await this.SendAsync(
            HttpMethodKind.Post, path, body, cancellationToken).ConfigureAwait(false);
        return ParseJson(response.Body);
    }

    public async Task ImportXegAsync(
        string pedigreeId,
        string xegXml,
        CancellationToken cancellationToken = default)
    {
        var path = $"/api/pedigrees/{pedigreeId}/import/xeg";
        var body = BuildImportBody(xegXml);
        await this.SendAsync(
            HttpMethodKind.Post, path, body, cancellationToken).ConfigureAwait(false);
    }

    public async Task DeletePedigreeAsync(
        string pedigreeId,
        CancellationToken cancellationToken = default)
    {
        var path = $"/api/pedigrees/{pedigreeId}";
        await this.SendAsync(
            HttpMethodKind.Delete, path, string.Empty, cancellationToken).ConfigureAwait(false);
    }

    private async Task<HttpResponsePayload> SendAsync(
        HttpMethodKind method,
        string path,
        string body,
        CancellationToken cancellationToken)
    {
        var url = $"{this.baseUrl}{path}";
        var response = await this.http.SendAsync(
            new HttpRequestDescriptor(method, url, this.Headers(), body),
            cancellationToken).ConfigureAwait(false);
        if (response.Status < HttpOkLower || response.Status >= HttpOkUpper)
        {
            throw new EvageneApiException(
                $"Evagene API returned HTTP {response.Status} for {FormatMethod(method)} {path}");
        }
        return response;
    }

    private Dictionary<string, string> Headers() => new(StringComparer.Ordinal)
    {
        ["X-API-Key"] = this.apiKey,
        ["Accept"] = "application/json",
    };

    private static string BuildImportBody(string xegXml)
    {
        return WriteJson(writer =>
        {
            writer.WriteStartObject();
            writer.WriteString("content", xegXml);
            writer.WriteEndObject();
        });
    }

    private static JsonElement ParseJson(string body)
    {
        if (string.IsNullOrWhiteSpace(body))
        {
            throw new EvageneApiException("Evagene API returned an empty response body");
        }
        try
        {
            using var doc = JsonDocument.Parse(body);
            return doc.RootElement.Clone();
        }
        catch (JsonException e)
        {
            throw new EvageneApiException($"Evagene API returned invalid JSON: {e.Message}");
        }
    }

    private static string RequireStringField(JsonElement payload, string key)
    {
        if (payload.ValueKind != JsonValueKind.Object)
        {
            throw new EvageneApiException("Evagene response is not an object");
        }
        if (!payload.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.String)
        {
            throw new EvageneApiException($"Evagene response is missing string field '{key}'");
        }
        return value.GetString() ?? throw new EvageneApiException($"Evagene response field '{key}' is null");
    }

    private static string FormatMethod(HttpMethodKind method) => method switch
    {
        HttpMethodKind.Post => "POST",
        HttpMethodKind.Delete => "DELETE",
        _ => throw new ArgumentOutOfRangeException(nameof(method)),
    };

    private static string WriteJson(Action<Utf8JsonWriter> build)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            build(writer);
        }
        return Encoding.UTF8.GetString(stream.ToArray());
    }
}
