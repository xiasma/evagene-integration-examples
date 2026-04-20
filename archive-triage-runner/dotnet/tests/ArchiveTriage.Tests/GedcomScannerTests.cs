using Xunit;

namespace ArchiveTriage.Tests;

public sealed class GedcomScannerTests : IDisposable
{
    private readonly string tempDir;

    public GedcomScannerTests()
    {
        this.tempDir = Path.Combine(Path.GetTempPath(), "ArchiveTriageTests-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(this.tempDir);
    }

    public void Dispose()
    {
        if (Directory.Exists(this.tempDir))
        {
            Directory.Delete(this.tempDir, recursive: true);
        }
    }

    [Fact]
    public void Yields_ged_files_in_sorted_order()
    {
        File.WriteAllText(Path.Combine(this.tempDir, "b.ged"), "B");
        File.WriteAllText(Path.Combine(this.tempDir, "a.ged"), "A");

        var files = new GedcomScanner(this.tempDir).Scan().ToList();

        Assert.Equal(new[] { "a.ged", "b.ged" }, files.Select(f => Path.GetFileName(f.Path)));
        Assert.Equal("A", files[0].Content);
        Assert.Equal("B", files[1].Content);
    }

    [Fact]
    public void Walks_subdirectories()
    {
        var nested = Path.Combine(this.tempDir, "archive-2019");
        Directory.CreateDirectory(nested);
        File.WriteAllText(Path.Combine(nested, "family.ged"), "nested");

        var files = new GedcomScanner(this.tempDir).Scan().ToList();

        Assert.Single(files);
        Assert.Equal("family.ged", Path.GetFileName(files[0].Path));
    }

    [Fact]
    public void Skips_non_ged_files()
    {
        File.WriteAllText(Path.Combine(this.tempDir, "notes.txt"), "ignored");
        File.WriteAllText(Path.Combine(this.tempDir, "a.ged"), "A");

        var files = new GedcomScanner(this.tempDir).Scan().ToList();

        Assert.Single(files);
        Assert.Equal("a.ged", Path.GetFileName(files[0].Path));
    }

    [Fact]
    public void Missing_directory_throws()
    {
        var missing = Path.Combine(this.tempDir, "does-not-exist");

        Assert.Throws<ScannerException>(() => new GedcomScanner(missing).Scan().ToList());
    }
}
