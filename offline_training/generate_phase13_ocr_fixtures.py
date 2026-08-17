"""Generate the two deterministic OCR fixtures used by Phase 13 live UAT.

These documents are intentionally easy OCR targets.  They test the live wiring
and payload contract, not the robustness of the vision model.  In particular,
money is rendered as uninterrupted digits so a thousands separator cannot be
misread as a decimal point.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from io import BytesIO
from pathlib import Path
from typing import Any, Sequence

from PIL import Image, ImageDraw, ImageFont

FIXTURE_VERSION = "phase13-live-ocr-v1"
IMAGE_SIZE = (1600, 1200)
TITLE_FONT_SIZE = 50
BODY_FONT_SIZE = 38
TITLE_TOP = 60
ROW_TOP = 190
ROW_SPACING = 85
LEFT_MARGIN = 90
OUTPUT_FILENAMES = (
    "customer_order.png",
    "material_weigh_slip.png",
    "manifest.json",
)

FIXTURE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "kind": "customer_order",
        "filename": "customer_order.png",
        "title": "PHIEU DAT HANG KHACH HANG",
        "rows": (
            ("So chung tu", "DH-P13-001"),
            ("Ma Khach hang", "KH-P13-001"),
            ("Khu vuc giao", "Da Lat"),
            ("Han giao", "2026-08-31"),
            ("Ma SKU san pham", "SP-P13-001"),
            ("Ten san pham", "Cao Atiso 100g"),
            ("So luong dat", "10"),
            ("Don gia (truoc thue)", "150000 VND"),
            ("Tong cong thanh toan (da gom VAT 10%)", "1650000 VND"),
        ),
        "truth": {
            "items": [
                {
                    "sku": "SP-P13-001",
                    "name": "Cao Atiso 100g",
                    "qty": 10,
                    "unit_price": 150000,
                }
            ],
            "total": 1650000,
            "farmer": None,
            "region_grown": None,
            "part": None,
            "form": None,
            "gacp_cert": None,
            "doc_no": "DH-P13-001",
            "customer_code": "KH-P13-001",
            "region": "Da Lat",
            "deadline": "2026-08-31",
        },
    },
    {
        "kind": "material_batch",
        "filename": "material_weigh_slip.png",
        "title": "PHIEU CAN NGUYEN LIEU",
        "rows": (
            ("Nong dan / HTX", "HTX Duoc Lieu Lam Dong"),
            ("Vung trong", "Lam Dong"),
            ("Bo phan cay", "la"),
            ("Dang tuoi/kho", "tuoi"),
            ("Chung nhan GACP", "GACP-P13-001"),
            ("Ma SKU san pham", "NVL-008"),
            ("Ten san pham", "La Atiso tuoi"),
            ("So luong dat", "50"),
            ("Don gia (truoc thue)", "12000 VND"),
            ("Tong cong thanh toan (da gom VAT 10%)", "660000 VND"),
        ),
        "truth": {
            "items": [
                {
                    "sku": "NVL-008",
                    "name": "La Atiso tuoi",
                    "qty": 50,
                    "unit_price": 12000,
                }
            ],
            "total": 660000,
            "farmer": "HTX Duoc Lieu Lam Dong",
            "region_grown": "Lam Dong",
            "part": "la",
            "form": "tuoi",
            "gacp_cert": "GACP-P13-001",
            "doc_no": None,
            "customer_code": None,
            "region": None,
            "deadline": None,
        },
    },
)

_FONT_PAIRS = (
    (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
    (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ),
)


def _validate_ttf(path: Path) -> Path:
    """Return a usable TrueType path or raise an actionable error."""
    if path.suffix.casefold() != ".ttf":
        raise ValueError(f"A .ttf font is required, got: {path}")
    if not path.is_file():
        raise FileNotFoundError(f"TrueType font was not found: {path}")
    try:
        probe = ImageFont.truetype(str(path), size=BODY_FONT_SIZE)
        unicode_glyph = probe.getmask("Đ").getbbox()
    except OSError as exc:
        raise ValueError(f"Pillow could not load TrueType font {path}: {exc}") from exc
    if not isinstance(probe, ImageFont.FreeTypeFont) or unicode_glyph is None:
        raise ValueError(f"Font does not provide usable Unicode TrueType glyphs: {path}")
    return path.resolve()


def resolve_font_paths(font: str | Path | None = None) -> tuple[Path, Path]:
    """Resolve regular/title fonts without ever falling back to Pillow's bitmap font."""
    if font is not None:
        explicit = _validate_ttf(Path(font).expanduser())
        return explicit, explicit

    for regular, bold in _FONT_PAIRS:
        if regular.is_file() and bold.is_file():
            return _validate_ttf(regular), _validate_ttf(bold)

    checked = ", ".join(str(path) for pair in _FONT_PAIRS for path in pair)
    raise FileNotFoundError(
        "No usable Unicode TrueType font pair was found. Pass --font with a real "
        f".ttf file. Checked: {checked}"
    )


def _load_fonts(font: str | Path | None) -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
    regular_path, title_path = resolve_font_paths(font)
    return (
        ImageFont.truetype(str(regular_path), size=BODY_FONT_SIZE),
        ImageFont.truetype(str(title_path), size=TITLE_FONT_SIZE),
    )


def _position_for_bbox(
    raw_bbox: tuple[int, int, int, int],
    *,
    desired_left: int,
    desired_top: int,
) -> tuple[int, int]:
    return desired_left - raw_bbox[0], desired_top - raw_bbox[1]


def _layout_document(
    spec: dict[str, Any],
    *,
    body_font: ImageFont.FreeTypeFont,
    title_font: ImageFont.FreeTypeFont,
) -> list[tuple[str, tuple[int, int], ImageFont.FreeTypeFont, tuple[int, int, int, int]]]:
    canvas = Image.new("RGB", IMAGE_SIZE, "white")
    draw = ImageDraw.Draw(canvas)
    layout = []

    title = str(spec["title"])
    raw_title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = raw_title_bbox[2] - raw_title_bbox[0]
    title_xy = _position_for_bbox(
        raw_title_bbox,
        desired_left=(IMAGE_SIZE[0] - title_width) // 2,
        desired_top=TITLE_TOP,
    )
    title_bbox = draw.textbbox(title_xy, title, font=title_font)
    layout.append((title, title_xy, title_font, title_bbox))

    for index, (label, value) in enumerate(spec["rows"]):
        text = f"{label}: {value}"
        raw_bbox = draw.textbbox((0, 0), text, font=body_font)
        xy = _position_for_bbox(
            raw_bbox,
            desired_left=LEFT_MARGIN,
            desired_top=ROW_TOP + index * ROW_SPACING,
        )
        bbox = draw.textbbox(xy, text, font=body_font)
        layout.append((text, xy, body_font, bbox))

    return layout


def _assert_no_clipping(
    spec: dict[str, Any],
    layout: list[
        tuple[str, tuple[int, int], ImageFont.FreeTypeFont, tuple[int, int, int, int]]
    ],
) -> None:
    width, height = IMAGE_SIZE
    for text, _, _, (left, top, right, bottom) in layout:
        if left < 0 or top < 0 or right > width or bottom > height:
            raise ValueError(
                f"Text clipping detected in {spec['filename']!r}: {text!r} has "
                f"bounding box {(left, top, right, bottom)} outside {IMAGE_SIZE}"
            )


def measure_document(
    spec: dict[str, Any],
    *,
    font: str | Path | None = None,
) -> tuple[tuple[int, int, int, int], ...]:
    """Measure configured text using the same layout path as the PNG renderer."""
    body_font, title_font = _load_fonts(font)
    layout = _layout_document(spec, body_font=body_font, title_font=title_font)
    _assert_no_clipping(spec, layout)
    return tuple(entry[3] for entry in layout)


def _render_png(spec: dict[str, Any], *, font: str | Path | None) -> bytes:
    body_font, title_font = _load_fonts(font)
    layout = _layout_document(spec, body_font=body_font, title_font=title_font)
    _assert_no_clipping(spec, layout)

    image = Image.new("RGB", IMAGE_SIZE, "white")
    draw = ImageDraw.Draw(image)
    for text, xy, selected_font, _ in layout:
        draw.text(xy, text, font=selected_font, fill="black")

    output = BytesIO()
    image.save(output, format="PNG", optimize=False, compress_level=9)
    return output.getvalue()


def generate_fixtures(
    output_dir: str | Path,
    *,
    force: bool = False,
    font: str | Path | None = None,
) -> Path:
    """Write both fixture PNGs plus their deterministic manifest."""
    root = Path(output_dir)
    targets = {filename: root / filename for filename in OUTPUT_FILENAMES}
    existing = [path for path in targets.values() if path.exists()]
    if existing and not force:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"Refusing to overwrite existing Phase 13 fixture target(s): {names}. "
            "Pass --force to replace all three targets."
        )

    regular_path, title_path = resolve_font_paths(font)
    explicit_font = regular_path if font is not None else None
    rendered = {
        spec["filename"]: _render_png(spec, font=explicit_font)
        for spec in FIXTURE_SPECS
    }
    specs_by_kind = {spec["kind"]: spec for spec in FIXTURE_SPECS}
    manifest = {
        "fixture_version": FIXTURE_VERSION,
        "image": {
            "width": IMAGE_SIZE[0],
            "height": IMAGE_SIZE[1],
            "mode": "RGB",
            "title_font_px": TITLE_FONT_SIZE,
            "body_font_px": BODY_FONT_SIZE,
        },
        "font": {
            "body_file": regular_path.name,
            "title_file": (regular_path if explicit_font is not None else title_path).name,
        },
        "webhook_contract": {
            "auth_header": "x-anser-token",
            "multipart_field": "data",
            "customer_order": {"endpoint": "/webhook/customer-order-ocr"},
            "material_batch": {"endpoint": "/webhook/material-intake"},
        },
        "fixtures": {
            kind: {
                "filename": spec["filename"],
                "sha256": hashlib.sha256(rendered[spec["filename"]]).hexdigest(),
                "truth": spec["truth"],
            }
            for kind, spec in specs_by_kind.items()
        },
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    root.mkdir(parents=True, exist_ok=True)
    for filename, payload in rendered.items():
        targets[filename].write_bytes(payload)
    targets["manifest.json"].write_bytes(manifest_bytes)
    return targets["manifest.json"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate deterministic customer-order and material OCR fixtures"
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--font",
        type=Path,
        help="Explicit Unicode .ttf font (otherwise Arial/DejaVu is resolved)",
    )
    args = parser.parse_args(argv)
    manifest_path = generate_fixtures(
        args.output_dir,
        force=args.force,
        font=args.font,
    )
    print(f"Generated Phase 13 OCR fixtures: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
