from pathlib import Path

from cascade_letters.letter_writer import (
    DiskLetterSink,
    LetterFile,
    compose_letter,
)
from cascade_letters.relative_selector import LetterTarget


def _target(display_name: str = "Sarah Ward", relationship: str = "Sister") -> LetterTarget:
    return LetterTarget(
        individual_id="b0000000-0000-0000-0000-000000000001",
        display_name=display_name,
        relationship=relationship,
    )


def test_filename_uses_two_digit_index_and_slug() -> None:
    letter = compose_letter(_target(), template_body="Body.", index=3)

    assert letter.filename == "03-sarah-ward.md"


def test_filename_strips_punctuation_and_collapses_whitespace() -> None:
    letter = compose_letter(
        _target(display_name="O'Brien,  Mary Jane!"),
        template_body="Body.",
        index=1,
    )

    assert letter.filename == "01-o-brien-mary-jane.md"


def test_filename_has_no_path_separators_even_for_malicious_names() -> None:
    letter = compose_letter(
        _target(display_name="../../etc/passwd"),
        template_body="Body.",
        index=1,
    )

    assert "/" not in letter.filename
    assert "\\" not in letter.filename
    assert ".." not in letter.filename


def test_filename_falls_back_when_name_slugifies_to_empty() -> None:
    letter = compose_letter(
        _target(display_name="..."),
        template_body="Body.",
        index=1,
    )

    assert letter.filename == "01-relative.md"


def test_content_contains_relative_name_and_relationship_and_body() -> None:
    letter = compose_letter(
        _target(display_name="Sarah Ward", relationship="Sister"),
        template_body="Dear reader, this is the template-generated body.",
        index=1,
    )

    assert "Dear Sarah Ward" in letter.content
    assert "sister" in letter.content  # lower-cased in the relationship sentence
    assert "template-generated body" in letter.content
    assert letter.content.endswith("The Clinical Genetics Team\n")


def test_disk_sink_writes_letter_and_returns_posix_path(tmp_path: Path) -> None:
    sink = DiskLetterSink(tmp_path / "letters")
    letter = LetterFile(filename="01-jane.md", content="Hello.\n")

    reported_path = sink.write(letter)

    written = tmp_path / "letters" / "01-jane.md"
    assert written.read_text(encoding="utf-8") == "Hello.\n"
    assert reported_path == written.as_posix()


def test_disk_sink_creates_parent_directory(tmp_path: Path) -> None:
    sink = DiskLetterSink(tmp_path / "nested" / "letters")

    sink.write(LetterFile(filename="01-a.md", content="x"))

    assert (tmp_path / "nested" / "letters" / "01-a.md").exists()
