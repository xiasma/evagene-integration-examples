using Xunit;

namespace FhirBridge.Tests;

public sealed class ConfigTests
{
    private const string PedigreeId = "11111111-1111-1111-1111-111111111111";

    [Fact]
    public void Push_requires_uuid_and_to_flag()
    {
        var config = ConfigLoader.Load(
            new[] { "push", PedigreeId, "--to", "https://fhir.example/fhir" },
            new Dictionary<string, string?>(StringComparer.Ordinal) { ["EVAGENE_API_KEY"] = "evg_test" });

        Assert.Equal(Mode.Push, config.Mode);
        Assert.Equal(PedigreeId, config.Subject);
        Assert.Equal("https://fhir.example/fhir", config.FhirBaseUrl);
        Assert.Null(config.FhirAuthHeader);
        Assert.Equal("https://evagene.net", config.EvageneBaseUrl);
    }

    [Fact]
    public void Pull_takes_any_subject_and_optional_auth_header()
    {
        var config = ConfigLoader.Load(
            new[] { "pull", "patient-42", "--from", "https://fhir.example", "--auth-header", "Authorization: Bearer xyz" },
            new Dictionary<string, string?>(StringComparer.Ordinal) { ["EVAGENE_API_KEY"] = "evg_test" });

        Assert.Equal(Mode.Pull, config.Mode);
        Assert.Equal("patient-42", config.Subject);
        Assert.Equal("Authorization: Bearer xyz", config.FhirAuthHeader);
    }

    [Fact]
    public void Missing_api_key_is_rejected()
    {
        Assert.Throws<ConfigException>(() =>
            ConfigLoader.Load(
                new[] { "push", PedigreeId, "--to", "https://fhir.example" },
                new Dictionary<string, string?>(StringComparer.Ordinal)));
    }

    [Fact]
    public void Push_rejects_non_uuid_pedigree_id()
    {
        Assert.Throws<ConfigException>(() =>
            ConfigLoader.Load(
                new[] { "push", "not-a-uuid", "--to", "https://fhir.example" },
                new Dictionary<string, string?>(StringComparer.Ordinal) { ["EVAGENE_API_KEY"] = "evg_test" }));
    }

    [Fact]
    public void Missing_to_flag_is_rejected()
    {
        Assert.Throws<ConfigException>(() =>
            ConfigLoader.Load(
                new[] { "push", PedigreeId },
                new Dictionary<string, string?>(StringComparer.Ordinal) { ["EVAGENE_API_KEY"] = "evg_test" }));
    }

    [Fact]
    public void Unknown_subcommand_is_rejected()
    {
        Assert.Throws<ConfigException>(() =>
            ConfigLoader.Load(
                Array.Empty<string>(),
                new Dictionary<string, string?>(StringComparer.Ordinal) { ["EVAGENE_API_KEY"] = "evg_test" }));
    }
}
