namespace FhirBridge;

/// <summary>
/// Orchestrates the REST calls that turn an IntakeFamily into a fresh
/// Evagene pedigree with a proband and all its relatives attached.
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
        IntakeFamily family,
        CancellationToken cancellationToken = default)
    {
        var pedigreeId = await this.client.CreatePedigreeAsync(
            new CreatePedigreeArgs(family.PedigreeDisplayName),
            cancellationToken).ConfigureAwait(false);
        var probandId = await this.client.CreateIndividualAsync(
            new CreateIndividualArgs(
                family.Proband.DisplayName,
                family.Proband.BiologicalSex,
                family.Proband.YearOfBirth),
            cancellationToken).ConfigureAwait(false);
        await this.client.AddIndividualToPedigreeAsync(pedigreeId, probandId, cancellationToken).ConfigureAwait(false);
        await this.client.DesignateAsProbandAsync(probandId, cancellationToken).ConfigureAwait(false);

        var added = 0;
        foreach (var relative in family.Relatives)
        {
            await this.client.AddRelativeAsync(
                new AddRelativeArgs(
                    pedigreeId,
                    probandId,
                    relative.RelativeType,
                    relative.DisplayName,
                    relative.BiologicalSex,
                    relative.YearOfBirth),
                cancellationToken).ConfigureAwait(false);
            added += 1;
        }
        return new IntakeCreationResult(pedigreeId, probandId, added);
    }
}
