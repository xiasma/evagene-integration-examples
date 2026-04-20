using Xunit;

namespace FhirBridge.Tests;

public sealed class RelationMapTests
{
    public static IEnumerable<object[]> Pairs() => new[]
    {
        new object[] { RelativeType.Mother, "MTH" },
        new object[] { RelativeType.Father, "FTH" },
        new object[] { RelativeType.Brother, "BRO" },
        new object[] { RelativeType.Sister, "SIS" },
        new object[] { RelativeType.HalfBrother, "HBRO" },
        new object[] { RelativeType.HalfSister, "HSIS" },
        new object[] { RelativeType.MaternalGrandmother, "MGRMTH" },
        new object[] { RelativeType.MaternalGrandfather, "MGRFTH" },
        new object[] { RelativeType.PaternalGrandmother, "PGRMTH" },
        new object[] { RelativeType.PaternalGrandfather, "PGRFTH" },
        new object[] { RelativeType.Son, "SON" },
        new object[] { RelativeType.Daughter, "DAU" },
        new object[] { RelativeType.MaternalAunt, "MAUNT" },
        new object[] { RelativeType.MaternalUncle, "MUNCLE" },
        new object[] { RelativeType.PaternalAunt, "PAUNT" },
        new object[] { RelativeType.PaternalUncle, "PUNCLE" },
        new object[] { RelativeType.Niece, "NIECE" },
        new object[] { RelativeType.Nephew, "NEPH" },
        new object[] { RelativeType.FirstCousin, "COUSN" },
    };

    [Theory]
    [MemberData(nameof(Pairs))]
    public void Round_trips_both_ways(RelativeType evagene, string fhir)
    {
        var coding = RelationMap.ToFhir(evagene);
        Assert.NotNull(coding);
        Assert.Equal(fhir, coding!.Code);
        Assert.Equal(RelationMap.V3RoleCodeSystem, coding.System);
        Assert.Equal(evagene, RelationMap.ToEvagene(fhir));
    }

    [Fact]
    public void Unknown_code_is_not_fabricated()
    {
        Assert.Null(RelationMap.ToEvagene("SPOUSE"));
        Assert.Null(RelationMap.ToEvagene(string.Empty));
    }
}
