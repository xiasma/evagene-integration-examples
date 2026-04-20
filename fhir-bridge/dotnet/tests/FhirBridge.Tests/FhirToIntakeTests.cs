using System.Text.Json;

using Xunit;

namespace FhirBridge.Tests;

public sealed class FhirToIntakeTests
{
    [Fact]
    public void Maps_sample_bundle_to_intake_family()
    {
        using var doc = JsonDocument.Parse(Fixtures.LoadFhirBundleJson());

        var result = FhirToIntake.ToIntakeFamily(
            doc.RootElement,
            new FhirToIntakeOptions("patient-emma", "Emma Chen"));

        Assert.Empty(result.Warnings);
        Assert.Equal("Emma Chen", result.Family.Proband.DisplayName);
        Assert.Equal(6, result.Family.Relatives.Count);
        var byType = result.Family.Relatives.ToDictionary(r => r.RelativeType);
        Assert.Equal("Linda Chen", byType[RelativeType.Mother].DisplayName);
        Assert.Equal("David Chen", byType[RelativeType.Father].DisplayName);
        Assert.Equal("Mary Chen", byType[RelativeType.MaternalGrandmother].DisplayName);
        Assert.Equal("Robert Chen", byType[RelativeType.MaternalGrandfather].DisplayName);
        Assert.Equal("James Chen", byType[RelativeType.Brother].DisplayName);
        Assert.Equal("Noah Chen", byType[RelativeType.Son].DisplayName);
        Assert.Equal(1962, byType[RelativeType.Mother].YearOfBirth);
        Assert.Equal(BiologicalSex.Female, byType[RelativeType.Mother].BiologicalSex);
    }

    [Fact]
    public void Unknown_relationship_code_is_warned_and_skipped()
    {
        var json = """
        {
          "resourceType": "Bundle",
          "type": "searchset",
          "entry": [
            {
              "resource": {
                "resourceType": "FamilyMemberHistory",
                "id": "fmh-stepmum",
                "status": "completed",
                "patient": { "reference": "Patient/p1" },
                "name": "Sarah",
                "relationship": {
                  "coding": [
                    { "system": "http://terminology.hl7.org/CodeSystem/v3-RoleCode", "code": "STPMTH" }
                  ]
                }
              }
            }
          ]
        }
        """;
        using var doc = JsonDocument.Parse(json);

        var result = FhirToIntake.ToIntakeFamily(doc.RootElement, new FhirToIntakeOptions("p1"));

        Assert.Empty(result.Family.Relatives);
        Assert.Single(result.Warnings);
        Assert.Contains("STPMTH", result.Warnings[0]);
    }

    [Fact]
    public void Non_bundle_input_is_rejected()
    {
        using var doc = JsonDocument.Parse("""{"resourceType":"Patient"}""");

        Assert.Throws<MappingException>(
            () => FhirToIntake.ToIntakeFamily(doc.RootElement, new FhirToIntakeOptions("p1")));
    }
}
