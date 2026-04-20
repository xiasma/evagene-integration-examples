using Xunit;

namespace FhirBridge.Tests;

internal sealed class RecordingGateway : IHttpGateway
{
    private readonly HttpResponsePayload response;
    private readonly List<HttpRequestDescriptor> calls = new();

    public RecordingGateway(HttpResponsePayload response)
    {
        this.response = response;
    }

    public IReadOnlyList<HttpRequestDescriptor> Calls => this.calls;

    public HttpRequestDescriptor OnlyCall()
    {
        Assert.Single(this.calls);
        return this.calls[0];
    }

    public Task<HttpResponsePayload> SendAsync(
        HttpRequestDescriptor request,
        CancellationToken cancellationToken = default)
    {
        this.calls.Add(request);
        return Task.FromResult(this.response);
    }
}
