using Xunit;

namespace XegUpgrader.Tests;

public sealed class ConfigTests
{
    private const string InputPath = "/tmp/legacy-family.xeg";

    [Fact]
    public void Defaults_mode_to_preview_and_base_url_when_env_unset()
    {
        var config = ConfigLoader.Load(new[] { InputPath }, Env(apiKey: "evg_test"));

        Assert.Equal(RunMode.Preview, config.Mode);
        Assert.Equal(ConfigLoader.DefaultBaseUrl, config.BaseUrl);
        Assert.Equal("https://evagene.net", config.BaseUrl);
        Assert.Equal(InputPath, config.InputPath);
    }

    [Fact]
    public void Create_flag_selects_create_mode()
    {
        var config = ConfigLoader.Load(
            new[] { InputPath, "--create" }, Env(apiKey: "evg_test"));

        Assert.Equal(RunMode.Create, config.Mode);
    }

    [Fact]
    public void Name_flag_overrides_default_display_name()
    {
        var config = ConfigLoader.Load(
            new[] { InputPath, "--create", "--name", "Hill family (2019)" },
            Env(apiKey: "evg_test"));

        Assert.Equal("Hill family (2019)", config.DisplayName);
    }

    [Fact]
    public void Default_display_name_is_filename_without_extension()
    {
        var config = ConfigLoader.Load(new[] { InputPath }, Env(apiKey: "evg_test"));

        Assert.Equal("legacy-family", config.DisplayName);
    }

    [Fact]
    public void Preview_and_create_are_mutually_exclusive()
    {
        Assert.Throws<ConfigException>(
            () => ConfigLoader.Load(
                new[] { InputPath, "--preview", "--create" },
                Env(apiKey: "evg_test")));
    }

    [Fact]
    public void Missing_api_key_throws()
    {
        Assert.Throws<ConfigException>(
            () => ConfigLoader.Load(new[] { InputPath }, Env()));
    }

    [Fact]
    public void Missing_input_path_throws()
    {
        Assert.Throws<ConfigException>(
            () => ConfigLoader.Load(Array.Empty<string>(), Env(apiKey: "evg_test")));
    }

    [Fact]
    public void Honours_custom_base_url()
    {
        var config = ConfigLoader.Load(
            new[] { InputPath },
            Env(apiKey: "evg_test", baseUrl: "https://evagene.example"));

        Assert.Equal("https://evagene.example", config.BaseUrl);
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
