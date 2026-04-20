using Xunit;

namespace ArchiveTriage.Tests;

public sealed class CsvWriterTests
{
    [Fact]
    public async Task Writes_header_first()
    {
        var output = await WriteAsync(Array.Empty<RowResult>());

        Assert.Equal(
            string.Join(',', CsvWriter.Header),
            SplitLines(output)[0]);
    }

    [Fact]
    public async Task Formats_successful_row_with_true_refer_flag()
    {
        var row = new RowResult(
            PedigreeId: "pedigree-1",
            ProbandName: "Jane Doe",
            Category: "high",
            ReferForGenetics: true,
            TriggersMatchedCount: 2,
            Error: string.Empty);

        var lines = SplitLines(await WriteAsync(new[] { row }));

        Assert.Equal("pedigree-1,Jane Doe,high,true,2,", lines[1]);
    }

    [Fact]
    public async Task Formats_failure_row_with_empty_bool_and_plain_error()
    {
        var row = new RowResult(
            PedigreeId: string.Empty,
            ProbandName: "family",
            Category: string.Empty,
            ReferForGenetics: null,
            TriggersMatchedCount: 0,
            Error: "create_pedigree failed: HTTP 503");

        var lines = SplitLines(await WriteAsync(new[] { row }));

        Assert.Equal(",family,,,0,create_pedigree failed: HTTP 503", lines[1]);
    }

    [Fact]
    public async Task Quotes_commas_inside_names()
    {
        var row = new RowResult(
            PedigreeId: "pedigree-1",
            ProbandName: "Doe, Jane",
            Category: "moderate",
            ReferForGenetics: false,
            TriggersMatchedCount: 1,
            Error: string.Empty);

        var lines = SplitLines(await WriteAsync(new[] { row }));

        Assert.Contains("\"Doe, Jane\"", lines[1], StringComparison.Ordinal);
    }

    private static async Task<string> WriteAsync(IReadOnlyList<RowResult> rows)
    {
        using var sink = new StringWriter();
        await new CsvWriter(sink).WriteAsync(ToAsync(rows));
        return sink.ToString();
    }

    private static async IAsyncEnumerable<RowResult> ToAsync(IEnumerable<RowResult> rows)
    {
        foreach (var row in rows)
        {
            yield return row;
        }
        await Task.CompletedTask;
    }

    private static string[] SplitLines(string value) =>
        value.Split('\n').Select(line => line.TrimEnd('\r')).Where(line => line.Length > 0).ToArray();
}
