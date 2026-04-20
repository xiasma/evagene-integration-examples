using System.Text;

namespace FhirBridge;

public enum HttpMethodKind
{
    Get,
    Post,
    Patch,
    Delete,
}

public sealed record HttpResponsePayload(int Status, string Body);

public sealed record HttpRequestDescriptor(
    HttpMethodKind Method,
    string Url,
    IReadOnlyDictionary<string, string> Headers,
    string? Body);

public interface IHttpGateway
{
    Task<HttpResponsePayload> SendAsync(
        HttpRequestDescriptor request,
        CancellationToken cancellationToken = default);
}

public sealed class HttpClientGateway : IHttpGateway, IDisposable
{
    private static readonly HttpMethod PatchMethod = new("PATCH");

    private readonly HttpClient client;
    private readonly bool ownsClient;

    public HttpClientGateway(TimeSpan? timeout = null)
    {
        this.client = new HttpClient { Timeout = timeout ?? TimeSpan.FromSeconds(15) };
        this.ownsClient = true;
    }

    public HttpClientGateway(HttpClient client)
    {
        this.client = client;
        this.ownsClient = false;
    }

    public async Task<HttpResponsePayload> SendAsync(
        HttpRequestDescriptor request,
        CancellationToken cancellationToken = default)
    {
        using var message = new HttpRequestMessage(MethodOf(request.Method), request.Url);
        var contentType = ContentTypeFor(request.Headers);
        if (request.Body is not null)
        {
            message.Content = new StringContent(request.Body, Encoding.UTF8, contentType);
        }
        foreach (var header in request.Headers)
        {
            if (header.Key.Equals("Content-Type", StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            message.Headers.Add(header.Key, header.Value);
        }

        using var response = await this.client.SendAsync(message, cancellationToken).ConfigureAwait(false);
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

    private static string ContentTypeFor(IReadOnlyDictionary<string, string> headers)
    {
        return headers.TryGetValue("Content-Type", out var explicitValue) ? explicitValue : "application/json";
    }

    private static HttpMethod MethodOf(HttpMethodKind kind) => kind switch
    {
        HttpMethodKind.Get => HttpMethod.Get,
        HttpMethodKind.Post => HttpMethod.Post,
        HttpMethodKind.Patch => PatchMethod,
        HttpMethodKind.Delete => HttpMethod.Delete,
        _ => throw new ArgumentOutOfRangeException(nameof(kind)),
    };
}
