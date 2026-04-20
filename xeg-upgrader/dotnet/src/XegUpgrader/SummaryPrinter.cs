using System.Globalization;
using System.Text.Json;

namespace XegUpgrader;

public sealed record ParseSummary(
    string Filename,
    int Individuals,
    int Relationships,
    int Eggs,
    int Diseases,
    int Events,
    IReadOnlyList<string> DiseaseNames,
    IReadOnlyList<string> Warnings);

/// <summary>
/// Pure helpers that turn a parse-mode response into a human-readable
/// summary and inspect it for inconsistencies worth flagging.  No I/O.
/// </summary>
public static class SummaryPrinter
{
    private const int CountColumnWidth = 14;

    public static ParseSummary Summarise(JsonElement parseResponse, string filename)
    {
        var individuals = ArrayOf(parseResponse, "individuals");
        var relationships = ArrayOf(parseResponse, "relationships");
        var eggs = ArrayOf(parseResponse, "eggs");
        var diseases = ArrayOf(parseResponse, "diseases");

        return new ParseSummary(
            Filename: filename,
            Individuals: individuals.Count,
            Relationships: relationships.Count,
            Eggs: eggs.Count,
            Diseases: diseases.Count,
            Events: CountEvents(individuals) + CountEvents(relationships) + CountEvents(eggs),
            DiseaseNames: CollectDiseaseNames(diseases),
            Warnings: DetectWarnings(individuals, eggs, diseases));
    }

    public static string Render(ParseSummary summary, RunMode mode)
    {
        var writer = new StringWriter { NewLine = "\n" };
        writer.WriteLine($"File: {summary.Filename}");
        writer.WriteLine($"Mode: {ModeLine(mode)}");
        writer.WriteLine();
        writer.WriteLine("Counts");
        WriteCount(writer, "individuals", summary.Individuals);
        WriteCount(writer, "relationships", summary.Relationships);
        WriteCount(writer, "eggs", summary.Eggs);
        WriteCount(writer, "diseases", summary.Diseases);
        WriteCount(writer, "events", summary.Events);
        writer.WriteLine();
        writer.WriteLine("Diseases");
        WriteList(writer, summary.DiseaseNames);
        writer.WriteLine();
        writer.WriteLine("Warnings");
        WriteList(writer, summary.Warnings);
        return writer.ToString();
    }

    private static string ModeLine(RunMode mode) => mode switch
    {
        RunMode.Preview => "preview (no pedigree created)",
        RunMode.Create => "create (pedigree imported)",
        _ => throw new ArgumentOutOfRangeException(nameof(mode)),
    };

    private static void WriteCount(TextWriter writer, string label, int count)
    {
        var padded = label.PadRight(CountColumnWidth);
        writer.WriteLine($"  {padded} {count.ToString(CultureInfo.InvariantCulture)}");
    }

    private static void WriteList(TextWriter writer, IReadOnlyList<string> items)
    {
        if (items.Count == 0)
        {
            writer.WriteLine("  (none)");
            return;
        }
        foreach (var item in items)
        {
            writer.WriteLine($"  - {item}");
        }
    }

    private static IReadOnlyList<JsonElement> ArrayOf(JsonElement container, string key)
    {
        if (container.ValueKind != JsonValueKind.Object)
        {
            return Array.Empty<JsonElement>();
        }
        if (!container.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.Array)
        {
            return Array.Empty<JsonElement>();
        }
        var list = new List<JsonElement>(value.GetArrayLength());
        foreach (var item in value.EnumerateArray())
        {
            list.Add(item);
        }
        return list;
    }

    private static int CountEvents(IReadOnlyList<JsonElement> containers)
    {
        var total = 0;
        foreach (var container in containers)
        {
            if (container.ValueKind != JsonValueKind.Object)
            {
                continue;
            }
            if (container.TryGetProperty("events", out var events) && events.ValueKind == JsonValueKind.Array)
            {
                total += events.GetArrayLength();
            }
        }
        return total;
    }

    private static List<string> CollectDiseaseNames(IReadOnlyList<JsonElement> diseases)
    {
        var names = new List<string>(diseases.Count);
        foreach (var disease in diseases)
        {
            names.Add(DisplayNameOf(disease) ?? "(unnamed)");
        }
        return names;
    }

    private static List<string> DetectWarnings(
        IReadOnlyList<JsonElement> individuals,
        IReadOnlyList<JsonElement> eggs,
        IReadOnlyList<JsonElement> diseases)
    {
        var warnings = new List<string>();

        var unknownSex = CountWhere(individuals, HasNoBiologicalSex);
        if (unknownSex > 0)
        {
            warnings.Add($"{unknownSex} individual(s) with unknown biological sex");
        }

        var unnamed = CountWhere(individuals, HasNoDisplayName);
        if (unnamed > 0)
        {
            warnings.Add($"{unnamed} individual(s) without a display name");
        }

        var orphanedEggs = CountWhere(eggs, HasNoRelationship);
        if (orphanedEggs > 0)
        {
            warnings.Add($"{orphanedEggs} egg(s) with no resolvable parent relationship");
        }

        var knownDiseaseIds = CollectDiseaseIds(diseases);
        var danglingManifestations = 0;
        foreach (var individual in individuals)
        {
            danglingManifestations += CountDanglingManifestations(individual, knownDiseaseIds);
        }
        if (danglingManifestations > 0)
        {
            warnings.Add($"{danglingManifestations} disease manifestation(s) with unknown disease_id");
        }

        return warnings;
    }

    private static int CountWhere(IReadOnlyList<JsonElement> items, Func<JsonElement, bool> predicate)
    {
        var count = 0;
        foreach (var item in items)
        {
            if (predicate(item))
            {
                count += 1;
            }
        }
        return count;
    }

    private static bool HasNoBiologicalSex(JsonElement individual)
    {
        if (individual.ValueKind != JsonValueKind.Object)
        {
            return false;
        }
        if (!individual.TryGetProperty("biological_sex", out var value))
        {
            return true;
        }
        if (value.ValueKind == JsonValueKind.Null)
        {
            return true;
        }
        if (value.ValueKind == JsonValueKind.String)
        {
            var text = value.GetString();
            return string.IsNullOrEmpty(text) || text.Equals("unknown", StringComparison.OrdinalIgnoreCase);
        }
        return false;
    }

    private static bool HasNoDisplayName(JsonElement individual)
    {
        return string.IsNullOrWhiteSpace(DisplayNameOf(individual));
    }

    private static bool HasNoRelationship(JsonElement egg)
    {
        if (egg.ValueKind != JsonValueKind.Object)
        {
            return true;
        }
        if (!egg.TryGetProperty("relationship_id", out var value))
        {
            return true;
        }
        return value.ValueKind == JsonValueKind.Null
            || (value.ValueKind == JsonValueKind.String && string.IsNullOrEmpty(value.GetString()));
    }

    private static HashSet<string> CollectDiseaseIds(IReadOnlyList<JsonElement> diseases)
    {
        var ids = new HashSet<string>(StringComparer.Ordinal);
        foreach (var disease in diseases)
        {
            if (disease.ValueKind != JsonValueKind.Object)
            {
                continue;
            }
            if (disease.TryGetProperty("id", out var id) && id.ValueKind == JsonValueKind.String)
            {
                var text = id.GetString();
                if (!string.IsNullOrEmpty(text))
                {
                    ids.Add(text);
                }
            }
        }
        return ids;
    }

    private static int CountDanglingManifestations(JsonElement individual, HashSet<string> knownIds)
    {
        if (individual.ValueKind != JsonValueKind.Object)
        {
            return 0;
        }
        if (!individual.TryGetProperty("diseases", out var diseases)
            || diseases.ValueKind != JsonValueKind.Array)
        {
            return 0;
        }
        var dangling = 0;
        foreach (var disease in diseases.EnumerateArray())
        {
            if (disease.ValueKind != JsonValueKind.Object)
            {
                continue;
            }
            if (!disease.TryGetProperty("disease_id", out var id) || id.ValueKind != JsonValueKind.String)
            {
                dangling += 1;
                continue;
            }
            var text = id.GetString();
            if (string.IsNullOrEmpty(text) || !knownIds.Contains(text))
            {
                dangling += 1;
            }
        }
        return dangling;
    }

    private static string? DisplayNameOf(JsonElement element)
    {
        if (element.ValueKind != JsonValueKind.Object)
        {
            return null;
        }
        if (!element.TryGetProperty("display_name", out var value) || value.ValueKind != JsonValueKind.String)
        {
            return null;
        }
        return value.GetString();
    }
}
