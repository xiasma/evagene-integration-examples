namespace FamilyIntake;

/// <summary>
/// Orchestrates the sequence of Evagene REST calls that turn a validated
/// IntakeSubmission into a persisted pedigree with relatives wired up.
///
/// No HTTP knowledge -- only the IEvageneApi interface. The order of
/// calls is load-bearing: grandparents depend on parents existing first
/// (the relative_of field points at an already-created individual).
/// </summary>
public sealed record IntakeCreationResult(string PedigreeId, string ProbandId, int RelativesAdded);

public sealed class IntakeService
{
    private readonly IEvageneApi client;

    public IntakeService(IEvageneApi client)
    {
        this.client = client;
    }

    public async Task<IntakeCreationResult> CreateAsync(
        IntakeSubmission submission,
        CancellationToken cancellationToken = default)
    {
        var pedigreeId = await this.client.CreatePedigreeAsync(
            new CreatePedigreeArgs($"{submission.Proband.DisplayName}'s family"),
            cancellationToken).ConfigureAwait(false);
        var probandId = await this.client.CreateIndividualAsync(
            new CreateIndividualArgs(
                submission.Proband.DisplayName,
                submission.Proband.BiologicalSex,
                submission.Proband.YearOfBirth),
            cancellationToken).ConfigureAwait(false);
        await this.client.AddIndividualToPedigreeAsync(pedigreeId, probandId, cancellationToken).ConfigureAwait(false);
        await this.client.DesignateAsProbandAsync(probandId, cancellationToken).ConfigureAwait(false);

        var motherId = await this.MaybeAddRelativeAsync(
            pedigreeId, probandId, RelativeType.Mother, BiologicalSex.Female,
            submission.Mother, cancellationToken).ConfigureAwait(false);
        var fatherId = await this.MaybeAddRelativeAsync(
            pedigreeId, probandId, RelativeType.Father, BiologicalSex.Male,
            submission.Father, cancellationToken).ConfigureAwait(false);

        var relativesAdded = CountAdded(motherId, fatherId);

        if (motherId is not null)
        {
            relativesAdded += await this.AddGrandparentsAsync(
                pedigreeId, motherId,
                submission.MaternalGrandmother, submission.MaternalGrandfather,
                cancellationToken).ConfigureAwait(false);
        }
        if (fatherId is not null)
        {
            relativesAdded += await this.AddGrandparentsAsync(
                pedigreeId, fatherId,
                submission.PaternalGrandmother, submission.PaternalGrandfather,
                cancellationToken).ConfigureAwait(false);
        }
        relativesAdded += await this.AddSiblingsAsync(
            pedigreeId, probandId, submission.Siblings, cancellationToken).ConfigureAwait(false);

        return new IntakeCreationResult(pedigreeId, probandId, relativesAdded);
    }

    private async Task<int> AddGrandparentsAsync(
        string pedigreeId,
        string parentId,
        RelativeEntry? grandmother,
        RelativeEntry? grandfather,
        CancellationToken cancellationToken)
    {
        var grandmotherId = await this.MaybeAddRelativeAsync(
            pedigreeId, parentId, RelativeType.Mother, BiologicalSex.Female,
            grandmother, cancellationToken).ConfigureAwait(false);
        var grandfatherId = await this.MaybeAddRelativeAsync(
            pedigreeId, parentId, RelativeType.Father, BiologicalSex.Male,
            grandfather, cancellationToken).ConfigureAwait(false);
        return CountAdded(grandmotherId, grandfatherId);
    }

    private async Task<int> AddSiblingsAsync(
        string pedigreeId,
        string probandId,
        IReadOnlyList<SiblingEntry> siblings,
        CancellationToken cancellationToken)
    {
        var added = 0;
        foreach (var sibling in siblings)
        {
            await this.client.AddRelativeAsync(
                new AddRelativeArgs(
                    pedigreeId,
                    probandId,
                    RelativeTypeForSibling(sibling.Relation),
                    sibling.DisplayName,
                    sibling.BiologicalSex,
                    sibling.YearOfBirth),
                cancellationToken).ConfigureAwait(false);
            added += 1;
        }
        return added;
    }

    private async Task<string?> MaybeAddRelativeAsync(
        string pedigreeId,
        string relativeOf,
        RelativeType relativeType,
        BiologicalSex biologicalSex,
        RelativeEntry? entry,
        CancellationToken cancellationToken)
    {
        if (entry is null)
        {
            return null;
        }
        return await this.client.AddRelativeAsync(
            new AddRelativeArgs(
                pedigreeId,
                relativeOf,
                relativeType,
                entry.DisplayName,
                biologicalSex,
                entry.YearOfBirth),
            cancellationToken).ConfigureAwait(false);
    }

    private static RelativeType RelativeTypeForSibling(SiblingRelation relation) => relation switch
    {
        SiblingRelation.Sister => RelativeType.Sister,
        SiblingRelation.Brother => RelativeType.Brother,
        SiblingRelation.HalfSister => RelativeType.HalfSister,
        SiblingRelation.HalfBrother => RelativeType.HalfBrother,
        _ => throw new ArgumentOutOfRangeException(nameof(relation)),
    };

    private static int CountAdded(params string?[] ids)
    {
        var count = 0;
        foreach (var id in ids)
        {
            if (id is not null)
            {
                count += 1;
            }
        }
        return count;
    }
}
