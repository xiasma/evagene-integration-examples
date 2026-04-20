using Xunit;

namespace ArchiveTriage.Tests;

public sealed class ConfigTests
{
    [Fact]
    public void Defaults_base_url_and_concurrency_when_env_unset()
    {
        var config = ConfigLoader.Load(new[] { "archive" }, Env(apiKey: "evg_test"));

        Assert.Equal(ConfigLoader.DefaultBaseUrl, config.BaseUrl);
        Assert.Equal("https://evagene.net", config.BaseUrl);
        Assert.Equal("evg_test", config.ApiKey);
        Assert.Equal("archive", config.InputDir);
        Assert.Null(config.OutputPath);
        Assert.Equal(ConfigLoader.DefaultConcurrency, config.Concurrency);
    }

    [Fact]
    public void Honours_custom_base_url()
    {
        var config = ConfigLoader.Load(
            new[] { "archive" },
            Env(apiKey: "evg_test", baseUrl: "https://evagene.example"));

        Assert.Equal("https://evagene.example", config.BaseUrl);
    }

    [Fact]
    public void Output_path_captured_when_provided()
    {
        var config = ConfigLoader.Load(
            new[] { "archive", "--output", "out.csv" },
            Env(apiKey: "evg_test"));

        Assert.Equal("out.csv", config.OutputPath);
    }

    [Fact]
    public void Concurrency_captured_when_provided()
    {
        var config = ConfigLoader.Load(
            new[] { "archive", "--concurrency", "8" },
            Env(apiKey: "evg_test"));

        Assert.Equal(8, config.Concurrency);
    }

    [Fact]
    public void Missing_api_key_throws()
    {
        Assert.Throws<ConfigException>(() =>
            ConfigLoader.Load(new[] { "archive" }, Env()));
    }

    [Fact]
    public void Concurrency_must_be_positive()
    {
        Assert.Throws<ConfigException>(() =>
            ConfigLoader.Load(
                new[] { "archive", "--concurrency", "0" },
                Env(apiKey: "evg_test")));
    }

    [Fact]
    public void Missing_input_dir_throws()
    {
        Assert.Throws<ConfigException>(() =>
            ConfigLoader.Load(Array.Empty<string>(), Env(apiKey: "evg_test")));
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
