namespace CanRiskBridge;

public sealed class ApiException : Exception
{
    public ApiException(string message) : base(message) { }
}

public sealed class CanRiskFormatException : Exception
{
    public CanRiskFormatException(string message) : base(message) { }
}

public sealed class CanRiskClient
{
    public const string CanRiskHeader = "##CanRisk 2.0";

    private const int HttpOkLower = 200;
    private const int HttpOkUpper = 300;

    private readonly string baseUrl;
    private readonly string apiKey;
    private readonly IHttpGateway http;

    public CanRiskClient(string baseUrl, string apiKey, IHttpGateway http)
    {
        this.baseUrl = baseUrl.TrimEnd('/');
        this.apiKey = apiKey;
        this.http = http;
    }

    public async Task<string> FetchAsync(string pedigreeId, CancellationToken cancellationToken = default)
    {
        var url = $"{this.baseUrl}/api/pedigrees/{pedigreeId}/risk/canrisk";

        var response = await this.http.GetTextAsync(url, this.Headers(), cancellationToken).ConfigureAwait(false);
        if (response.Status < HttpOkLower || response.Status >= HttpOkUpper)
        {
            throw new ApiException($"Evagene API returned HTTP {response.Status} for {url}");
        }

        if (!response.Body.StartsWith(CanRiskHeader, StringComparison.Ordinal))
        {
            throw new CanRiskFormatException(
                $"Response body does not begin with '{CanRiskHeader}'; "
                + "check the pedigree ID and that your key has the 'analyze' scope.");
        }
        return response.Body;
    }

    private Dictionary<string, string> Headers() => new(StringComparer.Ordinal)
    {
        ["X-API-Key"] = this.apiKey,
        ["Accept"] = "text/tab-separated-values",
    };
}
