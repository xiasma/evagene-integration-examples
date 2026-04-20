using Xunit;

namespace FamilyIntake.Tests;

public sealed class IntakeServiceTests
{
    [Fact]
    public async Task Proband_only_submission_creates_pedigree_individual_adds_designates()
    {
        var client = new RecordingClient();

        var result = await new IntakeService(client).CreateAsync(Submission());

        Assert.Equal(
            new[] { "CreatePedigree", "CreateIndividual", "AddIndividualToPedigree", "DesignateAsProband" },
            client.Operations);
        Assert.Equal(0, result.RelativesAdded);
        Assert.Equal("id-0001", result.PedigreeId);
        Assert.Equal("id-0002", result.ProbandId);
    }

    [Fact]
    public async Task Mother_and_father_are_added_before_their_respective_grandparents()
    {
        var client = new RecordingClient();

        await new IntakeService(client).CreateAsync(Submission() with
        {
            Mother = new RelativeEntry("Grace"),
            Father = new RelativeEntry("Henry"),
            MaternalGrandmother = new RelativeEntry("Edith"),
            PaternalGrandfather = new RelativeEntry("Arthur"),
        });

        var relatives = client.AddRelativeCalls
            .Select(a => (a.RelativeType, a.DisplayName))
            .ToArray();
        Assert.Equal(
            new[]
            {
                (RelativeType.Mother, "Grace"),
                (RelativeType.Father, "Henry"),
                (RelativeType.Mother, "Edith"),
                (RelativeType.Father, "Arthur"),
            },
            relatives);
    }

    [Fact]
    public async Task Grandparent_on_a_side_with_no_parent_is_skipped()
    {
        var client = new RecordingClient();

        await new IntakeService(client).CreateAsync(Submission() with
        {
            MaternalGrandmother = new RelativeEntry("Edith"),
        });

        Assert.Empty(client.AddRelativeCalls);
    }

    [Fact]
    public async Task Siblings_come_last_and_carry_biological_sex_derived_from_relation()
    {
        var client = new RecordingClient();

        var result = await new IntakeService(client).CreateAsync(Submission() with
        {
            Siblings = new[]
            {
                new SiblingEntry("Alice", SiblingRelation.Sister, BiologicalSex.Female),
                new SiblingEntry("Bob", SiblingRelation.Brother, BiologicalSex.Male),
            },
        });

        var siblingCalls = client.AddRelativeCalls
            .Where(a => a.RelativeType is RelativeType.Sister or RelativeType.Brother)
            .ToArray();
        Assert.Equal(2, siblingCalls.Length);
        Assert.Equal(2, result.RelativesAdded);
    }

    [Fact]
    public async Task RelativesAdded_counts_every_successful_add_relative_call()
    {
        var client = new RecordingClient();

        var result = await new IntakeService(client).CreateAsync(Submission() with
        {
            Mother = new RelativeEntry("Grace"),
            Father = new RelativeEntry("Henry"),
            MaternalGrandmother = new RelativeEntry("Edith"),
            MaternalGrandfather = new RelativeEntry("Cecil"),
            PaternalGrandmother = new RelativeEntry("Margaret"),
            PaternalGrandfather = new RelativeEntry("Arthur"),
            Siblings = new[]
            {
                new SiblingEntry("Alice", SiblingRelation.Sister, BiologicalSex.Female),
            },
        });

        Assert.Equal(7, result.RelativesAdded);
    }

    private static IntakeSubmission Submission()
    {
        return new IntakeSubmission(
            Proband: new ProbandEntry("Emma", BiologicalSex.Female),
            Siblings: Array.Empty<SiblingEntry>());
    }

    private sealed class RecordingClient : IEvageneApi
    {
        private readonly List<string> operations = new();
        private readonly List<AddRelativeArgs> addRelativeCalls = new();
        private int nextId = 1;

        public IReadOnlyList<string> Operations => this.operations;
        public IReadOnlyList<AddRelativeArgs> AddRelativeCalls => this.addRelativeCalls;

        public Task<string> CreatePedigreeAsync(CreatePedigreeArgs args, CancellationToken cancellationToken = default)
        {
            this.operations.Add("CreatePedigree");
            return Task.FromResult(this.IssueId());
        }

        public Task<string> CreateIndividualAsync(CreateIndividualArgs args, CancellationToken cancellationToken = default)
        {
            this.operations.Add("CreateIndividual");
            return Task.FromResult(this.IssueId());
        }

        public Task AddIndividualToPedigreeAsync(string pedigreeId, string individualId, CancellationToken cancellationToken = default)
        {
            this.operations.Add("AddIndividualToPedigree");
            return Task.CompletedTask;
        }

        public Task DesignateAsProbandAsync(string individualId, CancellationToken cancellationToken = default)
        {
            this.operations.Add("DesignateAsProband");
            return Task.CompletedTask;
        }

        public Task<string> AddRelativeAsync(AddRelativeArgs args, CancellationToken cancellationToken = default)
        {
            this.operations.Add("AddRelative");
            this.addRelativeCalls.Add(args);
            return Task.FromResult(this.IssueId());
        }

        private string IssueId()
        {
            var id = $"id-{this.nextId:D4}";
            this.nextId += 1;
            return id;
        }
    }
}
