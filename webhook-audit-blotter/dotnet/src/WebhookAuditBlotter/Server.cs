using System.Text.Json;

using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;

namespace WebhookAuditBlotter;

/// <summary>
/// ASP.NET Core surface: three routes, no business logic.  Everything
/// non-HTTP lives in <see cref="WebhookHandler"/> and <see cref="EventStore"/>.
/// </summary>
public static class Server
{
    private const int DefaultPageSize = 100;
    private const int MaxPageSize = 1000;

    public static WebApplication Build(WebhookHandler handler, EventStore store, int port)
    {
        var builder = WebApplication.CreateBuilder();
        builder.WebHost.UseUrls($"http://0.0.0.0:{port}");
        builder.Logging.ClearProviders();

        var app = builder.Build();

        app.MapPost("/webhook", async (HttpRequest request) =>
        {
            var rawBody = await ReadRawBodyAsync(request).ConfigureAwait(false);
            var outcome = handler.Handle(new IncomingDelivery(
                RawBody: rawBody,
                SignatureHeader: FirstHeader(request, "X-Evagene-Signature-256"),
                EventTypeHeader: FirstHeader(request, "X-Evagene-Event")));
            return OutcomeToResult(outcome);
        });

        app.MapGet("/events", (HttpRequest request) =>
        {
            var (limit, offset) = ParsePagination(request);
            var rows = store.List(limit, offset);
            return Results.Text(
                content: string.Concat(rows.Select(r => JsonSerializer.Serialize(r) + "\n")),
                contentType: "application/x-ndjson");
        });

        app.MapGet("/events/verify", () =>
        {
            var result = store.VerifyChain();
            return Results.Json(new { ok = result.Ok, break_at = result.BreakAt });
        });

        return app;
    }

    private static async Task<byte[]> ReadRawBodyAsync(HttpRequest request)
    {
        using var buffer = new MemoryStream();
        await request.Body.CopyToAsync(buffer).ConfigureAwait(false);
        return buffer.ToArray();
    }

    private static string? FirstHeader(HttpRequest request, string name)
        => request.Headers.TryGetValue(name, out var value) ? value.FirstOrDefault() : null;

    private static IResult OutcomeToResult(WebhookOutcome outcome) => outcome.Status switch
    {
        WebhookOutcomeStatus.Accepted => Results.NoContent(),
        WebhookOutcomeStatus.BadSignature => Results.Text("Invalid signature.", "text/plain", statusCode: 401),
        WebhookOutcomeStatus.BadRequest => Results.Text(outcome.Reason ?? "Bad request.", "text/plain", statusCode: 400),
        _ => Results.StatusCode(500),
    };

    private static (int Limit, int Offset) ParsePagination(HttpRequest request)
    {
        var limit = Clamp(ReadInt(request.Query["limit"], DefaultPageSize), 1, MaxPageSize);
        var offset = Math.Max(0, ReadInt(request.Query["offset"], 0));
        return (limit, offset);
    }

    private static int ReadInt(Microsoft.Extensions.Primitives.StringValues raw, int fallback)
    {
        var first = raw.FirstOrDefault();
        return int.TryParse(first, out var parsed) ? parsed : fallback;
    }

    private static int Clamp(int value, int lower, int upper) => Math.Min(Math.Max(value, lower), upper);
}
