from pathlib import Path

from publication_figure_renderer.output_writer import write_svg


def test_writes_svg_text_to_the_requested_path_as_utf8(tmp_path: Path) -> None:
    svg_text = "<svg xmlns=\"http://www.w3.org/2000/svg\"><text>Café</text></svg>"
    target = tmp_path / "fig.svg"

    returned = write_svg(svg_text, target)

    assert returned == target
    assert target.exists()
    assert target.read_text(encoding="utf-8") == svg_text
