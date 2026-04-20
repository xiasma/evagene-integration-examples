using System.Collections;

using FamilyIntake;

var env = new Dictionary<string, string?>(StringComparer.Ordinal);
foreach (DictionaryEntry entry in Environment.GetEnvironmentVariables())
{
    env[(string)entry.Key] = entry.Value as string;
}

return await App.RunAsync(env, Console.Out, Console.Error).ConfigureAwait(false);
