using System.Text.Json;

namespace FhirBridge;

public sealed class PedigreeParseException : Exception
{
    public PedigreeParseException(string message) : base(message) { }
}

public sealed record PedigreeIndividual(
    string Id,
    string DisplayName,
    BiologicalSex BiologicalSex,
    bool Proband,
    int? YearOfBirth,
    string? BornOn);

public sealed record PedigreeRelationship(string Id, IReadOnlyList<string> Members);

public sealed record PedigreeEgg(string IndividualId, string RelationshipId);

public sealed record PedigreeDetail(
    string Id,
    string DisplayName,
    IReadOnlyList<PedigreeIndividual> Individuals,
    IReadOnlyList<PedigreeRelationship> Relationships,
    IReadOnlyList<PedigreeEgg> Eggs);

public static class PedigreeDetailParser
{
    public static PedigreeDetail Parse(JsonElement root)
    {
        if (root.ValueKind != JsonValueKind.Object)
        {
            throw new PedigreeParseException("pedigree response is not a JSON object");
        }
        return new PedigreeDetail(
            Id: RequireString(root, "id"),
            DisplayName: RequireString(root, "display_name"),
            Individuals: RequireArray(root, "individuals").Select(ParseIndividual).ToList(),
            Relationships: RequireArray(root, "relationships").Select(ParseRelationship).ToList(),
            Eggs: RequireArray(root, "eggs").Select(ParseEgg).ToList());
    }

    private static PedigreeIndividual ParseIndividual(JsonElement element)
    {
        RequireObject(element, "individual");
        var properties = OptionalObject(element, "properties");
        int? year = null;
        if (properties is { } props && props.TryGetProperty("year_of_birth", out var yearElement) &&
            yearElement.ValueKind == JsonValueKind.Number && yearElement.TryGetInt32(out var y))
        {
            year = y;
        }
        return new PedigreeIndividual(
            Id: RequireString(element, "id"),
            DisplayName: RequireString(element, "display_name"),
            BiologicalSex: BiologicalSexWire.Parse(RequireString(element, "biological_sex")),
            Proband: ReadProbandFlag(element),
            YearOfBirth: year,
            BornOn: EarliestBirthDate(element));
    }

    private static PedigreeRelationship ParseRelationship(JsonElement element)
    {
        RequireObject(element, "relationship");
        var members = new List<string>();
        foreach (var member in RequireArray(element, "members"))
        {
            if (member.ValueKind != JsonValueKind.String)
            {
                throw new PedigreeParseException("relationship.members entries must be strings");
            }
            members.Add(member.GetString() ?? string.Empty);
        }
        return new PedigreeRelationship(RequireString(element, "id"), members);
    }

    private static PedigreeEgg ParseEgg(JsonElement element)
    {
        RequireObject(element, "egg");
        return new PedigreeEgg(
            IndividualId: RequireString(element, "individual_id"),
            RelationshipId: RequireString(element, "relationship_id"));
    }

    private static bool ReadProbandFlag(JsonElement element)
    {
        if (!element.TryGetProperty("proband", out var flag))
        {
            return false;
        }
        return flag.ValueKind switch
        {
            JsonValueKind.Number when flag.TryGetInt32(out var value) => value == 1,
            JsonValueKind.True => true,
            _ => false,
        };
    }

    private static string? EarliestBirthDate(JsonElement element)
    {
        if (!element.TryGetProperty("events", out var events) || events.ValueKind != JsonValueKind.Array)
        {
            return null;
        }
        foreach (var ev in events.EnumerateArray())
        {
            if (ev.ValueKind != JsonValueKind.Object)
            {
                continue;
            }
            if (ev.TryGetProperty("type", out var type) && type.GetString() == "birth" &&
                ev.TryGetProperty("date_start", out var date) && date.ValueKind == JsonValueKind.String)
            {
                return date.GetString();
            }
        }
        return null;
    }

    private static void RequireObject(JsonElement element, string label)
    {
        if (element.ValueKind != JsonValueKind.Object)
        {
            throw new PedigreeParseException($"Expected object for {label}");
        }
    }

    private static string RequireString(JsonElement element, string key)
    {
        if (!element.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.String)
        {
            throw new PedigreeParseException($"Missing string field '{key}'");
        }
        return value.GetString() ?? throw new PedigreeParseException($"Field '{key}' is null");
    }

    private static IEnumerable<JsonElement> RequireArray(JsonElement element, string key)
    {
        if (!element.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.Array)
        {
            throw new PedigreeParseException($"Missing array field '{key}'");
        }
        foreach (var item in value.EnumerateArray())
        {
            yield return item;
        }
    }

    private static JsonElement? OptionalObject(JsonElement element, string key)
    {
        if (element.TryGetProperty(key, out var value) && value.ValueKind == JsonValueKind.Object)
        {
            return value;
        }
        return null;
    }
}
