using System.Text;
using System.Text.Json;

namespace FamilyIntake;

public sealed class EvageneApiException : Exception
{
    public EvageneApiException(string message) : base(message) { }
}

public enum RelativeType
{
    Mother,
    Father,
    MaternalGrandmother,
    MaternalGrandfather,
    PaternalGrandmother,
    PaternalGrandfather,
    Sister,
    Brother,
    HalfSister,
    HalfBrother,
}

public sealed record CreatePedigreeArgs(string DisplayName);

public sealed record CreateIndividualArgs(
    string DisplayName,
    BiologicalSex BiologicalSex,
    int? YearOfBirth = null);

public sealed record AddRelativeArgs(
    string PedigreeId,
    string RelativeOf,
    RelativeType RelativeType,
    string DisplayName,
    BiologicalSex BiologicalSex,
    int? YearOfBirth = null);

/// <summary>
/// The subset of the Evagene API that the intake flow depends on.
/// IntakeService talks to this, not the concrete class, so tests
/// supply their own implementation without a live HTTP layer.
/// </summary>
public interface IEvageneApi
{
    Task<string> CreatePedigreeAsync(CreatePedigreeArgs args, CancellationToken cancellationToken = default);
    Task<string> CreateIndividualAsync(CreateIndividualArgs args, CancellationToken cancellationToken = default);
    Task AddIndividualToPedigreeAsync(string pedigreeId, string individualId, CancellationToken cancellationToken = default);
    Task DesignateAsProbandAsync(string individualId, CancellationToken cancellationToken = default);
    Task<string> AddRelativeAsync(AddRelativeArgs args, CancellationToken cancellationToken = default);
}

public sealed class EvageneClient : IEvageneApi
{
    private const int HttpOkLower = 200;
    private const int HttpOkUpper = 300;

    private readonly string baseUrl;
    private readonly string apiKey;
    private readonly IHttpGateway http;

    public EvageneClient(string baseUrl, string apiKey, IHttpGateway http)
    {
        this.baseUrl = baseUrl.TrimEnd('/');
        this.apiKey = apiKey;
        this.http = http;
    }

    public async Task<string> CreatePedigreeAsync(CreatePedigreeArgs args, CancellationToken cancellationToken = default)
    {
        var body = WritePedigreeBody(args.DisplayName);
        var payload = await this.RequestAsync(HttpMethodKind.Post, "/api/pedigrees", body, cancellationToken).ConfigureAwait(false);
        return RequireStringField(payload, "id");
    }

    public async Task<string> CreateIndividualAsync(CreateIndividualArgs args, CancellationToken cancellationToken = default)
    {
        var body = WriteIndividualBody(args);
        var payload = await this.RequestAsync(HttpMethodKind.Post, "/api/individuals", body, cancellationToken).ConfigureAwait(false);
        return RequireStringField(payload, "id");
    }

    public Task AddIndividualToPedigreeAsync(string pedigreeId, string individualId, CancellationToken cancellationToken = default)
    {
        var path = $"/api/pedigrees/{pedigreeId}/individuals/{individualId}";
        return this.SendIgnoringBodyAsync(HttpMethodKind.Post, path, "{}", cancellationToken);
    }

    public Task DesignateAsProbandAsync(string individualId, CancellationToken cancellationToken = default)
    {
        var path = $"/api/individuals/{individualId}";
        return this.SendIgnoringBodyAsync(HttpMethodKind.Patch, path, """{"proband":1}""", cancellationToken);
    }

    public async Task<string> AddRelativeAsync(AddRelativeArgs args, CancellationToken cancellationToken = default)
    {
        var body = WriteAddRelativeBody(args);
        var path = $"/api/pedigrees/{args.PedigreeId}/register/add-relative";
        var payload = await this.RequestAsync(HttpMethodKind.Post, path, body, cancellationToken).ConfigureAwait(false);
        var individual = RequireObjectField(payload, "individual");
        return RequireStringField(individual, "id");
    }

    private async Task<JsonElement> RequestAsync(
        HttpMethodKind method,
        string path,
        string jsonBody,
        CancellationToken cancellationToken)
    {
        var response = await this.SendAsync(method, path, jsonBody, cancellationToken).ConfigureAwait(false);
        try
        {
            using var doc = JsonDocument.Parse(response.JsonBody);
            return doc.RootElement.Clone();
        }
        catch (JsonException ex)
        {
            throw new EvageneApiException($"Evagene API returned invalid JSON: {ex.Message}");
        }
    }

    private async Task SendIgnoringBodyAsync(
        HttpMethodKind method,
        string path,
        string jsonBody,
        CancellationToken cancellationToken)
    {
        // For endpoints whose success response carries no useful body.
        await this.SendAsync(method, path, jsonBody, cancellationToken).ConfigureAwait(false);
    }

    private async Task<HttpResponsePayload> SendAsync(
        HttpMethodKind method,
        string path,
        string jsonBody,
        CancellationToken cancellationToken)
    {
        var url = $"{this.baseUrl}{path}";
        var response = await this.http.SendAsync(
            new HttpRequestDescriptor(method, url, this.Headers(), jsonBody),
            cancellationToken).ConfigureAwait(false);
        if (response.Status < HttpOkLower || response.Status >= HttpOkUpper)
        {
            throw new EvageneApiException(
                $"Evagene API returned HTTP {response.Status} for {FormatMethod(method)} {path}");
        }
        return response;
    }

    private Dictionary<string, string> Headers() => new(StringComparer.Ordinal)
    {
        ["X-API-Key"] = this.apiKey,
        ["Accept"] = "application/json",
    };

    private static string FormatMethod(HttpMethodKind method) => method switch
    {
        HttpMethodKind.Post => "POST",
        HttpMethodKind.Patch => "PATCH",
        _ => throw new ArgumentOutOfRangeException(nameof(method)),
    };

    private static string WritePedigreeBody(string displayName)
    {
        return WriteJson(writer =>
        {
            writer.WriteStartObject();
            writer.WriteString("display_name", displayName);
            writer.WriteEndObject();
        });
    }

    private static string WriteIndividualBody(CreateIndividualArgs args)
    {
        return WriteJson(writer =>
        {
            writer.WriteStartObject();
            writer.WriteString("display_name", args.DisplayName);
            writer.WriteString("biological_sex", BiologicalSexWire.Of(args.BiologicalSex));
            WriteYearOfBirth(writer, args.YearOfBirth);
            writer.WriteEndObject();
        });
    }

    private static string WriteAddRelativeBody(AddRelativeArgs args)
    {
        return WriteJson(writer =>
        {
            writer.WriteStartObject();
            writer.WriteString("relative_of", args.RelativeOf);
            writer.WriteString("relative_type", RelativeTypeWire.Of(args.RelativeType));
            writer.WriteString("display_name", args.DisplayName);
            writer.WriteString("biological_sex", BiologicalSexWire.Of(args.BiologicalSex));
            WriteYearOfBirth(writer, args.YearOfBirth);
            writer.WriteEndObject();
        });
    }

    private static void WriteYearOfBirth(Utf8JsonWriter writer, int? yearOfBirth)
    {
        if (yearOfBirth is null)
        {
            return;
        }
        writer.WriteStartObject("properties");
        writer.WriteNumber("year_of_birth", yearOfBirth.Value);
        writer.WriteEndObject();
    }

    private static string WriteJson(Action<Utf8JsonWriter> build)
    {
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            build(writer);
        }
        return Encoding.UTF8.GetString(stream.ToArray());
    }

    private static string RequireStringField(JsonElement payload, string key)
    {
        if (payload.ValueKind != JsonValueKind.Object)
        {
            throw new EvageneApiException("Evagene response is not an object");
        }
        if (!payload.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.String)
        {
            throw new EvageneApiException($"Evagene response is missing string field '{key}'");
        }
        return value.GetString() ?? throw new EvageneApiException($"Evagene response field '{key}' is null");
    }

    private static JsonElement RequireObjectField(JsonElement payload, string key)
    {
        if (payload.ValueKind != JsonValueKind.Object)
        {
            throw new EvageneApiException("Evagene response is not an object");
        }
        if (!payload.TryGetProperty(key, out var value) || value.ValueKind != JsonValueKind.Object)
        {
            throw new EvageneApiException($"Evagene response is missing object field '{key}'");
        }
        return value;
    }
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
}

internal static class RelativeTypeWire
{
    public static string Of(RelativeType type) => type switch
    {
        RelativeType.Mother => "mother",
        RelativeType.Father => "father",
        RelativeType.MaternalGrandmother => "maternal_grandmother",
        RelativeType.MaternalGrandfather => "maternal_grandfather",
        RelativeType.PaternalGrandmother => "paternal_grandmother",
        RelativeType.PaternalGrandfather => "paternal_grandfather",
        RelativeType.Sister => "sister",
        RelativeType.Brother => "brother",
        RelativeType.HalfSister => "half_sister",
        RelativeType.HalfBrother => "half_brother",
        _ => throw new ArgumentOutOfRangeException(nameof(type)),
    };
}
