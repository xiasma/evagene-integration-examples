namespace FamilyIntake;

/// <summary>
/// Static HTML views. Keeping them in a typed module rather than a
/// template engine means the demo ships with zero extra runtime deps
/// and is still easy to read.
/// </summary>
public static class Views
{
    private const string Style =
        ":root { --gap: 0.75rem; --accent: #0a58ca; --fg: #1f2937; }\n" +
        "* { box-sizing: border-box; }\n" +
        "body { font: 1rem/1.5 system-ui, sans-serif; color: var(--fg); max-width: 44rem; margin: 2rem auto; padding: 0 1rem; }\n" +
        "h1 { margin-top: 0; }\n" +
        "fieldset { margin: 0 0 1.25rem; border: 1px solid #d1d5db; border-radius: 6px; padding: 1rem 1.25rem; }\n" +
        "legend { font-weight: 600; padding: 0 0.5rem; }\n" +
        "label { display: block; margin-bottom: var(--gap); }\n" +
        "label span { display: block; font-size: 0.875rem; color: #4b5563; margin-bottom: 2px; }\n" +
        "input, select { width: 100%; padding: 0.5rem 0.625rem; font: inherit; border: 1px solid #d1d5db; border-radius: 4px; }\n" +
        ".row { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: var(--gap); align-items: end; }\n" +
        ".row label { margin-bottom: 0; }\n" +
        "button { background: var(--accent); color: white; border: 0; padding: 0.75rem 1.25rem; border-radius: 4px; font: inherit; cursor: pointer; }\n" +
        "button:hover { filter: brightness(1.1); }\n" +
        ".muted { color: #6b7280; font-size: 0.875rem; }\n" +
        ".success, .error { padding: 1rem 1.25rem; border-radius: 6px; margin-bottom: 1.5rem; }\n" +
        ".success { background: #ecfdf5; border: 1px solid #10b981; }\n" +
        ".error { background: #fef2f2; border: 1px solid #ef4444; }\n" +
        "a { color: var(--accent); }";

    public static string FormPage()
    {
        var body =
            "<h1>Family-history intake</h1>\n" +
            "<p class=\"muted\">Fill in the family members you know about. Everything except the patient's name is optional; blanks are skipped.</p>\n" +
            "<form method=\"post\" action=\"/submit\">\n" +
            "  <fieldset>\n" +
            "    <legend>Patient</legend>\n" +
            "    <label><span>Name (required)</span><input name=\"proband_name\" required></label>\n" +
            "    <div class=\"row\">\n" +
            "      <label><span>Biological sex</span>\n" +
            "        <select name=\"proband_sex\">\n" +
            "          <option value=\"unknown\">Prefer not to say</option>\n" +
            "          <option value=\"female\">Female</option>\n" +
            "          <option value=\"male\">Male</option>\n" +
            "        </select>\n" +
            "      </label>\n" +
            "      <label><span>Year of birth</span><input name=\"proband_year\" type=\"number\" min=\"1850\" max=\"2030\" inputmode=\"numeric\"></label>\n" +
            "    </div>\n" +
            "  </fieldset>\n" +
            "  <fieldset>\n" +
            "    <legend>Parents</legend>\n" +
            PersonRow("mother", "Mother") + "\n" +
            PersonRow("father", "Father") + "\n" +
            "  </fieldset>\n" +
            "  <fieldset>\n" +
            "    <legend>Maternal grandparents</legend>\n" +
            PersonRow("maternal_grandmother", "Maternal grandmother") + "\n" +
            PersonRow("maternal_grandfather", "Maternal grandfather") + "\n" +
            "  </fieldset>\n" +
            "  <fieldset>\n" +
            "    <legend>Paternal grandparents</legend>\n" +
            PersonRow("paternal_grandmother", "Paternal grandmother") + "\n" +
            PersonRow("paternal_grandfather", "Paternal grandfather") + "\n" +
            "  </fieldset>\n" +
            "  <fieldset>\n" +
            "    <legend>Siblings (optional, up to 4)</legend>\n" +
            SiblingRow(0) + "\n" +
            SiblingRow(1) + "\n" +
            SiblingRow(2) + "\n" +
            SiblingRow(3) + "\n" +
            "  </fieldset>\n" +
            "  <button type=\"submit\">Create pedigree</button>\n" +
            "</form>";
        return Wrap("Family-history intake", body);
    }

    public static string SuccessPage(string pedigreeId, string pedigreeUrl, int relativesAdded)
    {
        var body =
            "<div class=\"success\">\n" +
            "  <h1>Pedigree created</h1>\n" +
            $"  <p>Added the proband and <strong>{relativesAdded}</strong> relative(s).</p>\n" +
            $"  <p>Pedigree ID: <code>{EscapeHtml(pedigreeId)}</code></p>\n" +
            $"  <p><a href=\"{EscapeHtml(pedigreeUrl)}\">Open in Evagene &rarr;</a></p>\n" +
            "</div>\n" +
            "<p><a href=\"/\">Capture another family</a></p>";
        return Wrap("Pedigree created", body);
    }

    public static string ErrorPage(string message, string? partialPedigreeId = null)
    {
        var partial = partialPedigreeId is null
            ? string.Empty
            : $"<p class=\"muted\">A pedigree with ID <code>{EscapeHtml(partialPedigreeId)}</code> was partially created; open it in Evagene to clean up or resume.</p>";
        var body =
            "<div class=\"error\">\n" +
            "  <h1>Something went wrong</h1>\n" +
            $"  <p>{EscapeHtml(message)}</p>\n" +
            $"  {partial}\n" +
            "</div>\n" +
            "<p><a href=\"/\">Try again</a></p>";
        return Wrap("Something went wrong", body);
    }

    public static string EscapeHtml(string raw)
    {
        return raw
            .Replace("&", "&amp;", StringComparison.Ordinal)
            .Replace("<", "&lt;", StringComparison.Ordinal)
            .Replace(">", "&gt;", StringComparison.Ordinal)
            .Replace("\"", "&quot;", StringComparison.Ordinal)
            .Replace("'", "&#39;", StringComparison.Ordinal);
    }

    private static string PersonRow(string fieldPrefix, string label)
    {
        return
            "    <div class=\"row\">\n" +
            $"      <label><span>{EscapeHtml(label)} name</span><input name=\"{fieldPrefix}_name\"></label>\n" +
            $"      <label><span>Year of birth</span><input name=\"{fieldPrefix}_year\" type=\"number\" min=\"1850\" max=\"2030\" inputmode=\"numeric\"></label>\n" +
            "      <span></span>\n" +
            "    </div>";
    }

    private static string SiblingRow(int index)
    {
        return
            "    <div class=\"row\">\n" +
            $"      <label><span>Name</span><input name=\"sibling_{index}_name\"></label>\n" +
            "      <label><span>Relation</span>\n" +
            $"        <select name=\"sibling_{index}_relation\">\n" +
            "          <option value=\"\">&mdash;</option>\n" +
            "          <option value=\"sister\">Sister</option>\n" +
            "          <option value=\"brother\">Brother</option>\n" +
            "          <option value=\"half_sister\">Half sister</option>\n" +
            "          <option value=\"half_brother\">Half brother</option>\n" +
            "        </select>\n" +
            "      </label>\n" +
            $"      <label><span>Year of birth</span><input name=\"sibling_{index}_year\" type=\"number\" min=\"1850\" max=\"2030\" inputmode=\"numeric\"></label>\n" +
            "    </div>";
    }

    private static string Wrap(string title, string body)
    {
        return
            "<!DOCTYPE html>\n" +
            "<html lang=\"en\">\n" +
            "<head>\n" +
            "  <meta charset=\"utf-8\">\n" +
            $"  <title>{EscapeHtml(title)}</title>\n" +
            "  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n" +
            $"  <style>{Style}</style>\n" +
            "</head>\n" +
            "<body>\n" +
            "  <main>\n" +
            $"    {body}\n" +
            "  </main>\n" +
            "</body>\n" +
            "</html>";
    }
}
