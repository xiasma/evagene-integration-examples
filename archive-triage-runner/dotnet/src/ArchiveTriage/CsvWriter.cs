using System.Buffers;

namespace ArchiveTriage;

public sealed class CsvWriter
{
    public static readonly IReadOnlyList<string> Header = new[]
    {
        "pedigree_id",
        "proband_name",
        "category",
        "refer_for_genetics",
        "triggers_matched_count",
        "error",
    };

    private static readonly SearchValues<char> CharactersRequiringQuoting = SearchValues.Create(",\"\n\r");

    private readonly TextWriter sink;

    public CsvWriter(TextWriter sink)
    {
        this.sink = sink;
    }

    public async Task WriteAsync(IAsyncEnumerable<RowResult> rows)
    {
        await this.sink.WriteLineAsync(string.Join(',', Header.Select(EscapeField))).ConfigureAwait(false);
        await foreach (var row in rows.ConfigureAwait(false))
        {
            await this.sink.WriteLineAsync(FormatRow(row)).ConfigureAwait(false);
        }
    }

    private static string FormatRow(RowResult row) => string.Join(
        ',',
        new[]
        {
            EscapeField(row.PedigreeId),
            EscapeField(row.ProbandName),
            EscapeField(row.Category),
            EscapeField(FormatBool(row.ReferForGenetics)),
            EscapeField(row.TriggersMatchedCount.ToString(System.Globalization.CultureInfo.InvariantCulture)),
            EscapeField(row.Error),
        });

    private static string FormatBool(bool? value) => value switch
    {
        null => string.Empty,
        true => "true",
        false => "false",
    };

    private static string EscapeField(string value)
    {
        if (value.AsSpan().IndexOfAny(CharactersRequiringQuoting) < 0)
        {
            return value;
        }
        return "\"" + value.Replace("\"", "\"\"", StringComparison.Ordinal) + "\"";
    }
}
