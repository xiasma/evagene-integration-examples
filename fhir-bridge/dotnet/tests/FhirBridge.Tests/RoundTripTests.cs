using System.Text;
using System.Text.Json;

using Xunit;

namespace FhirBridge.Tests;

public sealed class RoundTripTests
{
    private const string PedigreeId = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
    private const string FhirBase = "https://fhir.example/fhir";
    private const string EvageneBase = "https://evagene.example";

    [Fact]
    public async Task Push_then_pull_reconstructs_the_family()
    {
        var fhir = new FhirSimulator();
        var evagene = new EvageneSimulator();
        var gateway = new RoutingGateway(fhir, evagene);
        var env = new Dictionary<string, string?>(StringComparer.Ordinal)
        {
            ["EVAGENE_API_KEY"] = "evg_test",
            ["EVAGENE_BASE_URL"] = EvageneBase,
        };
        var stdout = new StringWriter();
        var stderr = new StringWriter();

        var pushExit = await App.RunAsync(
            new[] { "push", PedigreeId, "--to", FhirBase },
            env, stdout, stderr, gateway);

        Assert.Equal(0, pushExit);
        Assert.Contains("wrote 6 FamilyMemberHistory resources", stdout.ToString(), StringComparison.Ordinal);
        Assert.Contains("skipped Sam Park", stdout.ToString(), StringComparison.Ordinal);

        var pullExit = await App.RunAsync(
            new[] { "pull", "p-proband", "--from", FhirBase },
            env, stdout, stderr, gateway);

        Assert.Equal(0, pullExit);
        Assert.Equal("created-pedigree", evagene.CreatedPedigreeId);
        Assert.Equal(6, evagene.AddRelativeBodies.Count);
        var relativeTypes = evagene.AddRelativeBodies
            .Select(body => JsonDocument.Parse(body).RootElement.GetProperty("relative_type").GetString() ?? string.Empty)
            .OrderBy(s => s, StringComparer.Ordinal)
            .ToList();
        Assert.Equal(new[]
        {
            "brother", "father", "maternal_grandfather", "maternal_grandmother", "mother", "son",
        }, relativeTypes);
    }

    private sealed class FhirSimulator
    {
        private readonly Dictionary<string, List<StoredResource>> byPatient = new(StringComparer.Ordinal);
        private int nextId = 1;

        public HttpResponsePayload Handle(HttpRequestDescriptor request)
        {
            if (request.Method == HttpMethodKind.Post && request.Url == FhirBase)
            {
                return this.AcceptTransaction(request);
            }
            if (request.Method == HttpMethodKind.Get && request.Url.StartsWith($"{FhirBase}/FamilyMemberHistory", StringComparison.Ordinal))
            {
                return this.Search(request);
            }
            return new HttpResponsePayload(404, """{"resourceType":"OperationOutcome"}""");
        }

        private HttpResponsePayload AcceptTransaction(HttpRequestDescriptor request)
        {
            using var doc = JsonDocument.Parse(request.Body ?? "{}");
            var responseEntries = new StringBuilder();
            responseEntries.Append("""{"resourceType":"Bundle","type":"transaction-response","entry":[""");
            var first = true;
            foreach (var entry in doc.RootElement.GetProperty("entry").EnumerateArray())
            {
                var resource = entry.GetProperty("resource");
                var id = $"fmh-{this.nextId++}";
                var patientRef = resource.GetProperty("patient").GetProperty("reference").GetString() ?? string.Empty;
                if (!this.byPatient.TryGetValue(patientRef, out var list))
                {
                    list = new List<StoredResource>();
                    this.byPatient[patientRef] = list;
                }
                list.Add(new StoredResource(id, resource.GetRawText()));
                if (!first) responseEntries.Append(',');
                first = false;
                responseEntries.Append($"{{\"response\":{{\"status\":\"201 Created\",\"location\":\"FamilyMemberHistory/{id}\"}}}}");
            }
            responseEntries.Append("]}");
            return new HttpResponsePayload(200, responseEntries.ToString());
        }

        private HttpResponsePayload Search(HttpRequestDescriptor request)
        {
            var uri = new Uri(request.Url);
            var patientId = System.Web.HttpUtility.ParseQueryString(uri.Query)["patient"] ?? string.Empty;
            var key = $"Patient/{patientId}";
            var stored = this.byPatient.TryGetValue(key, out var list) ? list : new List<StoredResource>();
            var sb = new StringBuilder();
            sb.Append("""{"resourceType":"Bundle","type":"searchset","entry":[""");
            for (var i = 0; i < stored.Count; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append("""{"resource":""").Append(stored[i].Body).Append('}');
            }
            sb.Append("]}");
            return new HttpResponsePayload(200, sb.ToString());
        }

        private sealed record StoredResource(string Id, string Body);
    }

    private sealed class EvageneSimulator
    {
        public string? CreatedPedigreeId { get; private set; }
        public List<string> AddRelativeBodies { get; } = new();
        private int individualCounter;

        public HttpResponsePayload Handle(HttpRequestDescriptor request)
        {
            if (request.Method == HttpMethodKind.Get && request.Url == $"{EvageneBase}/api/pedigrees/{PedigreeId}")
            {
                return new HttpResponsePayload(200, Fixtures.LoadPedigreeDetailJson());
            }
            if (request.Method == HttpMethodKind.Post && request.Url == $"{EvageneBase}/api/pedigrees")
            {
                this.CreatedPedigreeId = "created-pedigree";
                return new HttpResponsePayload(201, $$"""{"id":"{{this.CreatedPedigreeId}}"}""");
            }
            if (request.Method == HttpMethodKind.Post && request.Url == $"{EvageneBase}/api/individuals")
            {
                var id = $"ind-{++this.individualCounter}";
                return new HttpResponsePayload(201, $$"""{"id":"{{id}}"}""");
            }
            if (request.Method == HttpMethodKind.Post &&
                request.Url.StartsWith($"{EvageneBase}/api/pedigrees/", StringComparison.Ordinal) &&
                request.Url.EndsWith("/register/add-relative", StringComparison.Ordinal))
            {
                this.AddRelativeBodies.Add(request.Body ?? string.Empty);
                var id = $"rel-{this.AddRelativeBodies.Count}";
                return new HttpResponsePayload(201, $"{{\"individual\":{{\"id\":\"{id}\"}}}}");
            }
            if (request.Method == HttpMethodKind.Patch && request.Url.StartsWith($"{EvageneBase}/api/individuals/", StringComparison.Ordinal))
            {
                var id = request.Url[$"{EvageneBase}/api/individuals/".Length..];
                return new HttpResponsePayload(200, $$"""{"id":"{{id}}"}""");
            }
            if (request.Method == HttpMethodKind.Post &&
                request.Url.StartsWith($"{EvageneBase}/api/pedigrees/", StringComparison.Ordinal) &&
                request.Url.Contains("/individuals/", StringComparison.Ordinal))
            {
                return new HttpResponsePayload(204, "{}");
            }
            return new HttpResponsePayload(404, "{}");
        }
    }

    private sealed class RoutingGateway : IHttpGateway
    {
        private readonly FhirSimulator fhir;
        private readonly EvageneSimulator evagene;

        public RoutingGateway(FhirSimulator fhir, EvageneSimulator evagene)
        {
            this.fhir = fhir;
            this.evagene = evagene;
        }

        public Task<HttpResponsePayload> SendAsync(HttpRequestDescriptor request, CancellationToken cancellationToken = default)
        {
            if (request.Url.StartsWith(EvageneBase, StringComparison.Ordinal))
            {
                return Task.FromResult(this.evagene.Handle(request));
            }
            if (request.Url.StartsWith(FhirBase, StringComparison.Ordinal))
            {
                return Task.FromResult(this.fhir.Handle(request));
            }
            return Task.FromResult(new HttpResponsePayload(404, "{}"));
        }
    }
}
