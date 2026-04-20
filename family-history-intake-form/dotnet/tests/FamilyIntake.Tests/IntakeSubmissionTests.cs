using Xunit;

namespace FamilyIntake.Tests;

public sealed class IntakeSubmissionTests
{
    [Fact]
    public void Minimal_submission_keeps_only_proband()
    {
        var submission = IntakeSubmissionParser.Parse(Body(("proband_name", "Emma Smith")));

        Assert.Equal("Emma Smith", submission.Proband.DisplayName);
        Assert.Equal(BiologicalSex.Unknown, submission.Proband.BiologicalSex);
        Assert.Null(submission.Proband.YearOfBirth);
        Assert.Null(submission.Mother);
        Assert.Null(submission.Father);
        Assert.Empty(submission.Siblings);
    }

    [Fact]
    public void Proband_name_is_required()
    {
        Assert.Throws<IntakeValidationException>(() => IntakeSubmissionParser.Parse(Body()));
        Assert.Throws<IntakeValidationException>(
            () => IntakeSubmissionParser.Parse(Body(("proband_name", "   "))));
    }

    [Fact]
    public void Parses_proband_sex_and_year_of_birth()
    {
        var submission = IntakeSubmissionParser.Parse(Body(
            ("proband_name", "Emma"),
            ("proband_sex", "female"),
            ("proband_year", "1985")));

        Assert.Equal(BiologicalSex.Female, submission.Proband.BiologicalSex);
        Assert.Equal(1985, submission.Proband.YearOfBirth);
    }

    [Fact]
    public void Rejects_unknown_biological_sex()
    {
        Assert.Throws<IntakeValidationException>(
            () => IntakeSubmissionParser.Parse(Body(
                ("proband_name", "Emma"),
                ("proband_sex", "robot"))));
    }

    [Fact]
    public void Rejects_out_of_range_year_of_birth()
    {
        Assert.Throws<IntakeValidationException>(
            () => IntakeSubmissionParser.Parse(Body(
                ("proband_name", "Emma"),
                ("proband_year", "1700"))));
        Assert.Throws<IntakeValidationException>(
            () => IntakeSubmissionParser.Parse(Body(
                ("proband_name", "Emma"),
                ("proband_year", "2999"))));
    }

    [Fact]
    public void Includes_mother_when_provided_otherwise_omits()
    {
        var withMother = IntakeSubmissionParser.Parse(Body(
            ("proband_name", "Emma"),
            ("mother_name", "Grace Smith"),
            ("mother_year", "1960")));
        Assert.Equal(new RelativeEntry("Grace Smith", 1960), withMother.Mother);

        var withoutMother = IntakeSubmissionParser.Parse(Body(
            ("proband_name", "Emma"),
            ("mother_name", "  ")));
        Assert.Null(withoutMother.Mother);
    }

    [Fact]
    public void Parses_siblings_and_assigns_sex_from_relation()
    {
        var submission = IntakeSubmissionParser.Parse(Body(
            ("proband_name", "Emma"),
            ("sibling_0_name", "Alice"),
            ("sibling_0_relation", "sister"),
            ("sibling_0_year", "1988"),
            ("sibling_1_name", "Bob"),
            ("sibling_1_relation", "half_brother")));

        Assert.Equal(2, submission.Siblings.Count);
        Assert.Equal(
            new SiblingEntry("Alice", SiblingRelation.Sister, BiologicalSex.Female, 1988),
            submission.Siblings[0]);
        Assert.Equal(
            new SiblingEntry("Bob", SiblingRelation.HalfBrother, BiologicalSex.Male),
            submission.Siblings[1]);
    }

    [Fact]
    public void Skips_blank_sibling_rows()
    {
        var submission = IntakeSubmissionParser.Parse(Body(
            ("proband_name", "Emma"),
            ("sibling_0_name", "Alice"),
            ("sibling_0_relation", "sister"),
            ("sibling_2_name", "Carol"),
            ("sibling_2_relation", "sister")));

        Assert.Equal(2, submission.Siblings.Count);
        Assert.Equal("Alice", submission.Siblings[0].DisplayName);
        Assert.Equal("Carol", submission.Siblings[1].DisplayName);
    }

    [Fact]
    public void Sibling_without_a_relation_rejects_the_whole_submission()
    {
        Assert.Throws<IntakeValidationException>(
            () => IntakeSubmissionParser.Parse(Body(
                ("proband_name", "Emma"),
                ("sibling_0_name", "Alice"),
                ("sibling_0_relation", ""))));
    }

    private static IReadOnlyDictionary<string, string> Body(params (string Key, string Value)[] entries)
    {
        var dict = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var (key, value) in entries)
        {
            dict[key] = value;
        }
        return dict;
    }
}
