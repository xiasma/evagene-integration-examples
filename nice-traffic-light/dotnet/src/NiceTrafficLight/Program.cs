using System.Collections;

using NiceTrafficLight;

var env = new Dictionary<string, string?>(StringComparer.Ordinal);
foreach (DictionaryEntry entry in Environment.GetEnvironmentVariables())
{
    env[(string)entry.Key] = entry.Value as string;
}

return await App.RunAsync(args, env, Console.Out, Console.Error).ConfigureAwait(false);
