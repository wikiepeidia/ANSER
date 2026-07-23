"""VER-02: extracts iv-normalize's real jsCode from the workflow JSON and executes it in a
real Node.js subprocess against mocked Brain /ocr responses, mirroring v1.0 Phase 1's
verification technique ("standalone Node.js simulation of the normalizer's jsCode"), now
formalized as a committed, repeatable pytest instead of one-off verifier evidence.
"""

import json
import subprocess

import pytest

WORKFLOW_PATH = "workflow_templates/invoice_vlm_digitize.json"


def _load_workflow():
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        return json.load(f)


def _find_node(nodes, node_id):
    for node in nodes:
        if node.get("id") == node_id:
            return node
    raise AssertionError(f"node {node_id!r} not found in workflow")


def _run_normalizer(mocked_response):
    jscode = _find_node(_load_workflow()["nodes"], "iv-normalize")["parameters"]["jsCode"]
    harness = (
        f"const $input = {{ first: () => ({{ json: {json.dumps(mocked_response)} }}) }};\n"
        f"function __run() {{\n{jscode}\n}}\n"
        "const __result = __run();\n"
        "console.log(JSON.stringify(__result[0].json));\n"
    )
    proc = subprocess.run(
        ["node", "-e", harness],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"node harness failed: {proc.stderr}")
    return json.loads(proc.stdout.strip())


_NORMALIZE_CASES = [
    (
        "brain_connection_error",
        {"error": "connection refused"},
        "error",
    ),
    # iv-normalize's very first check is unconditional `if (item.error)`, which fires whenever
    # ANY `error` key is present on the mocked item, including Brain's documented
    # schema/business-logic-failure shape (which always carries its own `error` field per the
    # CONTRACT doc) -- so this case is caught by the `error` branch before the
    # `success`/`needs_manual_review` check is ever reached. This is still safe: per the
    # workflow's connections, both the `error` and `needs_manual_review` branches route only to
    # the Discord notification node, never to the write-back node -- so this collapse changes an
    # internal label, not the safety-critical write-back gating.
    (
        "brain_schema_invalid_failure",
        {"success": False, "error": "schema_invalid: invalid JSON returned by model"},
        "error",
    ),
    (
        "brain_flagged_needs_manual_review",
        {
            "success": True,
            "needs_manual_review": True,
            "invoice": {"items": [], "total": 0},
            "validation": {"is_valid": True, "calculated_total": 0, "difference": 0},
        },
        "needs_manual_review",
    ),
    (
        "brain_clean_success",
        {
            "success": True,
            "needs_manual_review": False,
            "invoice": {
                "items": [{"name": "Coca", "price": 1, "qty": 1, "is_reduced_vat": False}],
                "total": 1,
            },
            "validation": {"is_valid": True, "calculated_total": 1, "difference": 0},
        },
        "pending_review",
    ),
]


@pytest.mark.parametrize(
    "case_id, mocked_response, expected_branch",
    _NORMALIZE_CASES,
    ids=[c[0] for c in _NORMALIZE_CASES],
)
def test_normalizer_routes_to_expected_branch(case_id, mocked_response, expected_branch):
    assert _run_normalizer(mocked_response)["branch"] == expected_branch
