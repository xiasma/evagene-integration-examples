using Xunit;

namespace WebhookAuditBlotter.Tests;

public sealed class ConfigTests
{
    private static IReadOnlyDictionary<string, string?> Env(
        string? secret = null,
        string? port = null,
        string? sqlitePath = null)
    {
        var dict = new Dictionary<string, string?>(StringComparer.Ordinal);
        if (secret is not null) dict["EVAGENE_WEBHOOK_SECRET"] = secret;
        if (port is not null) dict["PORT"] = port;
        if (sqlitePath is not null) dict["SQLITE_PATH"] = sqlitePath;
        return dict;
    }

    [Fact]
    public void Defaults_port_and_sqlite_path_when_env_unset()
    {
        var config = ConfigLoader.Load(Env(secret: "shhh"));

        Assert.Equal(ConfigLoader.DefaultPort, config.Port);
        Assert.Equal(ConfigLoader.DefaultSqlitePath, config.SqlitePath);
        Assert.Equal("shhh", config.WebhookSecret);
    }

    [Fact]
    public void Missing_secret_throws()
    {
        Assert.Throws<ConfigException>(() => ConfigLoader.Load(Env()));
    }

    [Fact]
    public void Invalid_port_throws()
    {
        Assert.Throws<ConfigException>(() => ConfigLoader.Load(Env(secret: "shhh", port: "0")));
        Assert.Throws<ConfigException>(() => ConfigLoader.Load(Env(secret: "shhh", port: "999999")));
        Assert.Throws<ConfigException>(() => ConfigLoader.Load(Env(secret: "shhh", port: "abc")));
    }

    [Fact]
    public void Custom_port_and_sqlite_path_honoured()
    {
        var config = ConfigLoader.Load(Env(secret: "shhh", port: "5050", sqlitePath: "/tmp/foo.db"));

        Assert.Equal(5050, config.Port);
        Assert.Equal("/tmp/foo.db", config.SqlitePath);
    }
}
