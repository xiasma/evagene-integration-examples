using Microsoft.Data.Sqlite;

using Xunit;

namespace WebhookAuditBlotter.Tests;

public sealed class EventStoreTests : IDisposable
{
    private readonly string dbPath;

    public EventStoreTests()
    {
        this.dbPath = Path.Combine(Path.GetTempPath(), $"blotter-test-{Guid.NewGuid()}.db");
    }

    public void Dispose()
    {
        SqliteConnection.ClearAllPools();
        if (File.Exists(this.dbPath))
        {
            File.Delete(this.dbPath);
        }
    }

    private static void AppendSample(EventStore store, int count)
    {
        for (var i = 1; i <= count; i++)
        {
            store.Append(new AppendArgs(
                ReceivedAt: $"2026-04-20T00:00:0{i}Z",
                EventType: "pedigree.updated",
                Body: $"{{\"n\":{i}}}"));
        }
    }

    [Fact]
    public void Append_returns_inserted_row_id()
    {
        using var store = new EventStore(this.dbPath);
        var first = store.Append(new AppendArgs("2026-04-20T00:00:00Z", "pedigree.created", "{}"));
        var second = store.Append(new AppendArgs("2026-04-20T00:00:01Z", "pedigree.updated", "{}"));
        Assert.Equal(1, first);
        Assert.Equal(2, second);
    }

    [Fact]
    public void First_row_has_empty_prev_hash_subsequent_rows_chain()
    {
        using var store = new EventStore(this.dbPath);
        AppendSample(store, 3);
        var rows = store.List(10, 0);
        Assert.Equal(string.Empty, rows[0].PrevHash);
        Assert.Equal(rows[0].RowHash, rows[1].PrevHash);
        Assert.Equal(rows[1].RowHash, rows[2].PrevHash);
    }

    [Fact]
    public void List_honours_limit_and_offset()
    {
        using var store = new EventStore(this.dbPath);
        AppendSample(store, 5);
        Assert.Equal(2, store.List(2, 0).Count);
        Assert.Equal(2, store.List(2, 3).Count);
        Assert.Single(store.List(10, 4));
    }

    [Fact]
    public void VerifyChain_returns_ok_when_log_untouched()
    {
        using var store = new EventStore(this.dbPath);
        AppendSample(store, 3);
        var result = store.VerifyChain();
        Assert.True(result.Ok);
        Assert.Null(result.BreakAt);
    }

    [Fact]
    public void VerifyChain_detects_out_of_band_body_edit()
    {
        using (var store = new EventStore(this.dbPath))
        {
            AppendSample(store, 3);
        }

        using (var direct = new SqliteConnection($"Data Source={this.dbPath}"))
        {
            direct.Open();
            using var cmd = direct.CreateCommand();
            cmd.CommandText = "UPDATE events SET body = $body WHERE id = $id";
            cmd.Parameters.AddWithValue("$body", "{\"tampered\":true}");
            cmd.Parameters.AddWithValue("$id", 2);
            cmd.ExecuteNonQuery();
        }

        using var reopened = new EventStore(this.dbPath);
        var result = reopened.VerifyChain();
        Assert.False(result.Ok);
        Assert.Equal(2, result.BreakAt);
    }
}
