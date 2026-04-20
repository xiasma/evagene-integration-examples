namespace ArchiveTriage;

public sealed class ConfigException : Exception
{
    public ConfigException(string message) : base(message) { }
}

public sealed record Config(
    string BaseUrl,
    string ApiKey,
    string InputDir,
    string? OutputPath,
    int Concurrency);

public static class ConfigLoader
{
    public const string DefaultBaseUrl = "https://evagene.net";
    public const int DefaultConcurrency = 4;
    private const int MaxConcurrency = 32;

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

        return new Config(
            baseUrl,
            apiKey,
            parsed.InputDir,
            parsed.OutputPath,
            RequirePositive(parsed.Concurrency, "--concurrency"));
    }

    private sealed record ParsedArgs(string InputDir, string? OutputPath, int Concurrency);

    private static ParsedArgs ParseArgs(string[] args)
    {
        string? inputDir = null;
        string? outputPath = null;
        var concurrency = DefaultConcurrency;

        var index = 0;
        while (index < args.Length)
        {
            var token = args[index];
            if (token == "--output")
            {
                if (index + 1 >= args.Length)
                {
                    throw new ConfigException("--output requires a value");
                }
                outputPath = args[index + 1];
                index += 2;
            }
            else if (token == "--concurrency")
            {
                if (index + 1 >= args.Length)
                {
                    throw new ConfigException("--concurrency requires a value");
                }
                if (!int.TryParse(args[index + 1], out concurrency))
                {
                    throw new ConfigException($"--concurrency must be a number, got {args[index + 1]}");
                }
                index += 2;
            }
            else if (!token.StartsWith("--", StringComparison.Ordinal) && inputDir is null)
            {
                inputDir = token;
                index += 1;
            }
            else
            {
                throw new ConfigException($"Unexpected argument: {token}");
            }
        }

        if (inputDir is null)
        {
            throw new ConfigException("input-dir is required");
        }
        return new ParsedArgs(inputDir, outputPath, concurrency);
    }

    private static int RequirePositive(int value, string label)
    {
        if (value < 1 || value > MaxConcurrency)
        {
            throw new ConfigException($"{label} must be between 1 and {MaxConcurrency}, got {value}.");
        }
        return value;
    }

    private static string? Read(IReadOnlyDictionary<string, string?> env, string key) =>
        env.TryGetValue(key, out var value) ? value : null;
}
