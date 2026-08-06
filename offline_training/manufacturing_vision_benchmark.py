"""Synthetic manufacturing-document benchmark for the live VisionAgent.

The module deliberately separates cheap, deterministic corpus generation/scoring
from GPU inference.  Colab callers provide the already-loaded ``VisionAgent`` and
the runner checkpoints one JSON record per image, so interrupted 100-image runs
resume instead of starting over.

This is a controlled synthetic robustness benchmark, not a replacement for a
labeled set of real scans/photos from production.
"""

from __future__ import annotations

import json
import math
import random
import re
import statistics
import sys
import time
import unicodedata
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# Support both ``python -m offline_training...`` and direct script execution.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.mcp_server import MCPServer
from src.core.schemas import ManufacturingInvoicePayload

if TYPE_CHECKING:
    from src.agents.vision import VisionAgent

BENCHMARK_VERSION = "manufacturing-synthetic-v1"
DEFAULT_SEED = 20260806

CUSTOMER_FIELDS = ("doc_no", "customer_code", "region", "deadline")
MATERIAL_FIELDS = ("farmer", "region_grown", "part", "form", "gacp_cert")
MANUFACTURING_METADATA_FIELDS = MATERIAL_FIELDS + CUSTOMER_FIELDS

PRODUCTS = (
    ("SP-001", "Cao Atiso 100g", 150_000),
    ("SP-002", "Tra Atiso Tui Loc 20g", 45_000),
    ("SP-003", "Tra Duong Quyen 100g", 72_000),
    ("SP-004", "Cao Mem Atiso 200g", 238_000),
    ("SP-005", "Tra Thao Moc An Giac", 89_000),
    ("SP-006", "Vien Nang Atiso 60 Vien", 195_000),
)

MATERIALS = (
    ("NL-001", "La Atiso Tuoi", 12_000),
    ("NL-002", "Re Duong Quyen Kho", 28_000),
    ("NL-003", "Hoa Cuc Chi Kho", 95_000),
    ("NL-004", "Cam Thao Lat", 82_000),
    ("NL-005", "La Sen Kho", 44_000),
    ("NL-006", "Tra Xanh Nguyen Lieu", 67_000),
)

CUSTOMERS = (
    "Cong ty Duoc An Nhien",
    "Nha thuoc Minh Tam",
    "Cong ty Thao Moc Viet",
    "Dai ly Bao Chau",
    "Cua hang Song Xanh",
)

REGIONS = ("Ha Noi", "Da Lat", "Hue", "Da Nang", "Can Tho", "Hai Phong")
FARMERS = (
    "HTX Rau Sach Da Lat",
    "Nong trai Hoa Son",
    "HTX Duoc Lieu Lam Dong",
    "Nong ho Nguyen Van An",
    "Trang trai Xanh Cao Nguyen",
)
GROWING_REGIONS = ("Lam Dong", "Gia Lai", "Kon Tum", "Son La", "Lao Cai")
PLANT_PARTS = ("la", "re", "hoa", "than")
MATERIAL_FORMS = ("tuoi", "kho", "thai lat")

QUALITY_LEVELS = {
    "clean": {"rotation": 0.0, "blur": 0.0, "contrast": 1.0, "noise": 0.0, "jpeg": 95},
    "mild": {"rotation": 0.7, "blur": 0.2, "contrast": 0.92, "noise": 0.02, "jpeg": 86},
    "medium": {"rotation": 1.4, "blur": 0.45, "contrast": 0.82, "noise": 0.045, "jpeg": 72},
    "hard": {"rotation": 2.2, "blur": 0.75, "contrast": 0.70, "noise": 0.075, "jpeg": 58},
}


def _ascii_fold(value: str) -> str:
    value = value.replace("Đ", "D").replace("đ", "d")
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    folded = _ascii_fold(str(value)).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", folded))


def _present(value: Any) -> bool:
    return value is not None and not (isinstance(value, str) and not value.strip())


def _numeric_equal(actual: Any, expected: Any) -> bool:
    try:
        return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=0.01)
    except (TypeError, ValueError):
        return False


def _text_equal(actual: Any, expected: Any) -> bool:
    return _normalize_text(actual) == _normalize_text(expected)


def _font_path(bold: bool = False) -> Path | None:
    candidates = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        if bold
        else Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf") if bold else Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf") if bold else Path("C:/Windows/Fonts/calibri.ttf"),
    )
    return next((path for path in candidates if path.is_file()), None)


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    path = _font_path(bold)
    return ImageFont.truetype(str(path), size=size) if path else ImageFont.load_default()


def _draw_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    *,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int] = (20, 20, 20),
) -> None:
    try:
        draw.text(xy, text, font=font, fill=fill)
    except UnicodeEncodeError:
        draw.text(xy, _ascii_fold(text), font=font, fill=fill)


def _money(value: int, separator: str) -> str:
    rendered = f"{value:,}"
    if separator == ".":
        rendered = rendered.replace(",", ".")
    elif separator == " ":
        rendered = rendered.replace(",", " ")
    return rendered


def _customer_truth(rng: random.Random, index: int) -> dict[str, Any]:
    item_count = 2 if index % 5 == 0 else 1
    selected = rng.sample(PRODUCTS, k=item_count)
    items = []
    for sku, name, price in selected:
        qty = rng.randint(2, 30)
        items.append({"sku": sku, "name": name, "qty": qty, "unit_price": price})
    base = sum(item["qty"] * item["unit_price"] for item in items)
    deadline = date(2026, 8, 10) + timedelta(days=index % 45)
    return {
        "items": items,
        "total": int(round(base * 1.10)),
        "farmer": None,
        "region_grown": None,
        "part": None,
        "form": None,
        "gacp_cert": None,
        "doc_no": f"DH-2026{8 + (index % 4):02d}-{index + 1:03d}",
        "customer_code": f"KH-{100 + index:04d}",
        "region": rng.choice(REGIONS),
        "deadline": deadline.isoformat(),
        "customer_name": rng.choice(CUSTOMERS),
    }


def _material_truth(rng: random.Random, index: int) -> dict[str, Any]:
    item_count = 2 if index % 7 == 0 else 1
    selected = rng.sample(MATERIALS, k=item_count)
    items = []
    for sku, name, price in selected:
        qty = rng.randint(10, 120)
        items.append({"sku": sku, "name": name, "qty": qty, "unit_price": price})
    base = sum(item["qty"] * item["unit_price"] for item in items)
    return {
        "items": items,
        "total": int(round(base * 1.10)),
        "farmer": rng.choice(FARMERS),
        "region_grown": rng.choice(GROWING_REGIONS),
        "part": rng.choice(PLANT_PARTS),
        "form": rng.choice(MATERIAL_FORMS),
        "gacp_cert": f"GACP-2026-{index + 1:03d}",
        "doc_no": None,
        "customer_code": None,
        "region": None,
        "deadline": None,
    }


def _labels(kind: str, accented: bool) -> dict[str, str]:
    if kind == "customer_order":
        labels = {
            "title": "PHIẾU ĐẶT HÀNG KHÁCH HÀNG",
            "doc_no": "Số chứng từ",
            "customer_code": "Mã khách hàng",
            "customer_name": "Tên khách hàng",
            "region": "Khu vực giao",
            "deadline": "Hạn giao",
            "sku": "Mã SKU sản phẩm",
            "name": "Tên sản phẩm",
            "qty": "Số lượng đặt",
            "unit_price": "Đơn giá trước thuế",
            "total": "Tổng cộng thanh toán (VAT 10%)",
        }
    else:
        labels = {
            "title": "PHIẾU NHẬP NGUYÊN LIỆU",
            "farmer": "Nông dân / HTX",
            "region_grown": "Vùng trồng",
            "part": "Bộ phận cây",
            "form": "Dạng tươi/khô",
            "gacp_cert": "Chứng nhận GACP",
            "sku": "Mã nguyên liệu",
            "name": "Tên nguyên liệu",
            "qty": "Số lượng nhập",
            "unit_price": "Đơn giá trước thuế",
            "total": "Tổng thanh toán (VAT 10%)",
        }
    return labels if accented else {key: _ascii_fold(value) for key, value in labels.items()}


def _render_case(case: dict[str, Any], destination: Path) -> None:
    truth = case["truth"]
    labels = _labels(case["kind"], case["accented_labels"])
    rng = random.Random(case["render_seed"])
    width, height = case["canvas"]
    image = Image.new("RGB", (width, height), (250, 249, 245))
    draw = ImageDraw.Draw(image)
    title_font = _font(case["font_size"] + 10, bold=True)
    label_font = _font(case["font_size"], bold=True)
    value_font = _font(case["font_size"])
    small_font = _font(max(18, case["font_size"] - 3))
    margin = 58

    draw.rectangle((24, 24, width - 24, height - 24), outline=(45, 45, 45), width=3)
    title_box = draw.textbbox((0, 0), labels["title"], font=title_font)
    title_width = title_box[2] - title_box[0]
    _draw_text(
        draw,
        ((width - title_width) // 2, 48),
        labels["title"],
        font=title_font,
    )
    draw.line((margin, 105, width - margin, 105), fill=(70, 70, 70), width=2)

    if case["kind"] == "customer_order":
        metadata_rows = [
            (labels["doc_no"], truth["doc_no"]),
            (labels["customer_code"], truth["customer_code"]),
            (labels["customer_name"], truth["customer_name"]),
            (labels["region"], truth["region"]),
            (labels["deadline"], truth["deadline"]),
        ]
    else:
        metadata_rows = [
            (labels["farmer"], truth["farmer"]),
            (labels["region_grown"], truth["region_grown"]),
            (labels["part"], truth["part"]),
            (labels["form"], truth["form"]),
            (labels["gacp_cert"], truth["gacp_cert"]),
        ]

    layout = case["layout"]
    if layout == "two_column":
        for row_index, (label, value) in enumerate(metadata_rows):
            column = row_index % 2
            row = row_index // 2
            x = margin + column * 680
            y = 130 + row * 65
            _draw_text(draw, (x, y), f"{label}:", font=label_font)
            _draw_text(draw, (x, y + 27), str(value), font=value_font)
        table_y = 350
    else:
        for row_index, (label, value) in enumerate(metadata_rows):
            y = 132 + row_index * 49
            if layout == "boxed":
                draw.rounded_rectangle(
                    (margin - 8, y - 5, width - margin + 8, y + 37),
                    radius=7,
                    outline=(125, 125, 125),
                    width=1,
                )
            _draw_text(draw, (margin, y), f"{label}:", font=label_font)
            _draw_text(draw, (365, y), str(value), font=value_font)
        table_y = 410

    columns = (margin, 145, 300, 820, 970)
    table_headers = (
        "STT",
        "SKU",
        "Tên sản phẩm" if case["accented_labels"] else "Ten san pham",
        "SL",
        "Đơn giá (VND)" if case["accented_labels"] else "Don gia (VND)",
    )
    draw.rectangle((margin - 10, table_y - 10, width - margin + 10, table_y + 42), fill=(228, 232, 235))
    for x, header in zip(columns, table_headers):
        _draw_text(draw, (x, table_y), header, font=small_font)

    row_height = 68
    for item_index, item in enumerate(truth["items"]):
        y = table_y + 55 + item_index * row_height
        values = (
            str(item_index + 1),
            item["sku"],
            item["name"],
            str(item["qty"]),
            _money(item["unit_price"], case["money_separator"]),
        )
        for x, value in zip(columns, values):
            _draw_text(draw, (x, y), value, font=value_font)
        draw.line((margin - 10, y + 42, width - margin + 10, y + 42), fill=(185, 185, 185), width=1)

    total_y = table_y + 75 + len(truth["items"]) * row_height
    total_label = f"{labels['total']}:"
    total_value = f"{_money(truth['total'], case['money_separator'])} VND"
    label_box = draw.textbbox((0, 0), total_label, font=label_font)
    value_box = draw.textbbox((0, 0), total_value, font=label_font)
    label_width = label_box[2] - label_box[0]
    value_width = value_box[2] - value_box[0]
    value_x = width - margin - value_width
    label_x = max(margin, value_x - label_width - 28)
    _draw_text(draw, (label_x, total_y), total_label, font=label_font)
    _draw_text(draw, (value_x, total_y), total_value, font=label_font)
    footer = f"Mau thu nghiem {case['case_id']}  |  Khong co gia tri giao dich"
    _draw_text(draw, (margin, height - 68), footer, font=small_font, fill=(100, 100, 100))

    quality = QUALITY_LEVELS[case["quality"]]
    rotation = rng.uniform(-quality["rotation"], quality["rotation"])
    if rotation:
        image = image.rotate(rotation, resample=Image.Resampling.BICUBIC, fillcolor=(250, 249, 245))
    if quality["contrast"] != 1.0:
        image = ImageEnhance.Contrast(image).enhance(quality["contrast"])
    if quality["blur"]:
        image = image.filter(ImageFilter.GaussianBlur(radius=quality["blur"]))
    if quality["noise"]:
        noise = Image.effect_noise(image.size, 22).convert("RGB")
        image = Image.blend(image, noise, quality["noise"])
    if case["quality"] in {"medium", "hard"}:
        scale = 0.86 if case["quality"] == "medium" else 0.72
        reduced = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            Image.Resampling.BILINEAR,
        )
        image = reduced.resize((width, height), Image.Resampling.BILINEAR)

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() == ".jpg":
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=quality["jpeg"], optimize=True)
        destination.write_bytes(buffer.getvalue())
    else:
        image.save(destination, format="PNG", optimize=True)


def generate_corpus(
    output_dir: str | Path,
    *,
    count: int = 100,
    seed: int = DEFAULT_SEED,
    force: bool = False,
) -> Path:
    """Generate a deterministic, balanced corpus and return its manifest path."""
    if count <= 0 or count % 2:
        raise ValueError("count must be a positive even number so both document families are balanced")

    root = Path(output_dir)
    image_dir = root / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = root / "manifest.json"
    if manifest_path.is_file() and not force:
        try:
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = {}
        reusable = (
            existing.get("benchmark_version") == BENCHMARK_VERSION
            and existing.get("seed") == seed
            and existing.get("count") == count
            and len(existing.get("cases", [])) == count
            and all((root / case["image"]).is_file() for case in existing.get("cases", []))
        )
        if reusable:
            return manifest_path

    rng = random.Random(seed)
    quality_names = tuple(QUALITY_LEVELS)
    layouts = ("standard", "two_column", "boxed")
    cases = []

    for index in range(count):
        kind = "customer_order" if index % 2 == 0 else "material_batch"
        family_index = index // 2
        quality = quality_names[family_index % len(quality_names)]
        extension = ".png" if quality in {"clean", "mild"} else ".jpg"
        case_id = f"{kind[:2]}-{index + 1:03d}"
        truth = (
            _customer_truth(rng, family_index)
            if kind == "customer_order"
            else _material_truth(rng, family_index)
        )
        case = {
            "case_id": case_id,
            "kind": kind,
            "quality": quality,
            "layout": layouts[family_index % len(layouts)],
            "accented_labels": family_index % 2 == 0,
            "font_size": 25 + family_index % 4,
            "money_separator": (",", ".", " ")[family_index % 3],
            "canvas": [1400, 1050],
            "render_seed": seed + index * 997,
            "image": f"images/{case_id}{extension}",
            "truth": truth,
        }
        _render_case(case, root / case["image"])
        cases.append(case)

    manifest = {
        "benchmark_version": BENCHMARK_VERSION,
        "scope_warning": "Synthetic controlled documents do not replace labeled real scans/photos.",
        "seed": seed,
        "count": count,
        "distribution": {
            "customer_order": count // 2,
            "material_batch": count // 2,
            "quality_levels": list(quality_names),
            "layouts": list(layouts),
        },
        "cases": cases,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest_path


def endpoint_like_result(extracted: dict[str, Any]) -> dict[str, Any]:
    """Apply the production schema, total validation, and review signal locally."""
    if "error" in extracted:
        return {
            "success": False,
            "error": extracted["error"],
            "raw": extracted.get("raw", ""),
        }
    try:
        invoice = ManufacturingInvoicePayload(**extracted)
    except Exception as exc:
        return {"success": False, "error": f"schema_invalid: {exc}", "raw_json": extracted}

    mcp_items = [
        {"name": item.name, "price": item.unit_price, "qty": item.qty}
        for item in invoice.items
    ]
    validation = MCPServer.validate_invoice_total(mcp_items, invoice.total)
    metadata_present = any(
        getattr(invoice, field) is not None
        for field in MANUFACTURING_METADATA_FIELDS
    )
    needs_manual_review = (
        (not validation["is_valid"])
        or (len(invoice.items) == 0)
        or (not metadata_present)
    )
    return {
        "success": True,
        "invoice": invoice.model_dump(),
        "validation": validation,
        "needs_manual_review": needs_manual_review,
    }


def evaluate_case(case: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Score a response against one manifest case without fixture-specific literals."""
    expected = case["truth"]
    actual = response.get("invoice") or {}
    expected_items = expected["items"]
    actual_items = actual.get("items") or []
    item_count_ok = len(actual_items) == len(expected_items)

    item_scores = {"sku": [], "name": [], "qty": [], "unit_price": []}
    for index, expected_item in enumerate(expected_items):
        actual_item = actual_items[index] if index < len(actual_items) else {}
        item_scores["sku"].append(_text_equal(actual_item.get("sku"), expected_item["sku"]))
        item_scores["name"].append(_text_equal(actual_item.get("name"), expected_item["name"]))
        item_scores["qty"].append(_numeric_equal(actual_item.get("qty"), expected_item["qty"]))
        item_scores["unit_price"].append(
            _numeric_equal(actual_item.get("unit_price"), expected_item["unit_price"])
        )

    relevant_fields = CUSTOMER_FIELDS if case["kind"] == "customer_order" else MATERIAL_FIELDS
    irrelevant_fields = MATERIAL_FIELDS if case["kind"] == "customer_order" else CUSTOMER_FIELDS
    field_scores = {
        "schema_success": response.get("success") is True,
        "items.count": item_count_ok,
        "items.sku": item_count_ok and all(item_scores["sku"]),
        "items.name": item_count_ok and all(item_scores["name"]),
        "items.qty": item_count_ok and all(item_scores["qty"]),
        "items.unit_price": item_count_ok and all(item_scores["unit_price"]),
        "total": _numeric_equal(actual.get("total"), expected["total"]),
        "irrelevant_metadata_null": all(not _present(actual.get(field)) for field in irrelevant_fields),
    }
    for field in relevant_fields:
        field_scores[field] = _text_equal(actual.get(field), expected[field])

    document_complete = all(field_scores.values())
    validation_valid = (response.get("validation") or {}).get("is_valid") is True
    actual_review = response.get("needs_manual_review")
    review_should_be_required = not document_complete
    review_correct = actual_review is review_should_be_required
    return {
        "field_scores": field_scores,
        "document_complete": document_complete,
        "validation_valid": validation_valid,
        "needs_manual_review": actual_review,
        "review_should_be_required": review_should_be_required,
        "review_correct": review_correct,
        "review_false_negative": review_should_be_required and actual_review is False,
    }


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return round(ordered[index], 3)


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {
            "cases": 0,
            "document_accuracy": 0.0,
            "schema_success_rate": 0.0,
            "validation_valid_rate": 0.0,
            "review_false_negative_rate": 0.0,
            "latency_s": {"mean": 0.0, "p50": 0.0, "p95": 0.0},
            "field_accuracy": {},
        }
    field_totals: dict[str, list[bool]] = {}
    for row in rows:
        for field, passed in row["evaluation"]["field_scores"].items():
            field_totals.setdefault(field, []).append(bool(passed))
    latencies = [float(row["elapsed_s"]) for row in rows]
    return {
        "cases": len(rows),
        "document_accuracy": round(
            sum(row["evaluation"]["document_complete"] for row in rows) / len(rows), 4
        ),
        "schema_success_rate": round(
            sum(row["evaluation"]["field_scores"]["schema_success"] for row in rows)
            / len(rows),
            4,
        ),
        "validation_valid_rate": round(
            sum(row["evaluation"]["validation_valid"] for row in rows) / len(rows), 4
        ),
        "review_false_negative_rate": round(
            sum(row["evaluation"]["review_false_negative"] for row in rows) / len(rows), 4
        ),
        "latency_s": {
            "mean": round(statistics.fmean(latencies), 3),
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
        },
        "field_accuracy": {
            field: round(sum(values) / len(values), 4)
            for field, values in sorted(field_totals.items())
        },
    }


def summarize_results(
    rows: list[dict[str, Any]],
    *,
    expected_count: int,
    run_name: str,
) -> dict[str, Any]:
    complete_rows = [row for row in rows if not row.get("error")]
    by_kind = {
        kind: _aggregate([row for row in complete_rows if row["kind"] == kind])
        for kind in ("customer_order", "material_batch")
    }
    by_quality = {
        quality: _aggregate([row for row in complete_rows if row["quality"] == quality])
        for quality in QUALITY_LEVELS
    }
    failures = [
        {
            "case_id": row["case_id"],
            "kind": row["kind"],
            "quality": row["quality"],
            "failed_fields": [
                field
                for field, passed in row["evaluation"]["field_scores"].items()
                if not passed
            ],
            "needs_manual_review": row["evaluation"]["needs_manual_review"],
        }
        for row in complete_rows
        if not row["evaluation"]["document_complete"]
    ]
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "run_name": run_name,
        "expected_cases": expected_count,
        "completed_cases": len(rows),
        "inference_errors": sum(bool(row.get("error")) for row in rows),
        "is_complete": len(rows) == expected_count,
        "scope_warning": "Synthetic controlled documents do not replace labeled real scans/photos.",
        "overall": _aggregate(complete_rows),
        "by_kind": by_kind,
        "by_quality": by_quality,
        "failure_count": len(failures),
        "failures": failures,
    }


def _load_jsonl(path: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        case_id = record.get("case_id")
        if case_id:
            records[str(case_id)] = record
    return records


async def run_benchmark(
    manifest_path: str | Path,
    vision_agent: VisionAgent,
    *,
    run_name: str,
    limit: int | None = None,
    progress_every: int = 1,
) -> dict[str, Any]:
    """Run/resume sequential inference and persist each completed case immediately."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest["cases"][:limit] if limit is not None else manifest["cases"]
    safe_run_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", run_name).strip("-")
    if not safe_run_name:
        raise ValueError("run_name must contain at least one safe character")

    result_dir = manifest_path.parent / "results"
    result_dir.mkdir(parents=True, exist_ok=True)
    results_path = result_dir / f"{safe_run_name}.jsonl"
    summary_path = result_dir / f"{safe_run_name}.summary.json"
    records = _load_jsonl(results_path)
    selected_ids = {case["case_id"] for case in cases}
    records = {case_id: row for case_id, row in records.items() if case_id in selected_ids}
    started = time.perf_counter()
    newly_completed = 0

    with results_path.open("a", encoding="utf-8", buffering=1) as stream:
        for case in cases:
            if case["case_id"] in records:
                continue
            image_path = manifest_path.parent / case["image"]
            engine = getattr(vision_agent, "engine", None)
            raw_outputs = getattr(engine, "raw_outputs", None)
            if isinstance(raw_outputs, list):
                raw_outputs.clear()
            case_started = time.perf_counter()
            try:
                extracted = await vision_agent.extract_manufacturing_invoice(str(image_path))
                response = endpoint_like_result(extracted)
                evaluation = evaluate_case(case, response)
                error = None
            except Exception as exc:
                extracted = {}
                response = {"success": False, "error": str(exc)}
                evaluation = {
                    "field_scores": {"schema_success": False},
                    "document_complete": False,
                    "validation_valid": False,
                    "needs_manual_review": None,
                    "review_should_be_required": True,
                    "review_correct": False,
                    "review_false_negative": False,
                }
                error = f"{type(exc).__name__}: {exc}"
            elapsed_s = round(time.perf_counter() - case_started, 3)
            record = {
                "benchmark_version": BENCHMARK_VERSION,
                "case_id": case["case_id"],
                "kind": case["kind"],
                "quality": case["quality"],
                "layout": case["layout"],
                "image": case["image"],
                "elapsed_s": elapsed_s,
                "truth": case["truth"],
                "extracted": extracted,
                "response": response,
                "evaluation": evaluation,
                "raw_model_outputs": list(raw_outputs) if isinstance(raw_outputs, list) else [],
                "error": error,
            }
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            stream.flush()
            records[case["case_id"]] = record
            newly_completed += 1

            completed = len(records)
            remaining = len(cases) - completed
            recent_elapsed = time.perf_counter() - started
            eta_minutes = (
                (recent_elapsed / newly_completed) * remaining / 60
                if newly_completed and remaining
                else 0.0
            )
            if completed % max(1, progress_every) == 0 or completed == len(cases):
                verdict = "PASS" if evaluation["document_complete"] else "FAIL"
                print(
                    f"[{completed:03d}/{len(cases):03d}] {case['case_id']} "
                    f"{case['quality']} {verdict} {elapsed_s:.2f}s | ETA {eta_minutes:.1f} min"
                )

    ordered_rows = [records[case["case_id"]] for case in cases if case["case_id"] in records]
    summary = summarize_results(
        ordered_rows,
        expected_count=len(cases),
        run_name=safe_run_name,
    )
    summary["manifest_path"] = str(manifest_path)
    summary["results_path"] = str(results_path)
    summary["summary_path"] = str(summary_path)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def print_summary(summary: dict[str, Any]) -> None:
    overall = summary["overall"]
    print("\n=== MANUFACTURING VISION BENCHMARK ===")
    print(f"Completed: {summary['completed_cases']}/{summary['expected_cases']}")
    print(f"Document accuracy: {overall['document_accuracy']:.1%}")
    print(f"Schema success: {overall['schema_success_rate']:.1%}")
    print(f"Valid totals: {overall['validation_valid_rate']:.1%}")
    print(f"Review false negatives: {overall['review_false_negative_rate']:.1%}")
    print(
        "Latency: "
        f"mean={overall['latency_s']['mean']:.2f}s "
        f"p50={overall['latency_s']['p50']:.2f}s "
        f"p95={overall['latency_s']['p95']:.2f}s"
    )
    for kind, metrics in summary["by_kind"].items():
        print(f"{kind}: {metrics['document_accuracy']:.1%} ({metrics['cases']} cases)")
    for quality, metrics in summary["by_quality"].items():
        print(f"quality/{quality}: {metrics['document_accuracy']:.1%} ({metrics['cases']} cases)")
    print("Results:", summary["results_path"])
    print("Summary:", summary["summary_path"])
    print("NOTE:", summary["scope_warning"])


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate the synthetic vision benchmark corpus")
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    generated_manifest = generate_corpus(args.output_dir, count=args.count, seed=args.seed)
    print(generated_manifest)
