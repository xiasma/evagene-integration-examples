using System.Diagnostics;

namespace CanRiskBridge;

public interface IBrowserLauncher
{
    void Open(string url);
}

public sealed class ProcessBrowserLauncher : IBrowserLauncher
{
    public void Open(string url)
    {
        using var process = Process.Start(new ProcessStartInfo
        {
            FileName = url,
            UseShellExecute = true,
        });
    }
}

public sealed class OutputSink
{
    public const string CanRiskUploadUrl = "https://canrisk.org";

    private readonly string outputDir;
    private readonly IBrowserLauncher browser;

    public OutputSink(string outputDir, IBrowserLauncher browser)
    {
        this.outputDir = outputDir;
        this.browser = browser;
    }

    public string Save(string pedigreeId, string payload)
    {
        Directory.CreateDirectory(this.outputDir);
        var path = Path.GetFullPath(Path.Combine(this.outputDir, FilenameFor(pedigreeId)));
        File.WriteAllText(path, payload);
        return path;
    }

    public void OpenUploadPage() => this.browser.Open(CanRiskUploadUrl);

    public static string FilenameFor(string pedigreeId) =>
        $"evagene-canrisk-{pedigreeId[..8]}.txt";
}
