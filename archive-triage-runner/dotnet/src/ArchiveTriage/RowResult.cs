namespace ArchiveTriage;

public sealed record RowResult(
    string PedigreeId,
    string ProbandName,
    string Category,
    bool? ReferForGenetics,
    int TriggersMatchedCount,
    string Error);
