using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.Hosting;

namespace FamilyIntake;

/// <summary>
/// ASP.NET Core minimal-API surface: routes GET / and POST /submit,
/// delegates domain logic to IntakeService. Kept deliberately thin --
/// if a framework-level concern creeps in here it probably belongs in
/// IntakeService or IntakeSubmissionParser instead.
/// </summary>
public sealed record ServerOptions(IntakeService Service, string EvageneBaseUrl);

public static class Server
{
    public static WebApplication Build(ServerOptions options, int port)
    {
        var builder = WebApplication.CreateBuilder();
        builder.Logging.ClearProviders();
        builder.WebHost.UseUrls($"http://localhost:{port}");

        var app = builder.Build();
        MapRoutes(app, options);
        return app;
    }

    private static void MapRoutes(IEndpointRouteBuilder endpoints, ServerOptions options)
    {
        endpoints.MapGet("/", () => Results.Content(Views.FormPage(), "text/html; charset=utf-8"));
        endpoints.MapPost("/submit", (HttpRequest request) => HandleSubmitAsync(request, options));
    }

    private static async Task<IResult> HandleSubmitAsync(HttpRequest request, ServerOptions options)
    {
        var form = await ReadFormAsync(request).ConfigureAwait(false);

        IntakeSubmission submission;
        try
        {
            submission = IntakeSubmissionParser.Parse(form);
        }
        catch (IntakeValidationException e)
        {
            return Results.Content(Views.ErrorPage(e.Message), "text/html; charset=utf-8", statusCode: 400);
        }

        try
        {
            var result = await options.Service.CreateAsync(submission, request.HttpContext.RequestAborted).ConfigureAwait(false);
            var pedigreeUrl = $"{options.EvageneBaseUrl.TrimEnd('/')}/pedigrees/{result.PedigreeId}";
            return Results.Content(
                Views.SuccessPage(result.PedigreeId, pedigreeUrl, result.RelativesAdded),
                "text/html; charset=utf-8");
        }
        catch (EvageneApiException e)
        {
            return Results.Content(Views.ErrorPage(e.Message), "text/html; charset=utf-8", statusCode: 502);
        }
    }

    private static async Task<IReadOnlyDictionary<string, string>> ReadFormAsync(HttpRequest request)
    {
        var form = await request.ReadFormAsync().ConfigureAwait(false);
        var result = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var field in form)
        {
            result[field.Key] = field.Value.ToString();
        }
        return result;
    }
}
