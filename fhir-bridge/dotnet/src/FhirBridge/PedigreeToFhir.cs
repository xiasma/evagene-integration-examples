using System.Text;
using System.Text.Json;

namespace FhirBridge;

public sealed class MappingException : Exception
{
    public MappingException(string message) : base(message) { }
}

public sealed record PedigreeMappingResult(
    string BundleJson,
    string ProbandReference,
    int MappedResourceCount,
    IReadOnlyList<string> Warnings);

public static class PedigreeToFhir
{
    private const string AdminGenderSystem = "http://hl7.org/fhir/administrative-gender";

    public static PedigreeMappingResult ToFhirBundle(PedigreeDetail detail)
    {
        var relations = ProbandRelations.FromProband(detail)
            ?? throw new MappingException(
                $"Pedigree {detail.Id} has no proband: set one before pushing to FHIR.");

        var probandReference = $"Patient/{relations.Proband.Id}";
        var warnings = new List<string>();
        var entries = new List<Action<Utf8JsonWriter>>();

        foreach (var view in relations.Relatives)
        {
            var coding = RelationMap.ToFhir(view.RelativeType);
            if (coding is null)
            {
                warnings.Add(
                    $"skipped {view.Individual.DisplayName}: no FHIR code for relative_type '{RelativeTypeWire.Of(view.RelativeType)}'.");
                continue;
            }
            entries.Add(writer => WriteEntry(writer, view.Individual, probandReference, coding));
        }
        foreach (var unlabelled in relations.Unlabelled)
        {
            warnings.Add(
                $"skipped {unlabelled.DisplayName}: could not derive a supported relation to the proband.");
        }

        var bundleJson = WriteBundle(entries);
        return new PedigreeMappingResult(bundleJson, probandReference, entries.Count, warnings);
    }

    private static string WriteBundle(IReadOnlyList<Action<Utf8JsonWriter>> entryWriters)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writer.WriteString("resourceType", "Bundle");
            writer.WriteString("type", "transaction");
            writer.WriteStartArray("entry");
            foreach (var entry in entryWriters)
            {
                entry(writer);
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        return Encoding.UTF8.GetString(stream.ToArray());
    }

    private static void WriteEntry(
        Utf8JsonWriter writer,
        PedigreeIndividual individual,
        string patientReference,
        FhirCoding coding)
    {
        writer.WriteStartObject();
        writer.WriteString("fullUrl", $"urn:uuid:{individual.Id}");

        writer.WriteStartObject("resource");
        writer.WriteString("resourceType", "FamilyMemberHistory");
        writer.WriteString("status", "completed");
        writer.WriteStartObject("patient");
        writer.WriteString("reference", patientReference);
        writer.WriteEndObject();
        writer.WriteString("name", individual.DisplayName);

        writer.WriteStartObject("relationship");
        writer.WriteStartArray("coding");
        writer.WriteStartObject();
        writer.WriteString("system", coding.System);
        writer.WriteString("code", coding.Code);
        writer.WriteString("display", coding.Display);
        writer.WriteEndObject();
        writer.WriteEndArray();
        writer.WriteEndObject();

        writer.WriteStartObject("sex");
        writer.WriteStartArray("coding");
        writer.WriteStartObject();
        writer.WriteString("system", AdminGenderSystem);
        writer.WriteString("code", BiologicalSexWire.Of(individual.BiologicalSex));
        writer.WriteEndObject();
        writer.WriteEndArray();
        writer.WriteEndObject();

        if (individual.BornOn is not null)
        {
            writer.WriteString("bornDate", individual.BornOn);
        }
        writer.WriteEndObject();

        writer.WriteStartObject("request");
        writer.WriteString("method", "POST");
        writer.WriteString("url", "FamilyMemberHistory");
        writer.WriteEndObject();

        writer.WriteEndObject();
    }
}
