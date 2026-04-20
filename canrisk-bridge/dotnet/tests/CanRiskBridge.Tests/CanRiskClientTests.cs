using Xunit;

namespace CanRiskBridge.Tests;

public sealed class CanRiskClientTests
{
    private const string PedigreeId = "11111111-1111-1111-1111-111111111111";

    [Fact]
    public async Task Gets_canrisk_endpoint_with_documented_headers()
    {
        var gateway = new RecordingGateway(new HttpTextResponse(200, Fixtures.LoadSampleCanRisk()));

        var body = await Client(gateway).FetchAsync(PedigreeId);

        Assert.Equal(
            $"https://evagene.example/api/pedigrees/{PedigreeId}/risk/canrisk",
            gateway.LastUrl);
        Assert.Equal("evg_test", gateway.LastHeaders["X-API-Key"]);
        Assert.Equal("text/tab-separated-values", gateway.LastHeaders["Accept"]);
        Assert.StartsWith(CanRiskClient.CanRiskHeader, body, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Throws_api_exception_on_non_2xx_status()
    {
        var gateway = new RecordingGateway(new HttpTextResponse(500, ""));

        await Assert.ThrowsAsync<ApiException>(
            () => Client(gateway).FetchAsync(PedigreeId));
    }

    [Fact]
    public async Task Throws_format_exception_when_header_missing()
    {
        var gateway = new RecordingGateway(new HttpTextResponse(200, "not a canrisk file"));

        await Assert.ThrowsAsync<CanRiskFormatException>(
            () => Client(gateway).FetchAsync(PedigreeId));
    }

    private static CanRiskClient Client(IHttpGateway gateway) =>
        new("https://evagene.example", "evg_test", gateway);

    private sealed class RecordingGateway : IHttpGateway
    {
        private readonly HttpTextResponse response;

        public string LastUrl { get; private set; } = string.Empty;
        public IReadOnlyDictionary<string, string> LastHeaders { get; private set; } =
            new Dictionary<string, string>();

        public RecordingGateway(HttpTextResponse response)
        {
            this.response = response;
        }

        public Task<HttpTextResponse> GetTextAsync(
            string url,
            IReadOnlyDictionary<string, string> headers,
            CancellationToken cancellationToken = default)
        {
            this.LastUrl = url;
            this.LastHeaders = headers;
            return Task.FromResult(this.response);
        }
    }
}
