using System.Security.Cryptography;
using System.Text;

using Xunit;

namespace WebhookAuditBlotter.Tests;

public sealed class WebhookHandlerTests
{
    private const string Secret = "shared-secret";
    private const string FixedNow = "2026-04-20T09:15:22Z";

    private sealed class RecordingStore : IAppendOnlyStore
    {
        public List<AppendArgs> Appended { get; } = [];
        public long Append(AppendArgs args)
        {
            this.Appended.Add(args);
            return this.Appended.Count;
        }
    }

    private sealed class FixedClock : IClock
    {
        public string NowIso() => FixedNow;
    }

    private static string Sign(byte[] body, string secret = Secret)
    {
        var hash = HMACSHA256.HashData(Encoding.UTF8.GetBytes(secret), body);
        return $"sha256={Convert.ToHexString(hash).ToLowerInvariant()}";
    }

    private static WebhookHandler Handler(RecordingStore store) =>
        new(Secret, store, new FixedClock());

    [Fact]
    public void Valid_signature_and_json_body_appends_and_returns_accepted()
    {
        var body = Encoding.UTF8.GetBytes("{\"event\":\"pedigree.updated\"}");
        var store = new RecordingStore();

        var outcome = Handler(store).Handle(new IncomingDelivery(body, Sign(body), "pedigree.updated"));

        Assert.Equal(WebhookOutcomeStatus.Accepted, outcome.Status);
        Assert.Single(store.Appended);
        Assert.Equal(FixedNow, store.Appended[0].ReceivedAt);
        Assert.Equal("pedigree.updated", store.Appended[0].EventType);
        Assert.Equal(Encoding.UTF8.GetString(body), store.Appended[0].Body);
    }

    [Fact]
    public void Bad_signature_returns_bad_signature_and_does_not_append()
    {
        var body = Encoding.UTF8.GetBytes("{\"event\":\"pedigree.updated\"}");
        var store = new RecordingStore();

        var outcome = Handler(store).Handle(new IncomingDelivery(body, Sign(body, "wrong"), "pedigree.updated"));

        Assert.Equal(WebhookOutcomeStatus.BadSignature, outcome.Status);
        Assert.Empty(store.Appended);
    }

    [Fact]
    public void Missing_signature_header_rejected_as_bad_signature()
    {
        var body = Encoding.UTF8.GetBytes("{\"event\":\"pedigree.updated\"}");
        var store = new RecordingStore();

        var outcome = Handler(store).Handle(new IncomingDelivery(body, null, "pedigree.updated"));

        Assert.Equal(WebhookOutcomeStatus.BadSignature, outcome.Status);
    }

    [Fact]
    public void Non_json_body_bad_request_nothing_stored()
    {
        var body = Encoding.UTF8.GetBytes("not-json");
        var store = new RecordingStore();

        var outcome = Handler(store).Handle(new IncomingDelivery(body, Sign(body), "pedigree.updated"));

        Assert.Equal(WebhookOutcomeStatus.BadRequest, outcome.Status);
        Assert.Empty(store.Appended);
    }

    [Fact]
    public void Json_array_also_rejected_as_bad_request()
    {
        var body = Encoding.UTF8.GetBytes("[1,2,3]");
        var store = new RecordingStore();

        var outcome = Handler(store).Handle(new IncomingDelivery(body, Sign(body), "pedigree.updated"));

        Assert.Equal(WebhookOutcomeStatus.BadRequest, outcome.Status);
    }

    [Fact]
    public void Missing_event_header_rejected_as_bad_request()
    {
        var body = Encoding.UTF8.GetBytes("{\"ok\":true}");
        var store = new RecordingStore();

        var outcome = Handler(store).Handle(new IncomingDelivery(body, Sign(body), null));

        Assert.Equal(WebhookOutcomeStatus.BadRequest, outcome.Status);
    }
}
