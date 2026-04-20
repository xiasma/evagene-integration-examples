namespace FhirBridge;

/// <summary>
/// FHIR &lt;-&gt; Evagene relation code translation.
///
/// The FHIR codes come from the HL7 v3 RoleCode code system referenced
/// by FHIR R5 FamilyMemberHistory.relationship.
///
///   https://hl7.org/fhir/R5/familymemberhistory.html
///   https://terminology.hl7.org/CodeSystem-v3-RoleCode.html
///
/// Codes not listed here are reported as null; callers surface that as
/// a skip-with-warning, not a hard error.
/// </summary>
public sealed record FhirCoding(string System, string Code, string Display);

public static class RelationMap
{
    public const string V3RoleCodeSystem = "http://terminology.hl7.org/CodeSystem/v3-RoleCode";

    private static readonly IReadOnlyList<(RelativeType Evagene, string Fhir, string Display)> Mappings = new[]
    {
        (RelativeType.Mother, "MTH", "mother"),
        (RelativeType.Father, "FTH", "father"),
        (RelativeType.Brother, "BRO", "brother"),
        (RelativeType.Sister, "SIS", "sister"),
        (RelativeType.HalfBrother, "HBRO", "half-brother"),
        (RelativeType.HalfSister, "HSIS", "half-sister"),
        (RelativeType.MaternalGrandmother, "MGRMTH", "maternal grandmother"),
        (RelativeType.MaternalGrandfather, "MGRFTH", "maternal grandfather"),
        (RelativeType.PaternalGrandmother, "PGRMTH", "paternal grandmother"),
        (RelativeType.PaternalGrandfather, "PGRFTH", "paternal grandfather"),
        (RelativeType.Son, "SON", "son"),
        (RelativeType.Daughter, "DAU", "daughter"),
        (RelativeType.MaternalAunt, "MAUNT", "maternal aunt"),
        (RelativeType.MaternalUncle, "MUNCLE", "maternal uncle"),
        (RelativeType.PaternalAunt, "PAUNT", "paternal aunt"),
        (RelativeType.PaternalUncle, "PUNCLE", "paternal uncle"),
        (RelativeType.Niece, "NIECE", "niece"),
        (RelativeType.Nephew, "NEPH", "nephew"),
        (RelativeType.FirstCousin, "COUSN", "cousin"),
    };

    private static readonly Dictionary<string, RelativeType> ByFhir = Mappings.ToDictionary(
        m => m.Fhir, m => m.Evagene, StringComparer.Ordinal);

    private static readonly Dictionary<RelativeType, FhirCoding> ByEvagene = Mappings.ToDictionary(
        m => m.Evagene,
        m => new FhirCoding(V3RoleCodeSystem, m.Fhir, m.Display));

    public static FhirCoding? ToFhir(RelativeType type)
    {
        return ByEvagene.TryGetValue(type, out var coding) ? coding : null;
    }

    public static RelativeType? ToEvagene(string fhirCode)
    {
        return ByFhir.TryGetValue(fhirCode, out var type) ? type : null;
    }
}
