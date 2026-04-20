using Xunit;

namespace CanRiskBridge.Tests;

public sealed class OutputSinkTests : IDisposable
{
    private const string PedigreeId = "a1cfe665-2e95-4386-9eb8-53d46095478a";

    private readonly string tempDir;

    public OutputSinkTests()
    {
        this.tempDir = Path.Combine(Path.GetTempPath(), $"canrisk-bridge-{Guid.NewGuid():N}");
    }

    [Fact]
    public void Filename_uses_first_eight_chars_of_uuid()
    {
        Assert.Equal("evagene-canrisk-a1cfe665.txt", OutputSink.FilenameFor(PedigreeId));
    }

    [Fact]
    public void Save_writes_payload_to_named_file_in_output_dir()
    {
        var browser = new SpyBrowser();
        var sink = new OutputSink(this.tempDir, browser);
        var payload = $"{CanRiskClient.CanRiskHeader}\nFamID\tName\n";

        var saved = sink.Save(PedigreeId, payload);

        Assert.Equal(
            Path.GetFullPath(Path.Combine(this.tempDir, "evagene-canrisk-a1cfe665.txt")),
            saved);
        Assert.Equal(payload, File.ReadAllText(saved));
    }

    [Fact]
    public void Save_creates_missing_output_dir()
    {
        var nested = Path.Combine(this.tempDir, "nested", "dir");
        var sink = new OutputSink(nested, new SpyBrowser());

        sink.Save(PedigreeId, $"{CanRiskClient.CanRiskHeader}\n");

        Assert.True(Directory.Exists(nested));
    }

    [Fact]
    public void OpenUploadPage_delegates_to_injected_browser()
    {
        var browser = new SpyBrowser();
        var sink = new OutputSink(this.tempDir, browser);

        sink.OpenUploadPage();

        Assert.Equal(new[] { "https://canrisk.org" }, browser.Opened);
    }

    public void Dispose()
    {
        if (Directory.Exists(this.tempDir))
        {
            Directory.Delete(this.tempDir, recursive: true);
        }
    }

    private sealed class SpyBrowser : IBrowserLauncher
    {
        private readonly List<string> opened = new();

        public IReadOnlyList<string> Opened => this.opened;

        public void Open(string url) => this.opened.Add(url);
    }
}
