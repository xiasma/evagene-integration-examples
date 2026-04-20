using System.Text.Json;

namespace FhirBridge;

public sealed record FhirToIntakeOptions(string PatientId, string? ProbandDisplayName = null);

public sealed record FhirToIntakeResult(IntakeFamily Family, IReadOnlyList<string> Warnings);

public static class FhirToIntake
{
    public static FhirToIntakeResult ToIntakeFamily(JsonElement bundle, FhirToIntakeOptions options)
    {
        if (bundle.ValueKind != JsonValueKind.Object ||
            !TryReadResourceType(bundle, out var resourceType) ||
            resourceType != "Bundle")
        {
            throw new MappingException("FHIR response is not a Bundle with entries.");
        }
        if (!bundle.TryGetProperty("entry", out var entries) || entries.ValueKind != JsonValueKind.Array)
        {
            throw new MappingException("FHIR response is not a Bundle with entries.");
        }

        var warnings = new List<string>();
        var relatives = new List<Relative>();
        foreach (var entry in entries.EnumerateArray())
        {
            if (entry.ValueKind != JsonValueKind.Object ||
                !entry.TryGetProperty("resource", out var resource) ||
                resource.ValueKind != JsonValueKind.Object ||
                !TryReadResourceType(resource, out var kind) ||
                kind != "FamilyMemberHistory")
            {
                continue;
            }
            var mapped = MapResource(resource, warnings);
            if (mapped is not null)
            {
                relatives.Add(mapped);
            }
        }

        var probandName = (options.ProbandDisplayName ?? string.Empty).Trim();
        if (probandName.Length == 0)
        {
            probandName = $"Patient {options.PatientId}";
        }

        var family = new IntakeFamily(
            PedigreeDisplayName: $"{probandName}'s family (from FHIR)",
            Proband: new Proband(probandName, BiologicalSex.Unknown),
            Relatives: relatives);
        return new FhirToIntakeResult(family, warnings);
    }

    private static Relative? MapResource(JsonElement resource, List<string> warnings)
    {
        var id = TryReadString(resource, "id") ?? "(no id)";
        var fhirCode = ExtractV3Code(resource);
        if (fhirCode is null)
        {
            warnings.Add($"skipped FamilyMemberHistory {id}: no v3-RoleCode relationship coding.");
            return null;
        }
        var evageneType = RelationMap.ToEvagene(fhirCode);
        if (evageneType is null)
        {
            warnings.Add($"skipped FamilyMemberHistory {id}: relationship code '{fhirCode}' is not supported.");
            return null;
        }

        var displayName = TryReadString(resource, "name") ?? id;
        var sex = ExtractSex(resource);
        var year = ExtractYearOfBirth(resource);
        return new Relative(evageneType.Value, displayName, sex, year);
    }

    private static string? ExtractV3Code(JsonElement resource)
    {
        if (!resource.TryGetProperty("relationship", out var relationship) ||
            relationship.ValueKind != JsonValueKind.Object ||
            !relationship.TryGetProperty("coding", out var coding) ||
            coding.ValueKind != JsonValueKind.Array)
        {
            return null;
        }
        foreach (var entry in coding.EnumerateArray())
        {
            if (entry.ValueKind != JsonValueKind.Object) continue;
            if (TryReadString(entry, "system") == RelationMap.V3RoleCodeSystem)
            {
                return TryReadString(entry, "code");
            }
        }
        return null;
    }

    private static BiologicalSex ExtractSex(JsonElement resource)
    {
        if (!resource.TryGetProperty("sex", out var sex) ||
            sex.ValueKind != JsonValueKind.Object ||
            !sex.TryGetProperty("coding", out var coding) ||
            coding.ValueKind != JsonValueKind.Array)
        {
            return BiologicalSex.Unknown;
        }
        foreach (var entry in coding.EnumerateArray())
        {
            if (entry.ValueKind != JsonValueKind.Object) continue;
            var code = TryReadString(entry, "code");
            if (code == "female") return BiologicalSex.Female;
            if (code == "male") return BiologicalSex.Male;
        }
        return BiologicalSex.Unknown;
    }

    private static int? ExtractYearOfBirth(JsonElement resource)
    {
        var bornDate = TryReadString(resource, "bornDate");
        if (bornDate is null || bornDate.Length < 4)
        {
            return null;
        }
        return int.TryParse(bornDate.AsSpan(0, 4), out var year) ? year : null;
    }

    private static bool TryReadResourceType(JsonElement element, out string value)
    {
        if (element.TryGetProperty("resourceType", out var v) && v.ValueKind == JsonValueKind.String)
        {
            value = v.GetString() ?? string.Empty;
            return true;
        }
        value = string.Empty;
        return false;
    }

    private static string? TryReadString(JsonElement element, string key)
    {
        if (element.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.String)
        {
            return value.GetString();
        }
        return null;
    }
}
