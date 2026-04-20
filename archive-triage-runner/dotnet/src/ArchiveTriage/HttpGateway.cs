using System.Net.Http;
using System.Text;

namespace ArchiveTriage;

public sealed record HttpResponsePayload(int Status, string JsonBody);

public interface IHttpGateway
{
    Task<HttpResponsePayload> SendAsync(
        HttpMethod method,
        string url,
        IReadOnlyDictionary<string, string> headers,
        string? jsonBody,
        CancellationToken cancellationToken = default);
}

public sealed class HttpClientGateway : IHttpGateway, IDisposable
{
    private readonly HttpClient client;
    private readonly bool ownsClient;

    public HttpClientGateway(TimeSpan? timeout = null)
    {
        this.client = new HttpClient { Timeout = timeout ?? TimeSpan.FromSeconds(30) };
        this.ownsClient = true;
    }

    public HttpClientGateway(HttpClient client)
    {
        this.client = client;
        this.ownsClient = false;
    }

    public async Task<HttpResponsePayload> SendAsync(
        HttpMethod method,
        string url,
        IReadOnlyDictionary<string, string> headers,
        string? jsonBody,
        CancellationToken cancellationToken = default)
    {
        using var request = new HttpRequestMessage(method, url);
        if (jsonBody is not null)
        {
            request.Content = new StringContent(jsonBody, Encoding.UTF8, "application/json");
        }
        foreach (var header in headers)
        {
            if (header.Key.Equals("Content-Type", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            request.Headers.Add(header.Key, header.Value);
        }

        using var response = await this.client.SendAsync(request, cancellationToken).ConfigureAwait(false);
        var body = await response.Content.ReadAsStringAsync(cancellationToken).ConfigureAwait(false);
        return new HttpResponsePayload((int)response.StatusCode, body);
    }

    public void Dispose()
    {
        if (this.ownsClient)
        {
            this.client.Dispose();
        }
    }
}
