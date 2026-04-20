namespace XegUpgrader;

public sealed class ConfigException : Exception
{
    public ConfigException(string message) : base(message) { }
}

public enum RunMode
{
    Preview,
    Create,
}

public sealed record Config(
    string BaseUrl,
    string ApiKey,
    string InputPath,
    RunMode Mode,
    string DisplayName);

public static class ConfigLoader
{
    public const string DefaultBaseUrl = "https://evagene.net";

    public static Config Load(string[] args, IReadOnlyDictionary<string, string?> env)
    {
        var parsed = ParseArgs(args);

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

        var displayName = parsed.DisplayName ?? DefaultDisplayName(parsed.InputPath);

        return new Config(
            BaseUrl: baseUrl,
            ApiKey: apiKey,
            InputPath: parsed.InputPath,
            Mode: parsed.Mode,
            DisplayName: displayName);
    }

    private sealed record ParsedArgs(string InputPath, RunMode Mode, string? DisplayName);

    private static ParsedArgs ParseArgs(string[] args)
    {
        string? inputPath = null;
        string? displayName = null;
        var previewSeen = false;
        var createSeen = false;

        var index = 0;
        while (index < args.Length)
        {
            var token = args[index];
            switch (token)
            {
                case "--preview":
                    previewSeen = true;
                    index += 1;
                    break;
                case "--create":
                    createSeen = true;
                    index += 1;
                    break;
                case "--name":
                    if (index + 1 >= args.Length)
                    {
                        throw new ConfigException("--name requires a value");
                    }
                    displayName = args[index + 1];
                    index += 2;
                    break;
                default:
                    if (token.StartsWith("--", StringComparison.Ordinal))
                    {
                        throw new ConfigException($"Unexpected argument: {token}");
                    }
                    if (inputPath is not null)
                    {
                        throw new ConfigException($"Unexpected argument: {token}");
                    }
                    inputPath = token;
                    index += 1;
                    break;
            }
        }

        if (inputPath is null)
        {
            throw new ConfigException("input .xeg path is required");
        }
        if (previewSeen && createSeen)
        {
            throw new ConfigException("--preview and --create are mutually exclusive");
        }

        var mode = createSeen ? RunMode.Create : RunMode.Preview;
        return new ParsedArgs(inputPath, mode, displayName);
    }

    private static string DefaultDisplayName(string inputPath)
    {
        return Path.GetFileNameWithoutExtension(inputPath);
    }

    private static string? Read(IReadOnlyDictionary<string, string?> env, string key)
    {
        return env.TryGetValue(key, out var value) ? value : null;
    }
}
