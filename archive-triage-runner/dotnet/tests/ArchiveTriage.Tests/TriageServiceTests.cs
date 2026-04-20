using System.Text.Json;

using Xunit;

namespace ArchiveTriage.Tests;

public sealed class TriageServiceTests
{
    private static readonly JsonElement HappyPayload = JsonDocument.Parse("""
        {
            "counselee_name": "Jane Doe",
            "cancer_risk": {
                "nice_category": "high",
                "nice_refer_genetics": true,
                "nice_triggers": ["trigger A", "trigger B"]
            }
        }
        """).RootElement.Clone();

    [Fact]
    public async Task Happy_path_emits_one_row_per_file_with_trigger_count()
    {
        var client = new FakeClient(HappyPayload) { CreatedIds = new Queue<string>(new[] { "pedigree-1" }) };

        var rows = await CollectAsync(Service(client).TriageAsync(new[] { File("family.ged") }));

        Assert.Single(rows);
        Assert.Equal("pedigree-1", rows[0].PedigreeId);
        Assert.Equal("Jane Doe", rows[0].ProbandName);
        Assert.Equal("high", rows[0].Category);
        Assert.Equal(true, rows[0].ReferForGenetics);
        Assert.Equal(2, rows[0].TriggersMatchedCount);
        Assert.Empty(rows[0].Error);
    }

    [Fact]
    public async Task Display_name_comes_from_filename_stem()
    {
        var client = new FakeClient(HappyPayload) { CreatedIds = new Queue<string>(new[] { "pedigree-1" }) };

        await CollectAsync(Service(client).TriageAsync(new[] { File("smith-family.ged") }));

        Assert.Equal(new[] { "smith-family" }, client.CreatedCalls);
    }

    [Fact]
    public async Task Missing_proband_produces_failure_row_without_running_risk()
    {
        var client = new FakeClient(HappyPayload)
        {
            CreatedIds = new Queue<string>(new[] { "pedigree-1" }),
            HasProbandResult = false,
        };

        var rows = await CollectAsync(Service(client).TriageAsync(new[] { File("family.ged") }));

        Assert.StartsWith("no proband", rows[0].Error, StringComparison.Ordinal);
        Assert.Empty(rows[0].Category);
        Assert.Equal(0, rows[0].TriggersMatchedCount);
        Assert.False(client.CalculateNiceWasCalled);
    }

    [Fact]
    public async Task Create_pedigree_failure_produces_row_with_empty_pedigree_id()
    {
        var client = new FakeClient(HappyPayload)
        {
            CreateRaises = new EvageneApiException("HTTP 503"),
        };

        var rows = await CollectAsync(Service(client).TriageAsync(new[] { File("family.ged") }));

        Assert.Empty(rows[0].PedigreeId);
        Assert.Equal("family", rows[0].ProbandName);
        Assert.Contains("create_pedigree failed", rows[0].Error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Risk_calculation_failure_preserves_pedigree_id_in_row()
    {
        var client = new FakeClient(HappyPayload)
        {
            CreatedIds = new Queue<string>(new[] { "pedigree-1" }),
            CalculateRaises = new EvageneApiException("HTTP 500"),
        };

        var rows = await CollectAsync(Service(client).TriageAsync(new[] { File("family.ged") }));

        Assert.Equal("pedigree-1", rows[0].PedigreeId);
        Assert.Contains("calculate_nice failed", rows[0].Error, StringComparison.Ordinal);
    }

    [Fact]
    public async Task Every_file_gets_a_row_for_happy_path_batch()
    {
        var client = new FakeClient(HappyPayload)
        {
            CreatedIds = new Queue<string>(new[] { "pedigree-1", "pedigree-2" }),
        };

        var rows = await CollectAsync(
            Service(client).TriageAsync(new[] { File("a.ged"), File("b.ged") }));

        Assert.Equal(2, rows.Count);
    }

    private static GedcomFile File(string name) => new(Path: name, Content: $"{name}-content");

    private static TriageService Service(FakeClient client) =>
        new(client, new TriageOptions(Concurrency: 1));

    private static async Task<List<RowResult>> CollectAsync(IAsyncEnumerable<RowResult> source)
    {
        var list = new List<RowResult>();
        await foreach (var row in source)
        {
            list.Add(row);
        }
        return list;
    }

    private sealed class FakeClient : IEvageneApi
    {
        private readonly JsonElement nicePayload;

        public Queue<string> CreatedIds { get; set; } = new();
        public bool HasProbandResult { get; set; } = true;
        public Exception? CreateRaises { get; set; }
        public Exception? CalculateRaises { get; set; }
        public List<string> CreatedCalls { get; } = new();
        public bool CalculateNiceWasCalled { get; private set; }

        public FakeClient(JsonElement nicePayload)
        {
            this.nicePayload = nicePayload;
        }

        public Task<string> CreatePedigreeAsync(string displayName, CancellationToken cancellationToken)
        {
            if (this.CreateRaises is not null) throw this.CreateRaises;
            this.CreatedCalls.Add(displayName);
            return Task.FromResult(this.CreatedIds.Dequeue());
        }

        public Task ImportGedcomAsync(string pedigreeId, string gedcomText, CancellationToken cancellationToken) =>
            Task.CompletedTask;

        public Task<bool> HasProbandAsync(string pedigreeId, CancellationToken cancellationToken) =>
            Task.FromResult(this.HasProbandResult);

        public Task<JsonElement> CalculateNiceAsync(string pedigreeId, CancellationToken cancellationToken)
        {
            if (this.CalculateRaises is not null) throw this.CalculateRaises;
            this.CalculateNiceWasCalled = true;
            return Task.FromResult(this.nicePayload);
        }

        public Task DeletePedigreeAsync(string pedigreeId, CancellationToken cancellationToken) =>
            Task.CompletedTask;
    }
}
