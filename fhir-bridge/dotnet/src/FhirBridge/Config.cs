using System.Text.RegularExpressions;

namespace FhirBridge;

public sealed class ConfigException : Exception
{
    public ConfigException(string message) : base(message) { }
}

public enum Mode
{
    Push,
    Pull,
}

public sealed record Config(
    Mode Mode,
    string Subject,
    string FhirBaseUrl,
    string? FhirAuthHeader,
    string EvageneBaseUrl,
    string EvageneApiKey);

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

        if (parsed.Mode == Mode.Push && !UuidPattern.IsMatch(parsed.Subject))
        {
            throw new ConfigException($"pedigree-id must be a UUID, got: {parsed.Subject}");
        }

        var baseUrl = (Read(env, "EVAGENE_BASE_URL") ?? string.Empty).Trim();
        if (baseUrl.Length == 0)
        {
            baseUrl = DefaultBaseUrl;
        }

        return new Config(
            parsed.Mode,
            parsed.Subject,
            parsed.FhirBaseUrl,
            parsed.FhirAuthHeader,
            baseUrl,
            apiKey);
    }

    private sealed record ParsedArgs(Mode Mode, string Subject, string FhirBaseUrl, string? FhirAuthHeader);

    private static ParsedArgs ParseArgs(string[] args)
    {
        if (args.Length == 0)
        {
            throw new ConfigException("Unknown subcommand ''. Expected 'push' or 'pull'.");
        }
        var command = args[0];
        Mode mode;
        string flag;
        if (command == "push")
        {
            mode = Mode.Push;
            flag = "--to";
        }
        else if (command == "pull")
        {
            mode = Mode.Pull;
            flag = "--from";
        }
        else
        {
            throw new ConfigException($"Unknown subcommand '{command}'. Expected 'push' or 'pull'.");
        }

        string? subject = null;
        string? fhirBaseUrl = null;
        string? fhirAuthHeader = null;

        var index = 1;
        while (index < args.Length)
        {
            var token = args[index];
            if (token == flag)
            {
                fhirBaseUrl = RequireFlagValue(args, index + 1, flag);
                index += 2;
            }
            else if (token == "--auth-header")
            {
                fhirAuthHeader = RequireFlagValue(args, index + 1, "--auth-header");
                index += 2;
            }
            else if (!token.StartsWith("--", StringComparison.Ordinal) && subject is null)
            {
                subject = token;
                index += 1;
            }
            else
            {
                throw new ConfigException($"Unexpected argument: {token}");
            }
        }

        if (subject is null)
        {
            throw new ConfigException(
                mode == Mode.Push ? "pedigree-id is required" : "fhir-patient-id is required");
        }
        if (fhirBaseUrl is null)
        {
            throw new ConfigException($"{flag} <fhir-base-url> is required");
        }

        return new ParsedArgs(mode, subject, fhirBaseUrl, fhirAuthHeader);
    }

    private static string RequireFlagValue(string[] args, int index, string flag)
    {
        if (index >= args.Length || args[index].StartsWith("--", StringComparison.Ordinal))
        {
            throw new ConfigException($"{flag} requires a value");
        }
        return args[index];
    }

    private static string? Read(IReadOnlyDictionary<string, string?> env, string key)
    {
        return env.TryGetValue(key, out var value) ? value : null;
    }
}
