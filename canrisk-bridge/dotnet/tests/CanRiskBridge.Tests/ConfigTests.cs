using Xunit;

namespace CanRiskBridge.Tests;

public sealed class ConfigTests
{
    private const string ValidUuid = "11111111-1111-1111-1111-111111111111";

    [Fact]
    public void Defaults_base_url_and_output_dir_when_env_unset()
    {
        var config = ConfigLoader.Load(
            new[] { ValidUuid },
            Env(apiKey: "evg_test"));

        Assert.Equal(ConfigLoader.DefaultBaseUrl, config.BaseUrl);
        Assert.Equal("https://evagene.net", config.BaseUrl);
        Assert.Equal("evg_test", config.ApiKey);
        Assert.Equal(ValidUuid, config.PedigreeId);
        Assert.Equal(Directory.GetCurrentDirectory(), config.OutputDir);
        Assert.False(config.OpenBrowser);
    }

    [Fact]
    public void Honours_custom_base_url()
    {
        var config = ConfigLoader.Load(
            new[] { ValidUuid },
            Env(apiKey: "evg_test", baseUrl: "https://evagene.example"));

        Assert.Equal("https://evagene.example", config.BaseUrl);
    }

    [Fact]
    public void Parses_output_dir_and_open_flags()
    {
        var config = ConfigLoader.Load(
            new[] { ValidUuid, "--output-dir", "/tmp/x", "--open" },
            Env(apiKey: "evg_test"));

        Assert.Equal("/tmp/x", config.OutputDir);
        Assert.True(config.OpenBrowser);
    }

    [Fact]
    public void Missing_api_key_throws()
    {
        Assert.Throws<ConfigException>(() => ConfigLoader.Load(new[] { ValidUuid }, Env()));
    }

    [Fact]
    public void Pedigree_id_must_be_uuid()
    {
        Assert.Throws<ConfigException>(
            () => ConfigLoader.Load(new[] { "not-a-uuid" }, Env(apiKey: "evg_test")));
    }

    private static IReadOnlyDictionary<string, string?> Env(
        string? apiKey = null,
        string? baseUrl = null)
    {
        var dict = new Dictionary<string, string?>(StringComparer.Ordinal);
        if (apiKey is not null) dict["EVAGENE_API_KEY"] = apiKey;
        if (baseUrl is not null) dict["EVAGENE_BASE_URL"] = baseUrl;
        return dict;
    }
}
