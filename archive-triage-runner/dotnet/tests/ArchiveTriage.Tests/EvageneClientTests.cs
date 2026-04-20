using System.Net.Http;
using System.Text.Json;

using Xunit;

namespace ArchiveTriage.Tests;

public sealed class EvageneClientTests
{
    private const string PedigreeId = "pedigree-1";

    [Fact]
    public async Task Create_pedigree_posts_display_name_and_returns_id()
    {
        var gateway = new RecordingGateway(Response(201, """{"id":"pedigree-1"}"""));

        var id = await Client(gateway).CreatePedigreeAsync("Smith family", CancellationToken.None);

        var call = gateway.Calls[0];
        Assert.Equal(HttpMethod.Post, call.Method);
        Assert.Equal("https://evagene.example/api/pedigrees", call.Url);
        Assert.Equal("evg_test", call.Headers["X-API-Key"]);
        using var body = JsonDocument.Parse(call.Body!);
        Assert.Equal("Smith family", body.RootElement.GetProperty("display_name").GetString());
        Assert.Equal("pedigree-1", id);
    }

    [Fact]
    public async Task Import_gedcom_wraps_text_in_json_content_field()
    {
        var gateway = new RecordingGateway(Response(204, string.Empty));

        await Client(gateway).ImportGedcomAsync(PedigreeId, "0 HEAD\n0 TRLR\n", CancellationToken.None);

        var call = gateway.Calls[0];
        Assert.Equal("https://evagene.example/api/pedigrees/pedigree-1/import/gedcom", call.Url);
        using var body = JsonDocument.Parse(call.Body!);
        Assert.Equal("0 HEAD\n0 TRLR\n", body.RootElement.GetProperty("content").GetString());
    }

    [Fact]
    public async Task Has_proband_true_when_any_individual_has_nonzero_proband()
    {
        const string detail = """{"individuals":[{"id":"i1","proband":0},{"id":"i2","proband":90}]}""";
        var gateway = new RecordingGateway(Response(200, detail));

        Assert.True(await Client(gateway).HasProbandAsync(PedigreeId, CancellationToken.None));
    }

    [Fact]
    public async Task Has_proband_false_when_all_probands_zero()
    {
        const string detail = """{"individuals":[{"id":"i1","proband":0}]}""";
        var gateway = new RecordingGateway(Response(200, detail));

        Assert.False(await Client(gateway).HasProbandAsync(PedigreeId, CancellationToken.None));
    }

    [Fact]
    public async Task Calculate_nice_posts_model_nice()
    {
        var gateway = new RecordingGateway(
            Response(200, """{"cancer_risk":{"nice_category":"moderate"}}"""));

        var payload = await Client(gateway).CalculateNiceAsync(PedigreeId, CancellationToken.None);

        var call = gateway.Calls[0];
        Assert.Equal("https://evagene.example/api/pedigrees/pedigree-1/risk/calculate", call.Url);
        using var body = JsonDocument.Parse(call.Body!);
        Assert.Equal("NICE", body.RootElement.GetProperty("model").GetString());
        Assert.Equal("moderate", payload.GetProperty("cancer_risk").GetProperty("nice_category").GetString());
    }

    [Fact]
    public async Task Delete_pedigree_sends_delete()
    {
        var gateway = new RecordingGateway(Response(204, string.Empty));

        await Client(gateway).DeletePedigreeAsync(PedigreeId, CancellationToken.None);

        var call = gateway.Calls[0];
        Assert.Equal(HttpMethod.Delete, call.Method);
        Assert.Equal("https://evagene.example/api/pedigrees/pedigree-1", call.Url);
    }

    [Fact]
    public async Task Non_2xx_status_is_api_exception()
    {
        var gateway = new RecordingGateway(Response(500, """{"detail":"boom"}"""));

        await Assert.ThrowsAsync<EvageneApiException>(
            () => Client(gateway).CreatePedigreeAsync("Smith family", CancellationToken.None));
    }

    [Fact]
    public async Task Transport_failure_is_api_exception()
    {
        var gateway = new ExplodingGateway();

        await Assert.ThrowsAsync<EvageneApiException>(
            () => Client(gateway).CreatePedigreeAsync("Smith family", CancellationToken.None));
    }

    private static EvageneClient Client(IHttpGateway gateway) =>
        new("https://evagene.example", "evg_test", gateway);

    private static HttpResponsePayload Response(int status, string body) => new(status, body);

    private sealed record Call(
        HttpMethod Method,
        string Url,
        IReadOnlyDictionary<string, string> Headers,
        string? Body);

    private sealed class RecordingGateway : IHttpGateway
    {
        private readonly HttpResponsePayload response;

        public List<Call> Calls { get; } = new();

        public RecordingGateway(HttpResponsePayload response)
        {
            this.response = response;
        }

        public Task<HttpResponsePayload> SendAsync(
            HttpMethod method,
            string url,
            IReadOnlyDictionary<string, string> headers,
            string? jsonBody,
            CancellationToken cancellationToken = default)
        {
            this.Calls.Add(new Call(method, url, headers, jsonBody));
            return Task.FromResult(this.response);
        }
    }

    private sealed class ExplodingGateway : IHttpGateway
    {
        public Task<HttpResponsePayload> SendAsync(
            HttpMethod method,
            string url,
            IReadOnlyDictionary<string, string> headers,
            string? jsonBody,
            CancellationToken cancellationToken = default)
        {
            throw new HttpRequestException("DNS failed");
        }
    }
}
