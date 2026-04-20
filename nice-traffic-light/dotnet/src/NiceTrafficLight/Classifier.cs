using System.Text.Json;

namespace NiceTrafficLight;

public enum RiskCategory
{
    NearPopulation,
    Moderate,
    High,
}

public sealed record NiceOutcome(
    string CounseleeName,
    RiskCategory Category,
    bool ReferForGeneticsAssessment,
    IReadOnlyList<string> Triggers,
    IReadOnlyList<string> Notes);

public sealed class ResponseSchemaException : Exception
{
    public ResponseSchemaException(string message) : base(message) { }
}

public static class NiceClassifier
{
    public static NiceOutcome Classify(JsonElement payload)
    {
        var root = RequireObject(payload, "response");
        var cancerRisk = RequireObjectField(root, "cancer_risk");

        return new NiceOutcome(
            CounseleeName: OptionalString(root, "counselee_name"),
            Category: ParseCategory(RequireStringField(cancerRisk, "nice_category")),
            ReferForGeneticsAssessment: RequireBooleanField(cancerRisk, "nice_refer_genetics"),
            Triggers: RequireStringListField(cancerRisk, "nice_triggers"),
            Notes: RequireStringListField(cancerRisk, "notes"));
    }

    private static RiskCategory ParseCategory(string raw) => raw switch
    {
        "near_population" => RiskCategory.NearPopulation,
        "moderate" => RiskCategory.Moderate,
        "high" => RiskCategory.High,
        _ => throw new ResponseSchemaException($"Unknown NICE category: '{raw}'"),
    };

    private static JsonElement RequireObject(JsonElement value, string label)
    {
        if (value.ValueKind != JsonValueKind.Object)
        {
            throw new ResponseSchemaException($"{label} is not an object");
        }
        return value;
    }

    private static JsonElement RequireObjectField(JsonElement container, string key)
    {
        if (!container.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.Object)
        {
            throw new ResponseSchemaException($"field '{key}' is missing or not an object");
        }
        return value;
    }

    private static string RequireStringField(JsonElement container, string key)
    {
        if (!container.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.String)
        {
            throw new ResponseSchemaException($"field '{key}' is missing or not a string");
        }
        return value.GetString() ?? throw new ResponseSchemaException($"field '{key}' is null");
    }

    private static bool RequireBooleanField(JsonElement container, string key)
    {
        if (!container.TryGetProperty(key, out var value)
            || (value.ValueKind != JsonValueKind.True && value.ValueKind != JsonValueKind.False))
        {
            throw new ResponseSchemaException($"field '{key}' is missing or not a boolean");
        }
        return value.GetBoolean();
    }

    private static IReadOnlyList<string> RequireStringListField(JsonElement container, string key)
    {
        if (!container.TryGetProperty(key, out var value))
        {
            return Array.Empty<string>();
        }
        if (value.ValueKind != JsonValueKind.Array)
        {
            throw new ResponseSchemaException($"field '{key}' is not a list of strings");
        }

        var list = new List<string>(value.GetArrayLength());
        foreach (var item in value.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.String)
            {
                throw new ResponseSchemaException($"field '{key}' is not a list of strings");
            }
            list.Add(item.GetString() ?? string.Empty);
        }
        return list;
    }

    private static string OptionalString(JsonElement container, string key)
    {
        if (!container.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.String)
        {
            return string.Empty;
        }
        return value.GetString() ?? string.Empty;
    }
}
