namespace FamilyIntake;

public sealed class ConfigException : Exception
{
    public ConfigException(string message) : base(message) { }
}

public sealed record Config(string BaseUrl, string ApiKey, int Port);

public static class ConfigLoader
{
    public const string DefaultBaseUrl = "https://evagene.net";
    public const int DefaultPort = 3000;
    private const int MinPort = 1;
    private const int MaxPort = 65_535;

    public static Config Load(IReadOnlyDictionary<string, string?> env)
    {
        var apiKey = (Read(env, "EVAGENE_API_KEY") ?? string.Empty).Trim();
        if (apiKey.Length == 0)
        {
            throw new ConfigException("EVAGENE_API_KEY environment variable is required.");
        }

        var baseUrl = (Read(env, "EVAGENE_BASE_URL") ?? string.Empty).Trim();
        if (baseUrl.Length == 0)
        {
            baseUrl = DefaultBaseUrl;
        }

        return new Config(baseUrl, apiKey, ParsePort(Read(env, "PORT")));
    }

    private static int ParsePort(string? raw)
    {
        if (raw is null || raw.Trim().Length == 0)
        {
            return DefaultPort;
        }
        if (!int.TryParse(raw.Trim(), out var parsed) || parsed < MinPort || parsed > MaxPort)
        {
            throw new ConfigException($"PORT must be an integer between {MinPort} and {MaxPort}; got '{raw}'.");
        }
        return parsed;
    }

    private static string? Read(IReadOnlyDictionary<string, string?> env, string key)
    {
        return env.TryGetValue(key, out var value) ? value : null;
    }
}
