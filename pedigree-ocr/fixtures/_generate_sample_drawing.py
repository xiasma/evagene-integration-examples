"""One-shot fixture builder: renders fixtures/sample-pedigree-drawing.png.

Not shipped as part of the demo -- only used to regenerate the synthetic
"hand-drawn" pedigree fixture. Re-run with::

    python fixtures/_generate_sample_drawing.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font() -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arial.ttf", 18)
    except OSError:
        return ImageFont.load_default()


def _square(draw: ImageDraw.ImageDraw, cx: int, cy: int, *, filled: bool, deceased: bool) -> None:
    half = 28
    box = (cx - half, cy - half, cx + half, cy + half)
    fill = (40, 40, 40) if filled else (255, 255, 255)
    draw.rectangle(box, outline=(20, 20, 20), fill=fill, width=3)
    if deceased:
        draw.line((cx - half - 10, cy + half + 10, cx + half + 10, cy - half - 10),
                  fill=(20, 20, 20), width=3)


def _circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, *, filled: bool, deceased: bool) -> None:
    half = 28
    box = (cx - half, cy - half, cx + half, cy + half)
    fill = (40, 40, 40) if filled else (255, 255, 255)
    draw.ellipse(box, outline=(20, 20, 20), fill=fill, width=3)
    if deceased:
        draw.line((cx - half - 10, cy + half + 10, cx + half + 10, cy - half - 10),
                  fill=(20, 20, 20), width=3)


def _couple_line(draw: ImageDraw.ImageDraw, left: tuple[int, int], right: tuple[int, int]) -> None:
    draw.line((left[0] + 28, left[1], right[0] - 28, right[1]), fill=(20, 20, 20), width=3)


def _descent(draw: ImageDraw.ImageDraw,
             parents_mid: tuple[int, int],
             children: list[tuple[int, int]]) -> None:
    drop = parents_mid[1] + 50
    draw.line((parents_mid[0], parents_mid[1], parents_mid[0], drop), fill=(20, 20, 20), width=3)
    xs = [child[0] for child in children]
    draw.line((min(xs), drop, max(xs), drop), fill=(20, 20, 20), width=3)
    for (cx, cy) in children:
        draw.line((cx, drop, cx, cy - 28), fill=(20, 20, 20), width=3)


def _label(draw: ImageDraw.ImageDraw, cx: int, cy: int, text: str,
           font: ImageFont.ImageFont) -> None:
    draw.text((cx - 30, cy + 38), text, fill=(20, 20, 20), font=font)


def _arrow(draw: ImageDraw.ImageDraw, tip: tuple[int, int]) -> None:
    start = (tip[0] - 40, tip[1] + 40)
    draw.line((start[0], start[1], tip[0] - 10, tip[1] + 10), fill=(200, 20, 20), width=3)
    draw.polygon([
        (tip[0] - 10, tip[1] + 10),
        (tip[0] - 22, tip[1] + 6),
        (tip[0] - 6, tip[1] + 22),
    ], fill=(200, 20, 20))


def build(path: Path) -> None:
    image = Image.new("RGB", (900, 700), (252, 251, 245))
    draw = ImageDraw.Draw(image)
    font = _font()

    gm_mat = (220, 120)
    gf_mat = (360, 120)
    gm_pat = (540, 120)
    gf_pat = (680, 120)
    _circle(draw, *gm_mat, filled=True, deceased=True)
    _label(draw, *gm_mat, "Edith d.59", font)
    _square(draw, *gf_mat, filled=False, deceased=False)
    _label(draw, *gf_mat, "Cecil 92", font)
    _circle(draw, *gm_pat, filled=False, deceased=True)
    _label(draw, *gm_pat, "Margaret", font)
    _square(draw, *gf_pat, filled=True, deceased=False)
    _label(draw, *gf_pat, "Arthur 78", font)
    _couple_line(draw, gm_mat, gf_mat)
    _couple_line(draw, gm_pat, gf_pat)

    mother = (290, 340)
    father = (610, 340)
    _circle(draw, *mother, filled=False, deceased=False)
    _label(draw, *mother, "Grace 68", font)
    _square(draw, *father, filled=False, deceased=False)
    _label(draw, *father, "Henry 70", font)
    _couple_line(draw, mother, father)

    maternal_mid = ((gm_mat[0] + gf_mat[0]) // 2, gm_mat[1])
    paternal_mid = ((gm_pat[0] + gf_pat[0]) // 2, gm_pat[1])
    _descent(draw, maternal_mid, [mother])
    _descent(draw, paternal_mid, [father])

    alice = (390, 560)
    emma = (480, 560)
    _circle(draw, *alice, filled=True, deceased=False)
    _label(draw, *alice, "Alice 42", font)
    _circle(draw, *emma, filled=False, deceased=False)
    _label(draw, *emma, "Emma 40", font)
    couple_mid = ((mother[0] + father[0]) // 2, mother[1])
    _descent(draw, couple_mid, [alice, emma])
    _arrow(draw, (emma[0] - 32, emma[1] - 32))

    draw.text((20, 20), "Family: Carter (synthetic)", fill=(20, 20, 20), font=font)

    image.save(path, format="PNG")


if __name__ == "__main__":
    build(Path(__file__).resolve().parent / "sample-pedigree-drawing.png")
