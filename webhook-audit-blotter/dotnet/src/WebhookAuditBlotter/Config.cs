namespace WebhookAuditBlotter;

public sealed class ConfigException : Exception
{
    public ConfigException(string message) : base(message) { }
}

public sealed record Config(int Port, string WebhookSecret, string SqlitePath);

public static class ConfigLoader
{
    public const int DefaultPort = 4000;
    public const string DefaultSqlitePath = "./blotter.db";
    private const int MaxPort = 65_535;

    public static Config Load(IReadOnlyDictionary<string, string?> env)
    {
        var secret = (Read(env, "EVAGENE_WEBHOOK_SECRET") ?? string.Empty).Trim();
        if (secret.Length == 0)
        {
            throw new ConfigException("EVAGENE_WEBHOOK_SECRET environment variable is required.");
        }

        var sqlitePath = (Read(env, "SQLITE_PATH") ?? string.Empty).Trim();
        if (sqlitePath.Length == 0)
        {
            sqlitePath = DefaultSqlitePath;
        }

        return new Config(ParsePort(Read(env, "PORT")), secret, sqlitePath);
    }

    private static int ParsePort(string? raw)
    {
        if (string.IsNullOrWhiteSpace(raw))
        {
            return DefaultPort;
        }
        if (!int.TryParse(raw, out var parsed) || parsed < 1 || parsed > MaxPort)
        {
            throw new ConfigException($"PORT must be an integer between 1 and {MaxPort}; got '{raw}'.");
        }
        return parsed;
    }

    private static string? Read(IReadOnlyDictionary<string, string?> env, string key)
        => env.TryGetValue(key, out var value) ? value : null;
}
