using System.Security.Cryptography;
using System.Text;

using Microsoft.Data.Sqlite;

namespace WebhookAuditBlotter;

public sealed record AppendArgs(string ReceivedAt, string EventType, string Body);

public sealed record EventRow(
    long Id,
    string ReceivedAt,
    string EventType,
    string Body,
    string PrevHash,
    string RowHash);

public sealed record VerifyResult(bool Ok, long? BreakAt);

/// <summary>
/// SQLite-backed, hash-chained audit log.  Each row's <c>row_hash</c>
/// is SHA-256 over <c>prev_hash || received_at || event_type || body</c>
/// (UTF-8 concatenation).  Re-running that computation across every row
/// reveals any out-of-band edit.
/// </summary>
public sealed class EventStore : IAppendOnlyStore, IDisposable
{
    private const string Schema = @"
        CREATE TABLE IF NOT EXISTS events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            received_at TEXT NOT NULL,
            event_type  TEXT NOT NULL,
            body        TEXT NOT NULL,
            prev_hash   TEXT NOT NULL,
            row_hash    TEXT NOT NULL
        );";

    private readonly SqliteConnection connection;

    public EventStore(string path)
    {
        this.connection = new SqliteConnection($"Data Source={path}");
        this.connection.Open();
        using var cmd = this.connection.CreateCommand();
        cmd.CommandText = Schema;
        cmd.ExecuteNonQuery();
    }

    public long Append(AppendArgs args)
    {
        var prevHash = this.LatestRowHash();
        var rowHash = HashChainEntry(prevHash, args);

        using var cmd = this.connection.CreateCommand();
        cmd.CommandText = @"
            INSERT INTO events (received_at, event_type, body, prev_hash, row_hash)
            VALUES ($received_at, $event_type, $body, $prev_hash, $row_hash);
            SELECT last_insert_rowid();";
        cmd.Parameters.AddWithValue("$received_at", args.ReceivedAt);
        cmd.Parameters.AddWithValue("$event_type", args.EventType);
        cmd.Parameters.AddWithValue("$body", args.Body);
        cmd.Parameters.AddWithValue("$prev_hash", prevHash);
        cmd.Parameters.AddWithValue("$row_hash", rowHash);
        var id = (long)(cmd.ExecuteScalar() ?? 0L);
        return id;
    }

    public IReadOnlyList<EventRow> List(int limit, int offset)
    {
        using var cmd = this.connection.CreateCommand();
        cmd.CommandText = @"
            SELECT id, received_at, event_type, body, prev_hash, row_hash
            FROM events ORDER BY id ASC LIMIT $limit OFFSET $offset";
        cmd.Parameters.AddWithValue("$limit", limit);
        cmd.Parameters.AddWithValue("$offset", offset);

        var rows = new List<EventRow>();
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            rows.Add(ReadRow(reader));
        }
        return rows;
    }

    public VerifyResult VerifyChain()
    {
        using var cmd = this.connection.CreateCommand();
        cmd.CommandText = @"
            SELECT id, received_at, event_type, body, prev_hash, row_hash
            FROM events ORDER BY id ASC";

        var expectedPrev = string.Empty;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var row = ReadRow(reader);
            var recomputed = HashChainEntry(expectedPrev,
                new AppendArgs(row.ReceivedAt, row.EventType, row.Body));
            if (row.PrevHash != expectedPrev || row.RowHash != recomputed)
            {
                return new VerifyResult(false, row.Id);
            }
            expectedPrev = row.RowHash;
        }
        return new VerifyResult(true, null);
    }

    public void Dispose()
    {
        this.connection.Dispose();
    }

    private string LatestRowHash()
    {
        using var cmd = this.connection.CreateCommand();
        cmd.CommandText = "SELECT row_hash FROM events ORDER BY id DESC LIMIT 1";
        return cmd.ExecuteScalar() as string ?? string.Empty;
    }

    private static EventRow ReadRow(SqliteDataReader reader) => new(
        Id: reader.GetInt64(0),
        ReceivedAt: reader.GetString(1),
        EventType: reader.GetString(2),
        Body: reader.GetString(3),
        PrevHash: reader.GetString(4),
        RowHash: reader.GetString(5));

    private static string HashChainEntry(string prevHash, AppendArgs args)
    {
        var bytes = Encoding.UTF8.GetBytes(prevHash + args.ReceivedAt + args.EventType + args.Body);
        return Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
    }
}
