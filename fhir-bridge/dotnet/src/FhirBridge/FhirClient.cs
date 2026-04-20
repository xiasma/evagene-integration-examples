using System.Text.Json;

namespace FhirBridge;

public sealed class FhirApiException : Exception
{
    public FhirApiException(string message) : base(message) { }
}

public sealed class FhirClient
{
    private const int HttpOkLower = 200;
    private const int HttpOkUpper = 300;
    private const string FhirContentType = "application/fhir+json";

    private readonly string baseUrl;
    private readonly IHttpGateway http;
    private readonly string? authHeader;

    public FhirClient(string baseUrl, IHttpGateway http, string? authHeader = null)
    {
        this.baseUrl = baseUrl.TrimEnd('/');
        this.http = http;
        this.authHeader = authHeader;
    }

    public async Task<JsonElement> FetchFamilyHistoryForPatientAsync(
        string patientId,
        CancellationToken cancellationToken = default)
    {
        var url = $"{this.baseUrl}/FamilyMemberHistory?patient={Uri.EscapeDataString(patientId)}";
        var bundle = await this.SendExpectingBundleAsync(
            new HttpRequestDescriptor(HttpMethodKind.Get, url, this.Headers(), null),
            cancellationToken).ConfigureAwait(false);
        var type = bundle.TryGetProperty("type", out var t) && t.ValueKind == JsonValueKind.String
            ? t.GetString() ?? string.Empty
            : string.Empty;
        if (type != "searchset" && type != "collection")
        {
            throw new FhirApiException(
                $"FHIR server returned Bundle of unexpected type '{type}'; expected 'searchset'.");
        }
        return bundle;
    }

    public async Task<JsonElement> PostTransactionBundleAsync(
        string bundleJson,
        CancellationToken cancellationToken = default)
    {
        return await this.SendExpectingBundleAsync(
            new HttpRequestDescriptor(HttpMethodKind.Post, this.baseUrl, this.Headers(), bundleJson),
            cancellationToken).ConfigureAwait(false);
    }

    private async Task<JsonElement> SendExpectingBundleAsync(
        HttpRequestDescriptor request,
        CancellationToken cancellationToken)
    {
        var response = await this.http.SendAsync(request, cancellationToken).ConfigureAwait(false);
        if (response.Status < HttpOkLower || response.Status >= HttpOkUpper)
        {
            throw new FhirApiException(
                $"FHIR server returned HTTP {response.Status} for {request.Method} {request.Url}");
        }
        JsonElement bundle;
        try
        {
            using var doc = JsonDocument.Parse(response.Body);
            bundle = doc.RootElement.Clone();
        }
        catch (JsonException ex)
        {
            throw new FhirApiException($"FHIR server returned non-JSON body: {ex.Message}");
        }
        if (bundle.ValueKind != JsonValueKind.Object ||
            !bundle.TryGetProperty("resourceType", out var kind) ||
            kind.ValueKind != JsonValueKind.String ||
            kind.GetString() != "Bundle")
        {
            throw new FhirApiException("FHIR server returned a resource that is not a Bundle.");
        }
        return bundle;
    }

    private Dictionary<string, string> Headers()
    {
        var headers = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["Accept"] = FhirContentType,
            ["Content-Type"] = FhirContentType,
        };
        if (this.authHeader is not null)
        {
            var colon = this.authHeader.IndexOf(':', StringComparison.Ordinal);
            if (colon > 0)
            {
                var name = this.authHeader[..colon].Trim();
                var value = this.authHeader[(colon + 1)..].Trim();
                if (name.Length > 0 && value.Length > 0)
                {
                    headers[name] = value;
                }
            }
        }
        return headers;
    }
}
