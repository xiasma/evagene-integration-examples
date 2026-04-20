namespace FhirBridge;

public enum BiologicalSex
{
    Female,
    Male,
    Unknown,
}

public enum RelativeType
{
    Mother,
    Father,
    Brother,
    Sister,
    HalfBrother,
    HalfSister,
    MaternalGrandmother,
    MaternalGrandfather,
    PaternalGrandmother,
    PaternalGrandfather,
    Son,
    Daughter,
    MaternalAunt,
    MaternalUncle,
    PaternalAunt,
    PaternalUncle,
    Niece,
    Nephew,
    FirstCousin,
}

public sealed record Proband(string DisplayName, BiologicalSex BiologicalSex, int? YearOfBirth = null);

public sealed record Relative(
    RelativeType RelativeType,
    string DisplayName,
    BiologicalSex BiologicalSex,
    int? YearOfBirth = null);

public sealed record IntakeFamily(
    string PedigreeDisplayName,
    Proband Proband,
    IReadOnlyList<Relative> Relatives);

internal static class RelativeTypeWire
{
    public static string Of(RelativeType type) => type switch
    {
        RelativeType.Mother => "mother",
        RelativeType.Father => "father",
        RelativeType.Brother => "brother",
        RelativeType.Sister => "sister",
        RelativeType.HalfBrother => "half_brother",
        RelativeType.HalfSister => "half_sister",
        RelativeType.MaternalGrandmother => "maternal_grandmother",
        RelativeType.MaternalGrandfather => "maternal_grandfather",
        RelativeType.PaternalGrandmother => "paternal_grandmother",
        RelativeType.PaternalGrandfather => "paternal_grandfather",
        RelativeType.Son => "son",
        RelativeType.Daughter => "daughter",
        RelativeType.MaternalAunt => "maternal_aunt",
        RelativeType.MaternalUncle => "maternal_uncle",
        RelativeType.PaternalAunt => "paternal_aunt",
        RelativeType.PaternalUncle => "paternal_uncle",
        RelativeType.Niece => "niece",
        RelativeType.Nephew => "nephew",
        RelativeType.FirstCousin => "first_cousin",
        _ => throw new ArgumentOutOfRangeException(nameof(type)),
    };
}

internal static class BiologicalSexWire
{
    public static string Of(BiologicalSex sex) => sex switch
    {
        BiologicalSex.Female => "female",
        BiologicalSex.Male => "male",
        BiologicalSex.Unknown => "unknown",
        _ => throw new ArgumentOutOfRangeException(nameof(sex)),
    };

    public static BiologicalSex Parse(string raw) => raw switch
    {
        "female" => BiologicalSex.Female,
        "male" => BiologicalSex.Male,
        _ => BiologicalSex.Unknown,
    };
}
