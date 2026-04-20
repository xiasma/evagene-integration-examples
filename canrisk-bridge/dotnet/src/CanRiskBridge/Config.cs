using System.Text.RegularExpressions;

namespace CanRiskBridge;

public sealed class ConfigException : Exception
{
    public ConfigException(string message) : base(message) { }
}

public sealed record Config(
    string BaseUrl,
    string ApiKey,
    string PedigreeId,
    string OutputDir,
    bool OpenBrowser);

public static class ConfigLoader
{
    public const string DefaultBaseUrl = "https://evagene.net";

    private static readonly Regex UuidPattern = new(
        @"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        RegexOptions.IgnoreCase | RegexOptions.Compiled);

    public static Config Load(string[] args, IReadOnlyDictionary<string, string?> env)
    {
        var parsed = ParseArgs(args);

        var apiKey = (Read(env, "EVAGENE_API_KEY") ?? string.Empty).Trim();
        if (apiKey.Length == 0)
        {
            throw new ConfigException("EVAGENE_API_KEY environment variable is required.");
        }

        RequireUuid(parsed.PedigreeId, "pedigree-id");

        var baseUrl = (Read(env, "EVAGENE_BASE_URL") ?? string.Empty).Trim();
        if (baseUrl.Length == 0)
        {
            baseUrl = DefaultBaseUrl;
        }

        return new Config(
            BaseUrl: baseUrl,
            ApiKey: apiKey,
            PedigreeId: parsed.PedigreeId,
            OutputDir: parsed.OutputDir ?? Directory.GetCurrentDirectory(),
            OpenBrowser: parsed.OpenBrowser);
    }

    private sealed record ParsedArgs(string PedigreeId, string? OutputDir, bool OpenBrowser);

    private static ParsedArgs ParseArgs(string[] args)
    {
        string? pedigreeId = null;
        string? outputDir = null;
        var openBrowser = false;

        var index = 0;
        while (index < args.Length)
        {
            var token = args[index];
            if (token == "--output-dir")
            {
                if (index + 1 >= args.Length)
                {
                    throw new ConfigException("--output-dir requires a value");
                }
                outputDir = args[index + 1];
                index += 2;
            }
            else if (token == "--open")
            {
                openBrowser = true;
                index += 1;
            }
            else if (!token.StartsWith("--", StringComparison.Ordinal) && pedigreeId is null)
            {
                pedigreeId = token;
                index += 1;
            }
            else
            {
                throw new ConfigException($"Unexpected argument: {token}");
            }
        }

        if (pedigreeId is null)
        {
            throw new ConfigException("pedigree-id is required");
        }
        return new ParsedArgs(pedigreeId, outputDir, openBrowser);
    }

    private static void RequireUuid(string value, string label)
    {
        if (!UuidPattern.IsMatch(value))
        {
            throw new ConfigException($"{label} must be a UUID, got: {value}");
        }
    }

    private static string? Read(IReadOnlyDictionary<string, string?> env, string key)
    {
        return env.TryGetValue(key, out var value) ? value : null;
    }
}
