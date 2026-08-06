"""Tests for the resumable synthetic manufacturing vision benchmark."""

import asyncio
import json
from pathlib import Path

from offline_training.manufacturing_vision_benchmark import (
    CUSTOMER_FIELDS,
    MATERIAL_FIELDS,
    endpoint_like_result,
    evaluate_case,
    generate_corpus,
    run_benchmark,
    summarize_results,
)


def _read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_generate_corpus_is_balanced_deterministic_and_persistent(tmp_path):
    first_path = generate_corpus(tmp_path / "corpus", count=8, seed=1234)
    first = _read_manifest(first_path)
    second_path = generate_corpus(tmp_path / "corpus", count=8, seed=1234)
    second = _read_manifest(second_path)

    assert first == second
    assert first["count"] == 8
    assert sum(case["kind"] == "customer_order" for case in first["cases"]) == 4
    assert sum(case["kind"] == "material_batch" for case in first["cases"]) == 4
    assert {case["quality"] for case in first["cases"]} == {
        "clean",
        "mild",
        "medium",
        "hard",
    }
    for case in first["cases"]:
        image_path = first_path.parent / case["image"]
        assert image_path.is_file()
        assert image_path.stat().st_size > 0


def test_customer_order_exact_response_scores_complete(tmp_path):
    manifest_path = generate_corpus(tmp_path / "corpus", count=2, seed=22)
    case = _read_manifest(manifest_path)["cases"][0]
    response = endpoint_like_result(case["truth"])

    evaluation = evaluate_case(case, response)

    assert evaluation["document_complete"] is True
    assert evaluation["review_correct"] is True
    assert evaluation["review_false_negative"] is False
    assert all(evaluation["field_scores"][field] for field in CUSTOMER_FIELDS)
    assert evaluation["field_scores"]["irrelevant_metadata_null"] is True


def test_material_missing_field_exposes_review_false_negative(tmp_path):
    manifest_path = generate_corpus(tmp_path / "corpus", count=2, seed=23)
    case = _read_manifest(manifest_path)["cases"][1]
    incomplete = dict(case["truth"])
    incomplete["gacp_cert"] = None
    response = endpoint_like_result(incomplete)

    evaluation = evaluate_case(case, response)

    assert evaluation["document_complete"] is False
    assert evaluation["field_scores"]["gacp_cert"] is False
    assert response["needs_manual_review"] is False
    assert evaluation["review_false_negative"] is True
    assert all(field in case["truth"] for field in MATERIAL_FIELDS)


def test_summary_splits_kind_quality_and_field_accuracy(tmp_path):
    manifest_path = generate_corpus(tmp_path / "corpus", count=4, seed=24)
    cases = _read_manifest(manifest_path)["cases"]
    rows = []
    for case in cases:
        response = endpoint_like_result(case["truth"])
        rows.append(
            {
                "case_id": case["case_id"],
                "kind": case["kind"],
                "quality": case["quality"],
                "elapsed_s": 1.0 + len(rows),
                "evaluation": evaluate_case(case, response),
                "error": None,
            }
        )

    summary = summarize_results(rows, expected_count=4, run_name="unit")

    assert summary["is_complete"] is True
    assert summary["overall"]["document_accuracy"] == 1.0
    assert summary["overall"]["latency_s"] == {"mean": 2.5, "p50": 2.0, "p95": 4.0}
    assert summary["by_kind"]["customer_order"]["cases"] == 2
    assert summary["by_kind"]["material_batch"]["cases"] == 2
    assert summary["failure_count"] == 0


class _TruthAgent:
    def __init__(self, truth_by_name):
        self.truth_by_name = truth_by_name
        self.calls = 0

    async def extract_manufacturing_invoice(self, image_path):
        self.calls += 1
        return self.truth_by_name[Path(image_path).name]


def test_runner_checkpoints_and_resumes_without_repeating_cases(tmp_path):
    manifest_path = generate_corpus(tmp_path / "corpus", count=4, seed=25)
    manifest = _read_manifest(manifest_path)
    truth_by_name = {
        Path(case["image"]).name: case["truth"]
        for case in manifest["cases"]
    }
    first_agent = _TruthAgent(truth_by_name)

    first = asyncio.run(
        run_benchmark(manifest_path, first_agent, run_name="resume-test", limit=2)
    )

    assert first["completed_cases"] == 2
    assert first_agent.calls == 2

    second_agent = _TruthAgent(truth_by_name)
    second = asyncio.run(
        run_benchmark(manifest_path, second_agent, run_name="resume-test", limit=2)
    )

    assert second["completed_cases"] == 2
    assert second_agent.calls == 0
    assert Path(second["results_path"]).read_text(encoding="utf-8").count("\n") == 2
