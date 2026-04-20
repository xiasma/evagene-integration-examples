using System.Text.Json;

using Xunit;

namespace FhirBridge.Tests;

public sealed class EvageneClientTests
{
    private const string PedigreeId = "11111111-1111-1111-1111-111111111111";
    private const string IndividualId = "22222222-2222-2222-2222-222222222222";

    [Fact]
    public async Task GetPedigreeDetail_issues_get_with_api_key()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(200, $$"""{"id":"{{PedigreeId}}"}"""));

        var payload = await Client(gateway).GetPedigreeDetailAsync(PedigreeId);

        Assert.Equal(PedigreeId, payload.GetProperty("id").GetString());
        var call = gateway.OnlyCall();
        Assert.Equal(HttpMethodKind.Get, call.Method);
        Assert.Equal($"https://evagene.example/api/pedigrees/{PedigreeId}", call.Url);
        Assert.Equal("evg_test", call.Headers["X-API-Key"]);
    }

    [Fact]
    public async Task CreatePedigree_posts_display_name_and_returns_id()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(201, $$"""{"id":"{{PedigreeId}}"}"""));

        var id = await Client(gateway).CreatePedigreeAsync(new CreatePedigreeArgs("Emma"));

        Assert.Equal(PedigreeId, id);
        var call = gateway.OnlyCall();
        Assert.Equal(HttpMethodKind.Post, call.Method);
        using var body = JsonDocument.Parse(call.Body!);
        Assert.Equal("Emma", body.RootElement.GetProperty("display_name").GetString());
    }

    [Fact]
    public async Task AddRelative_returns_new_individual_id()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            201,
            $"{{\"individual\":{{\"id\":\"{IndividualId}\"}}}}"));

        var id = await Client(gateway).AddRelativeAsync(new AddRelativeArgs(
            PedigreeId,
            "proband",
            RelativeType.Mother,
            "Grace",
            BiologicalSex.Female));

        Assert.Equal(IndividualId, id);
    }

    [Fact]
    public async Task DeletePedigree_issues_delete()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(204, string.Empty));

        await Client(gateway).DeletePedigreeAsync(PedigreeId);

        var call = gateway.OnlyCall();
        Assert.Equal(HttpMethodKind.Delete, call.Method);
        Assert.Equal($"https://evagene.example/api/pedigrees/{PedigreeId}", call.Url);
    }

    [Fact]
    public async Task Non_2xx_raises()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(500, "{}"));

        await Assert.ThrowsAsync<EvageneApiException>(
            () => Client(gateway).CreatePedigreeAsync(new CreatePedigreeArgs("Emma")));
    }

    private static EvageneClient Client(IHttpGateway gateway) =>
        new("https://evagene.example", "evg_test", gateway);
}
