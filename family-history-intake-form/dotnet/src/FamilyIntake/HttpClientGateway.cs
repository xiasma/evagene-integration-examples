using System.Text;

namespace FamilyIntake;

public sealed class HttpClientGateway : IHttpGateway, IDisposable
{
    private static readonly HttpMethod PatchMethod = new("PATCH");

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

    public async Task<HttpResponsePayload> SendAsync(
        HttpRequestDescriptor request,
        CancellationToken cancellationToken = default)
    {
        using var message = new HttpRequestMessage(MethodOf(request.Method), request.Url)
        {
            Content = new StringContent(request.JsonBody, Encoding.UTF8, "application/json"),
        };
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

    private static HttpMethod MethodOf(HttpMethodKind kind) => kind switch
    {
        HttpMethodKind.Post => HttpMethod.Post,
        HttpMethodKind.Patch => PatchMethod,
        _ => throw new ArgumentOutOfRangeException(nameof(kind)),
    };
}
