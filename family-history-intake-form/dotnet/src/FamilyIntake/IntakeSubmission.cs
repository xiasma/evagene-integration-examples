namespace FamilyIntake;

public enum BiologicalSex
{
    Female,
    Male,
    Unknown,
}

public enum SiblingRelation
{
    Sister,
    Brother,
    HalfSister,
    HalfBrother,
}

public sealed record RelativeEntry(string DisplayName, int? YearOfBirth = null);

public sealed record SiblingEntry(
    string DisplayName,
    SiblingRelation Relation,
    BiologicalSex BiologicalSex,
    int? YearOfBirth = null);

public sealed record ProbandEntry(
    string DisplayName,
    BiologicalSex BiologicalSex,
    int? YearOfBirth = null);

public sealed record IntakeSubmission(
    ProbandEntry Proband,
    IReadOnlyList<SiblingEntry> Siblings,
    RelativeEntry? Mother = null,
    RelativeEntry? Father = null,
    RelativeEntry? MaternalGrandmother = null,
    RelativeEntry? MaternalGrandfather = null,
    RelativeEntry? PaternalGrandmother = null,
    RelativeEntry? PaternalGrandfather = null);

public sealed class IntakeValidationException : Exception
{
    public IntakeValidationException(string message) : base(message) { }
}

public static class IntakeSubmissionParser
{
    private const int MinYear = 1850;
    private const int MaxYear = 2030;
    private const int MaxSiblings = 4;

    public static IntakeSubmission Parse(IReadOnlyDictionary<string, string> body)
    {
        var probandName = RequireNonEmpty(body, "proband_name", "The patient's name");
        var probandSex = ParseSex(OptionalString(body, "proband_sex"));
        var probandYear = ParseYear(OptionalString(body, "proband_year"), "proband_year");

        return new IntakeSubmission(
            Proband: new ProbandEntry(probandName, probandSex, probandYear),
            Siblings: ParseSiblings(body),
            Mother: OptionalRelative(body, "mother"),
            Father: OptionalRelative(body, "father"),
            MaternalGrandmother: OptionalRelative(body, "maternal_grandmother"),
            MaternalGrandfather: OptionalRelative(body, "maternal_grandfather"),
            PaternalGrandmother: OptionalRelative(body, "paternal_grandmother"),
            PaternalGrandfather: OptionalRelative(body, "paternal_grandfather"));
    }

    private static RelativeEntry? OptionalRelative(IReadOnlyDictionary<string, string> body, string formPrefix)
    {
        var name = OptionalString(body, $"{formPrefix}_name").Trim();
        if (name.Length == 0)
        {
            return null;
        }
        var year = ParseYear(OptionalString(body, $"{formPrefix}_year"), $"{formPrefix}_year");
        return new RelativeEntry(name, year);
    }

    private static List<SiblingEntry> ParseSiblings(IReadOnlyDictionary<string, string> body)
    {
        var siblings = new List<SiblingEntry>();
        for (var index = 0; index < MaxSiblings; index += 1)
        {
            var name = OptionalString(body, $"sibling_{index}_name").Trim();
            if (name.Length == 0)
            {
                continue;
            }
            var relation = ParseSiblingRelation(OptionalString(body, $"sibling_{index}_relation"), index);
            var year = ParseYear(OptionalString(body, $"sibling_{index}_year"), $"sibling_{index}_year");
            siblings.Add(new SiblingEntry(name, relation, SexForSiblingRelation(relation), year));
        }
        return siblings;
    }

    private static BiologicalSex ParseSex(string raw) => raw switch
    {
        "" => BiologicalSex.Unknown,
        "female" => BiologicalSex.Female,
        "male" => BiologicalSex.Male,
        "unknown" => BiologicalSex.Unknown,
        _ => throw new IntakeValidationException($"Unknown biological sex: {raw}"),
    };

    private static SiblingRelation ParseSiblingRelation(string raw, int index) => raw switch
    {
        "sister" => SiblingRelation.Sister,
        "brother" => SiblingRelation.Brother,
        "half_sister" => SiblingRelation.HalfSister,
        "half_brother" => SiblingRelation.HalfBrother,
        _ => throw new IntakeValidationException(
            $"Sibling {index + 1} must have a relation (sister / brother / half_sister / half_brother)."),
    };

    private static BiologicalSex SexForSiblingRelation(SiblingRelation relation) => relation switch
    {
        SiblingRelation.Sister or SiblingRelation.HalfSister => BiologicalSex.Female,
        SiblingRelation.Brother or SiblingRelation.HalfBrother => BiologicalSex.Male,
        _ => throw new ArgumentOutOfRangeException(nameof(relation)),
    };

    private static int? ParseYear(string raw, string fieldName)
    {
        var trimmed = raw.Trim();
        if (trimmed.Length == 0)
        {
            return null;
        }
        if (!int.TryParse(trimmed, out var parsed) || parsed < MinYear || parsed > MaxYear)
        {
            throw new IntakeValidationException(
                $"Field '{fieldName}' must be a year between {MinYear} and {MaxYear}.");
        }
        return parsed;
    }

    private static string RequireNonEmpty(IReadOnlyDictionary<string, string> body, string key, string label)
    {
        var value = OptionalString(body, key).Trim();
        if (value.Length == 0)
        {
            throw new IntakeValidationException($"{label} is required.");
        }
        return value;
    }

    private static string OptionalString(IReadOnlyDictionary<string, string> body, string key)
    {
        return body.TryGetValue(key, out var value) ? value : string.Empty;
    }
}
