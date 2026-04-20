using System.Text;
using System.Text.Json;

namespace NiceTrafficLight;

public sealed class ApiException : Exception
{
    public ApiException(string message) : base(message) { }
}

public sealed record CalculateNiceArgs(string PedigreeId, string? CounseleeId = null);

public sealed class RiskApiClient
{
    private const int HttpOkLower = 200;
    private const int HttpOkUpper = 300;

    private readonly string baseUrl;
    private readonly string apiKey;
    private readonly IHttpGateway http;

    public RiskApiClient(string baseUrl, string apiKey, IHttpGateway http)
    {
        this.baseUrl = baseUrl.TrimEnd('/');
        this.apiKey = apiKey;
        this.http = http;
    }

    public async Task<JsonElement> CalculateNiceAsync(
        CalculateNiceArgs args,
        CancellationToken cancellationToken = default)
    {
        var url = $"{this.baseUrl}/api/pedigrees/{args.PedigreeId}/risk/calculate";
        var body = BuildRequestBody(args.CounseleeId);

        var response = await this.http.PostJsonAsync(url, this.Headers(), body, cancellationToken).ConfigureAwait(false);
        if (response.Status < HttpOkLower || response.Status >= HttpOkUpper)
        {
            throw new ApiException($"Evagene API returned HTTP {response.Status} for {url}");
        }

        JsonElement root;
        try
        {
            using var doc = JsonDocument.Parse(response.JsonBody);
            root = doc.RootElement.Clone();
        }
        catch (JsonException ex)
        {
            throw new ApiException($"Evagene API returned invalid JSON: {ex.Message}");
        }

        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new ApiException($"Evagene API returned non-object JSON: {root.ValueKind}");
        }
        return root;
    }

    private Dictionary<string, string> Headers() => new(StringComparer.Ordinal)
    {
        ["X-API-Key"] = this.apiKey,
        ["Accept"] = "application/json",
    };

    private static string BuildRequestBody(string? counseleeId)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writer.WriteString("model", "NICE");
            if (counseleeId is not null)
            {
                writer.WriteString("counselee_id", counseleeId);
            }
            writer.WriteEndObject();
        }
        return Encoding.UTF8.GetString(stream.ToArray());
    }
}
