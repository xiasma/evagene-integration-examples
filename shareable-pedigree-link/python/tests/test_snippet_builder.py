from shareable_pedigree_link.snippet_builder import SnippetRequest, build_snippet

_REQUEST = SnippetRequest(
    embed_url="https://evagene.net/api/embed/abc?api_key=evg_x",
    label="Family pedigree",
    minted_at="2026-04-20T12:00:00.000Z",
    plaintext_key="evg_x",
    revoke_url="https://evagene.net/account/api-keys",
)


def test_emits_iframe_with_embed_url_as_src() -> None:
    html = build_snippet(_REQUEST)

    assert '<iframe src="https://evagene.net/api/embed/abc?api_key=evg_x"' in html


def test_emits_label_as_iframe_title() -> None:
    html = build_snippet(_REQUEST)

    assert 'title="Family pedigree"' in html


def test_escapes_quotes_in_label() -> None:
    from dataclasses import replace

    html = build_snippet(replace(_REQUEST, label='Mum\'s "pedigree"'))

    assert 'title="Mum&#x27;s &quot;pedigree&quot;"' in html


def test_escapes_html_significant_characters_in_embed_url() -> None:
    from dataclasses import replace

    html = build_snippet(
        replace(
            _REQUEST,
            embed_url="https://evagene.net/api/embed/abc?api_key=evg_x&foo=<bar>",
        ),
    )

    assert "api_key=evg_x&amp;foo=&lt;bar&gt;" in html


def test_note_contains_minted_key_and_revoke_url() -> None:
    html = build_snippet(_REQUEST)

    note = next(line for line in html.splitlines() if line.startswith("Minted API key:"))
    assert "evg_x" in note
    assert "https://evagene.net/account/api-keys" in note


def test_opening_comment_records_minted_at() -> None:
    html = build_snippet(_REQUEST)

    first_line = html.splitlines()[0]
    assert first_line.startswith("<!--")
    assert _REQUEST.minted_at in first_line


def test_separates_snippet_and_note_with_blank_line() -> None:
    lines = build_snippet(_REQUEST).splitlines()
    iframe_index = next(i for i, line in enumerate(lines) if line.startswith("<iframe"))

    assert lines[iframe_index + 1] == ""
