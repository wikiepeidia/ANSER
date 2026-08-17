"""Tests for the deterministic Phase 13 live-OCR fixtures."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from offline_training.generate_phase13_ocr_fixtures import (
    FIXTURE_SPECS,
    IMAGE_SIZE,
    OUTPUT_FILENAMES,
    generate_fixtures,
    measure_document,
    resolve_font_paths,
)
from offline_training.manufacturing_vision_benchmark import endpoint_like_result


SCHEMA_KEYS = {
    "items",
    "total",
    "farmer",
    "region_grown",
    "part",
    "form",
    "gacp_cert",
    "doc_no",
    "customer_code",
    "region",
    "deadline",
}

EXPECTED_TRUTHS = {
    "customer_order": {
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
    "material_batch": {
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
}


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _explicit_test_font() -> Path:
    regular, _ = resolve_font_paths()
    return regular


def test_generation_is_byte_deterministic_with_the_same_explicit_font(tmp_path):
    font = _explicit_test_font()
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first_manifest = generate_fixtures(first_root, font=font)
    second_manifest = generate_fixtures(second_root, font=font)

    for filename in OUTPUT_FILENAMES:
        assert (first_root / filename).read_bytes() == (second_root / filename).read_bytes()
    assert first_manifest.read_bytes() == second_manifest.read_bytes()


def test_images_have_fixed_properties_are_nonblank_and_do_not_clip(tmp_path):
    font = _explicit_test_font()
    manifest_path = generate_fixtures(tmp_path, font=font)
    manifest = _load_manifest(manifest_path)

    for fixture in manifest["fixtures"].values():
        with Image.open(tmp_path / fixture["filename"]) as image:
            assert image.size == IMAGE_SIZE
            assert image.mode == "RGB"
            assert ImageChops.difference(
                image, Image.new("RGB", IMAGE_SIZE, "white")
            ).getbbox() is not None

    for spec in FIXTURE_SPECS:
        for left, top, right, bottom in measure_document(spec, font=font):
            assert 0 <= left < right <= IMAGE_SIZE[0]
            assert 0 <= top < bottom <= IMAGE_SIZE[1]


def test_manifest_has_exact_files_truth_hashes_and_safe_webhook_contract(tmp_path):
    manifest_path = generate_fixtures(tmp_path, font=_explicit_test_font())
    manifest = _load_manifest(manifest_path)

    assert {path.name for path in tmp_path.iterdir()} == set(OUTPUT_FILENAMES)
    assert manifest_path.name == "manifest.json"
    assert set(manifest["fixtures"]) == set(EXPECTED_TRUTHS)
    assert manifest["webhook_contract"] == {
        "auth_header": "x-anser-token",
        "multipart_field": "data",
        "customer_order": {"endpoint": "/webhook/customer-order-ocr"},
        "material_batch": {"endpoint": "/webhook/material-intake"},
    }

    for kind, expected_truth in EXPECTED_TRUTHS.items():
        fixture = manifest["fixtures"][kind]
        assert fixture["truth"] == expected_truth
        assert set(fixture["truth"]) == SCHEMA_KEYS
        assert set(fixture["truth"]["items"][0]) == {
            "sku",
            "name",
            "qty",
            "unit_price",
        }
        assert fixture["sha256"] == _sha256(tmp_path / fixture["filename"])

    serialized = manifest_path.read_text(encoding="utf-8")
    assert "sanxuat-dev-token" not in serialized
    assert "timestamp" not in serialized.casefold()
    assert str(tmp_path.resolve()) not in serialized


def test_monetary_rows_are_plain_digits_and_vat_arithmetic_is_exact():
    for spec in FIXTURE_SPECS:
        monetary_values = {
            label: value
            for label, value in spec["rows"]
            if label in {
                "Don gia (truoc thue)",
                "Tong cong thanh toan (da gom VAT 10%)",
            }
        }
        assert monetary_values.keys() == {
            "Don gia (truoc thue)",
            "Tong cong thanh toan (da gom VAT 10%)",
        }
        assert all(re.fullmatch(r"\d+ VND", value) for value in monetary_values.values())

        truth = spec["truth"]
        item = truth["items"][0]
        assert truth["total"] * 10 == item["qty"] * item["unit_price"] * 11


def test_truths_are_family_separated_and_pass_endpoint_validation(tmp_path):
    manifest = _load_manifest(
        generate_fixtures(tmp_path, font=_explicit_test_font())
    )
    customer = manifest["fixtures"]["customer_order"]["truth"]
    material = manifest["fixtures"]["material_batch"]["truth"]

    assert all(
        customer[field] is None
        for field in ("farmer", "region_grown", "part", "form", "gacp_cert")
    )
    assert all(
        material[field] is None
        for field in ("doc_no", "customer_code", "region", "deadline")
    )
    assert material["items"][0]["sku"] == "NVL-008"

    for truth in (customer, material):
        result = endpoint_like_result(truth)
        assert result["success"] is True
        assert result["validation"]["is_valid"] is True
        assert result["validation"]["difference"] == 0
        assert result["needs_manual_review"] is False


def test_existing_target_refuses_before_writing_and_force_replaces(tmp_path):
    font = _explicit_test_font()
    generate_fixtures(tmp_path, font=font)
    customer_path = tmp_path / "customer_order.png"
    material_path = tmp_path / "material_weigh_slip.png"
    manifest_path = tmp_path / "manifest.json"
    original_material = material_path.read_bytes()
    customer_path.write_bytes(b"do-not-overwrite")

    with pytest.raises(FileExistsError, match="--force"):
        generate_fixtures(tmp_path, font=font)

    assert customer_path.read_bytes() == b"do-not-overwrite"
    assert material_path.read_bytes() == original_material
    assert manifest_path.is_file()

    replaced_manifest = generate_fixtures(tmp_path, font=font, force=True)
    assert customer_path.read_bytes() != b"do-not-overwrite"
    assert _load_manifest(replaced_manifest)["fixtures"]["customer_order"][
        "sha256"
    ] == _sha256(customer_path)
