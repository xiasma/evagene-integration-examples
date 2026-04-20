using System.Text;
using System.Text.Json;

namespace WebhookAuditBlotter;

public enum WebhookOutcomeStatus
{
    Accepted,
    BadSignature,
    BadRequest,
}

public sealed record WebhookOutcome(WebhookOutcomeStatus Status, long? RowId = null, string? Reason = null);

public sealed record IncomingDelivery(
    byte[] RawBody,
    string? SignatureHeader,
    string? EventTypeHeader);

public interface IAppendOnlyStore
{
    long Append(AppendArgs args);
}

public interface IClock
{
    string NowIso();
}

public sealed class SystemClock : IClock
{
    public string NowIso() => DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ", System.Globalization.CultureInfo.InvariantCulture);
}

/// <summary>
/// Framework-agnostic webhook orchestration: verify signature,
/// persist, produce an outcome.
/// </summary>
public sealed class WebhookHandler
{
    private readonly string secret;
    private readonly IAppendOnlyStore store;
    private readonly IClock clock;

    public WebhookHandler(string secret, IAppendOnlyStore store, IClock clock)
    {
        this.secret = secret;
        this.store = store;
        this.clock = clock;
    }

    public WebhookOutcome Handle(IncomingDelivery delivery)
    {
        if (!SignatureVerifier.Verify(delivery.RawBody, delivery.SignatureHeader, this.secret))
        {
            return new WebhookOutcome(WebhookOutcomeStatus.BadSignature);
        }
        var bodyText = Encoding.UTF8.GetString(delivery.RawBody);
        if (!IsJsonObject(bodyText))
        {
            return new WebhookOutcome(WebhookOutcomeStatus.BadRequest, Reason: "Body is not a JSON object.");
        }
        var eventType = (delivery.EventTypeHeader ?? string.Empty).Trim();
        if (eventType.Length == 0)
        {
            return new WebhookOutcome(WebhookOutcomeStatus.BadRequest, Reason: "Missing X-Evagene-Event header.");
        }
        var id = this.store.Append(new AppendArgs(this.clock.NowIso(), eventType, bodyText));
        return new WebhookOutcome(WebhookOutcomeStatus.Accepted, RowId: id);
    }

    private static bool IsJsonObject(string text)
    {
        try
        {
            using var doc = JsonDocument.Parse(text);
            return doc.RootElement.ValueKind == JsonValueKind.Object;
        }
        catch (JsonException)
        {
            return false;
        }
    }
}
