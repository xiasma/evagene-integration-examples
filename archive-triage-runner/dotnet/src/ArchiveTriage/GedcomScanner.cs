namespace ArchiveTriage;

public sealed record GedcomFile(string Path, string Content);

public sealed class ScannerException : Exception
{
    public ScannerException(string message) : base(message) { }
}

public sealed class GedcomScanner
{
    private const string GedcomSuffix = ".ged";

    private readonly string root;

    public GedcomScanner(string root)
    {
        this.root = root;
    }

    public IEnumerable<GedcomFile> Scan()
    {
        if (!Directory.Exists(this.root))
        {
            throw new ScannerException(
                $"Input path is not a directory: {this.root} "
                + "(pass a folder that contains *.ged files).");
        }

        var files = Directory.EnumerateFiles(this.root, $"*{GedcomSuffix}", SearchOption.AllDirectories)
            .OrderBy(path => path, StringComparer.Ordinal);

        foreach (var path in files)
        {
            yield return new GedcomFile(path, File.ReadAllText(path));
        }
    }
}
