using System.Text.Json;

using Xunit;

namespace FhirBridge.Tests;

public sealed class FhirClientTests
{
    [Fact]
    public async Task FetchForPatient_issues_get_with_fhir_accept()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            200,
            """{"resourceType":"Bundle","type":"searchset","entry":[]}"""));

        var client = new FhirClient("https://fhir.example/fhir", gateway);

        var bundle = await client.FetchFamilyHistoryForPatientAsync("p1");

        Assert.Equal("Bundle", bundle.GetProperty("resourceType").GetString());
        var call = gateway.OnlyCall();
        Assert.Equal(HttpMethodKind.Get, call.Method);
        Assert.Equal("https://fhir.example/fhir/FamilyMemberHistory?patient=p1", call.Url);
        Assert.Equal("application/fhir+json", call.Headers["Accept"]);
    }

    [Fact]
    public async Task FetchForPatient_rejects_non_searchset_bundle()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            200,
            """{"resourceType":"Bundle","type":"transaction-response","entry":[]}"""));

        var client = new FhirClient("https://fhir.example", gateway);

        await Assert.ThrowsAsync<FhirApiException>(() => client.FetchFamilyHistoryForPatientAsync("p1"));
    }

    [Fact]
    public async Task PostTransactionBundle_sends_post_to_base_url()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            200,
            """{"resourceType":"Bundle","type":"transaction-response","entry":[]}"""));
        var client = new FhirClient("https://fhir.example/fhir", gateway);

        var txBody = """{"resourceType":"Bundle","type":"transaction","entry":[]}""";
        await client.PostTransactionBundleAsync(txBody);

        var call = gateway.OnlyCall();
        Assert.Equal(HttpMethodKind.Post, call.Method);
        Assert.Equal("https://fhir.example/fhir", call.Url);
        Assert.Equal(txBody, call.Body);
    }

    [Fact]
    public async Task Auth_header_is_forwarded()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(
            200,
            """{"resourceType":"Bundle","type":"searchset"}"""));
        var client = new FhirClient("https://fhir.example", gateway, "Authorization: Bearer xyz");

        await client.FetchFamilyHistoryForPatientAsync("p1");

        Assert.Equal("Bearer xyz", gateway.OnlyCall().Headers["Authorization"]);
    }

    [Fact]
    public async Task Non_2xx_raises()
    {
        var gateway = new RecordingGateway(new HttpResponsePayload(503, string.Empty));
        var client = new FhirClient("https://fhir.example", gateway);

        await Assert.ThrowsAsync<FhirApiException>(() => client.FetchFamilyHistoryForPatientAsync("p1"));
    }
}
