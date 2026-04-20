using System.Text.Json;

using Xunit;

namespace FamilyIntake.Tests;

public sealed class EvageneClientTests
{
    private const string PedigreeId = "11111111-1111-1111-1111-111111111111";
    private const string IndividualId = "22222222-2222-2222-2222-222222222222";

    [Fact]
    public async Task CreatePedigree_posts_display_name_and_returns_id()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            Status: 201,
            JsonBody: $$"""{ "id": "{{PedigreeId}}" }"""));

        var id = await Client(gateway).CreatePedigreeAsync(new CreatePedigreeArgs("Emma\u2019s family"));

        Assert.Equal(PedigreeId, id);
        var call = gateway.OnlyCall();
        Assert.Equal(HttpMethodKind.Post, call.Method);
        Assert.Equal("https://evagene.example/api/pedigrees", call.Url);
        Assert.Equal("evg_test", call.Headers["X-API-Key"]);
        using var body = JsonDocument.Parse(call.JsonBody);
        Assert.Equal("Emma\u2019s family", body.RootElement.GetProperty("display_name").GetString());
    }

    [Fact]
    public async Task CreateIndividual_includes_biological_sex_and_optional_year()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(201, $$"""{ "id": "{{IndividualId}}" }"""));

        await Client(gateway).CreateIndividualAsync(new CreateIndividualArgs(
            DisplayName: "Emma",
            BiologicalSex: BiologicalSex.Female,
            YearOfBirth: 1985));

        using var body = JsonDocument.Parse(gateway.OnlyCall().JsonBody);
        Assert.Equal("Emma", body.RootElement.GetProperty("display_name").GetString());
        Assert.Equal("female", body.RootElement.GetProperty("biological_sex").GetString());
        Assert.Equal(1985, body.RootElement.GetProperty("properties").GetProperty("year_of_birth").GetInt32());
    }

    [Fact]
    public async Task DesignateAsProband_patches_proband_flag_on_the_individual()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(200, $$"""{ "id": "{{IndividualId}}" }"""));

        await Client(gateway).DesignateAsProbandAsync(IndividualId);

        var call = gateway.OnlyCall();
        Assert.Equal(HttpMethodKind.Patch, call.Method);
        Assert.Equal($"https://evagene.example/api/individuals/{IndividualId}", call.Url);
        using var body = JsonDocument.Parse(call.JsonBody);
        Assert.Equal(1, body.RootElement.GetProperty("proband").GetInt32());
    }

    [Fact]
    public async Task AddRelative_returns_the_new_individual_id()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            201,
            $$"""{ "individual": { "id": "{{IndividualId}}" } }"""));

        var id = await Client(gateway).AddRelativeAsync(new AddRelativeArgs(
            PedigreeId: PedigreeId,
            RelativeOf: "proband-id",
            RelativeType: RelativeType.Mother,
            DisplayName: "Grace",
            BiologicalSex: BiologicalSex.Female));

        Assert.Equal(IndividualId, id);
        var call = gateway.OnlyCall();
        Assert.Equal(
            $"https://evagene.example/api/pedigrees/{PedigreeId}/register/add-relative",
            call.Url);
        using var body = JsonDocument.Parse(call.JsonBody);
        Assert.Equal("proband-id", body.RootElement.GetProperty("relative_of").GetString());
        Assert.Equal("mother", body.RootElement.GetProperty("relative_type").GetString());
        Assert.Equal("Grace", body.RootElement.GetProperty("display_name").GetString());
        Assert.Equal("female", body.RootElement.GetProperty("biological_sex").GetString());
        Assert.False(body.RootElement.TryGetProperty("properties", out _));
    }

    [Fact]
    public async Task AddIndividualToPedigree_tolerates_empty_response_body()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(204, ""));

        await Client(gateway).AddIndividualToPedigreeAsync(PedigreeId, IndividualId);

        var call = gateway.OnlyCall();
        Assert.Equal(HttpMethodKind.Post, call.Method);
        Assert.Equal(
            $"https://evagene.example/api/pedigrees/{PedigreeId}/individuals/{IndividualId}",
            call.Url);
    }

    [Fact]
    public async Task DesignateAsProband_tolerates_empty_response_body()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(204, ""));

        await Client(gateway).DesignateAsProbandAsync(IndividualId);

        var call = gateway.OnlyCall();
        Assert.Equal(HttpMethodKind.Patch, call.Method);
        Assert.Equal($"https://evagene.example/api/individuals/{IndividualId}", call.Url);
        using var body = JsonDocument.Parse(call.JsonBody);
        Assert.Equal(1, body.RootElement.GetProperty("proband").GetInt32());
    }

    [Fact]
    public async Task Non_2xx_response_raises_api_exception()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(500, "{}"));

        await Assert.ThrowsAsync<EvageneApiException>(
            () => Client(gateway).CreatePedigreeAsync(new CreatePedigreeArgs("Emma")));
    }

    [Fact]
    public async Task Response_missing_id_raises_api_exception()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(201, """{"not_id":"x"}"""));

        await Assert.ThrowsAsync<EvageneApiException>(
            () => Client(gateway).CreatePedigreeAsync(new CreatePedigreeArgs("Emma")));
    }

    private static EvageneClient Client(IHttpGateway gateway) =>
        new("https://evagene.example", "evg_test", gateway);

    private sealed class RecordingGateway : IHttpGateway
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
}
