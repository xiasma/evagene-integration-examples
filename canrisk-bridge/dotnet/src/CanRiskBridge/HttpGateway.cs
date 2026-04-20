namespace CanRiskBridge;

public sealed record HttpTextResponse(int Status, string Body);

public interface IHttpGateway
{
    Task<HttpTextResponse> GetTextAsync(
        string url,
        IReadOnlyDictionary<string, string> headers,
        CancellationToken cancellationToken = default);
}

public sealed class HttpClientGateway : IHttpGateway, IDisposable
{
    private readonly HttpClient client;
    private readonly bool ownsClient;

    public HttpClientGateway(TimeSpan? timeout = null)
    {
        this.client = new HttpClient { Timeout = timeout ?? TimeSpan.FromSeconds(10) };
        this.ownsClient = true;
    }

    public HttpClientGateway(HttpClient client)
    {
        this.client = client;
        this.ownsClient = false;
    }

    public async Task<HttpTextResponse> GetTextAsync(
        string url,
        IReadOnlyDictionary<string, string> headers,
        CancellationToken cancellationToken = default)
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, url);
        foreach (var header in headers)
        {
            request.Headers.Add(header.Key, header.Value);
        }

        using var response = await this.client.SendAsync(request, cancellationToken).ConfigureAwait(false);
        var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
        return new HttpTextResponse((int)response.StatusCode, body);
    }

    public void Dispose()
    {
        if (this.ownsClient)
        {
            this.client.Dispose();
        }
    }
}
