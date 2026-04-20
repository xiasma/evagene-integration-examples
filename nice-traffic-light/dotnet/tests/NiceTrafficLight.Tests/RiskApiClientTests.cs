using System.Text.Json;

using Xunit;

namespace NiceTrafficLight.Tests;

public sealed class RiskApiClientTests
{
    private const string PedigreeId = "11111111-1111-1111-1111-111111111111";
    private const string CounseleeId = "22222222-2222-2222-2222-222222222222";

    [Fact]
    public async Task Posts_nice_model_to_risk_calculate()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            Status: 200,
            JsonBody: """{"cancer_risk": {"nice_category": "near_population"}}"""));

        await Client(gateway).CalculateNiceAsync(new CalculateNiceArgs(PedigreeId));

        Assert.Equal(
            $"https://evagene.example/api/pedigrees/{PedigreeId}/risk/calculate",
            gateway.LastUrl);
        Assert.Equal("evg_test", gateway.LastHeaders["X-API-Key"]);
        using var body = JsonDocument.Parse(gateway.LastBody);
        Assert.Equal("NICE", body.RootElement.GetProperty("model").GetString());
        Assert.False(body.RootElement.TryGetProperty("counselee_id", out _));
    }

    [Fact]
    public async Task Includes_counselee_id_when_provided()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(200, "{}"));

        await Client(gateway).CalculateNiceAsync(new CalculateNiceArgs(PedigreeId, CounseleeId));

        using var body = JsonDocument.Parse(gateway.LastBody);
        Assert.Equal(CounseleeId, body.RootElement.GetProperty("counselee_id").GetString());
    }

    [Fact]
    public async Task Throws_api_error_on_non_2xx_status()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(500, "{}"));

        await Assert.ThrowsAsync<ApiException>(
            () => Client(gateway).CalculateNiceAsync(new CalculateNiceArgs(PedigreeId)));
    }

    [Fact]
    public async Task Throws_api_error_on_non_object_payload()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(200, """["not", "an", "object"]"""));

        await Assert.ThrowsAsync<ApiException>(
            () => Client(gateway).CalculateNiceAsync(new CalculateNiceArgs(PedigreeId)));
    }

    private static RiskApiClient Client(IHttpGateway gateway) =>
        new("https://evagene.example", "evg_test", gateway);

    private sealed class RecordingGateway : IHttpGateway
    {
        private readonly HttpResponsePayload response;

        public string LastUrl { get; private set; } = string.Empty;
        public IReadOnlyDictionary<string, string> LastHeaders { get; private set; } =
            new Dictionary<string, string>();
        public string LastBody { get; private set; } = string.Empty;

        public RecordingGateway(HttpResponsePayload response)
        {
            this.response = response;
        }

        public Task<HttpResponsePayload> PostJsonAsync(
            string url,
            IReadOnlyDictionary<string, string> headers,
            string jsonBody,
            CancellationToken cancellationToken = default)
        {
            this.LastUrl = url;
            this.LastHeaders = headers;
            this.LastBody = jsonBody;
            return Task.FromResult(this.response);
        }
    }
}
