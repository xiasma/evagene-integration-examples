using System.Collections;

using WebhookAuditBlotter;

try
{
    var env = new Dictionary<string, string?>(StringComparer.Ordinal);
    foreach (DictionaryEntry entry in Environment.GetEnvironmentVariables())
    {
        env[(string)entry.Key] = entry.Value as string;
    }

    var config = ConfigLoader.Load(env);
    var store = new EventStore(config.SqlitePath);
    var handler = new WebhookHandler(config.WebhookSecret, store, new SystemClock());
    var app = Server.Build(handler, store, config.Port);

    Console.Out.WriteLine($"Webhook audit blotter listening on http://localhost:{config.Port}/");
    await app.RunAsync().ConfigureAwait(false);
    return 0;
}
catch (ConfigException e)
{
    await Console.Error.WriteLineAsync($"error: {e.Message}").ConfigureAwait(false);
    return 64;
}
