using System.Text.Json;

using Xunit;

namespace XegUpgrader.Tests;

public sealed class EvageneClientTests
{
    private const string PedigreeId = "11111111-1111-1111-1111-111111111111";
    private const string XegXml = "<?xml version=\"1.0\"?><Pedigree/>";

    [Fact]
    public async Task Create_pedigree_posts_display_name_and_returns_id()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            Status: 201,
            Body: $"{{\"id\":\"{PedigreeId}\"}}"));

        var id = await Client(gateway).CreatePedigreeAsync("Hill family");

        Assert.Equal(PedigreeId, id);
        Assert.Equal("https://evagene.example/api/pedigrees", gateway.LastUrl);
        Assert.Equal(HttpMethodKind.Post, gateway.LastMethod);
        Assert.Equal("evg_test", gateway.LastHeaders["X-API-Key"]);
        using var body = JsonDocument.Parse(gateway.LastBody);
        Assert.Equal("Hill family", body.RootElement.GetProperty("display_name").GetString());
    }

    [Fact]
    public async Task Parse_only_posts_to_xeg_endpoint_with_mode_parse()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            Status: 200,
            Body: """{"individuals":[],"relationships":[],"eggs":[],"diseases":[]}"""));

        await Client(gateway).ImportXegParseOnlyAsync(PedigreeId, XegXml);

        Assert.Equal(
            $"https://evagene.example/api/pedigrees/{PedigreeId}/import/xeg?mode=parse",
            gateway.LastUrl);
        using var body = JsonDocument.Parse(gateway.LastBody);
        Assert.Equal(XegXml, body.RootElement.GetProperty("content").GetString());
    }

    [Fact]
    public async Task Import_posts_to_xeg_endpoint_without_mode_query()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(Status: 204, Body: string.Empty));

        await Client(gateway).ImportXegAsync(PedigreeId, XegXml);

        Assert.Equal(
            $"https://evagene.example/api/pedigrees/{PedigreeId}/import/xeg",
            gateway.LastUrl);
        Assert.DoesNotContain("mode=", gateway.LastUrl, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Throws_when_non_2xx_status()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(Status: 500, Body: string.Empty));

        await Assert.ThrowsAsync<EvageneApiException>(
            () => Client(gateway).ImportXegAsync(PedigreeId, XegXml));
    }

    [Fact]
    public async Task Delete_pedigree_sends_delete_to_pedigree_path()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(Status: 204, Body: string.Empty));

        await Client(gateway).DeletePedigreeAsync(PedigreeId);

        Assert.Equal(HttpMethodKind.Delete, gateway.LastMethod);
        Assert.Equal(
            $"https://evagene.example/api/pedigrees/{PedigreeId}", gateway.LastUrl);
    }

    private static EvageneClient Client(IHttpGateway gateway) =>
        new("https://evagene.example", "evg_test", gateway);

    private sealed class RecordingGateway : IHttpGateway
    {
        private readonly HttpResponsePayload response;

        public string LastUrl { get; private set; } = string.Empty;
        public IReadOnlyDictionary<string, string> LastHeaders { get; private set; } =
            new Dictionary<string, string>();
        public string LastBody { get; private set; } = string.Empty;
        public HttpMethodKind LastMethod { get; private set; }

        public RecordingGateway(HttpResponsePayload response)
        {
            this.response = response;
        }

        public Task<HttpResponsePayload> SendAsync(
            HttpRequestDescriptor request,
            CancellationToken cancellationToken = default)
        {
            this.LastUrl = request.Url;
            this.LastHeaders = request.Headers;
            this.LastBody = request.Body;
            this.LastMethod = request.Method;
            return Task.FromResult(this.response);
        }
    }
}
