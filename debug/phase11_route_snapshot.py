import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _normalize_methods(methods):
    return sorted([m for m in methods if m not in {"HEAD", "OPTIONS"}])


def _load_manifest(manifest_path):
    with manifest_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    endpoints = data.get("endpoints", [])
    if not isinstance(endpoints, list):
        raise ValueError("Manifest 'endpoints' must be a list")

    return data, endpoints


def _collect_routes():
    import app as app_module

    flask_app = getattr(app_module, "app", None)
    if flask_app is None:
        flask_app = app_module.create_app()

    route_map = {}
    for rule in flask_app.url_map.iter_rules():
        existing = route_map.setdefault(rule.rule, [])
        merged = sorted(set(existing) | set(_normalize_methods(rule.methods)))
        route_map[rule.rule] = merged
    return route_map


def _build_snapshot(endpoints, route_map):
    entries = []
    found_count = 0
    missing_paths = []
    method_mismatches = []

    for endpoint in sorted(endpoints, key=lambda item: item.get("path", "")):
        path = endpoint.get("path", "")
        expected_methods = sorted(endpoint.get("methods", []))
        actual_methods = route_map.get(path)
        found = actual_methods is not None

        if not found:
            missing_paths.append(path)
            actual_methods = []
        else:
            found_count += 1

        missing_methods = [m for m in expected_methods if m not in actual_methods]
        unexpected_methods = [m for m in actual_methods if m not in expected_methods]

        if missing_methods:
            method_mismatches.append(
                {
                    "path": path,
                    "missing_methods": missing_methods,
                    "actual_methods": actual_methods,
                }
            )

        entries.append(
            {
                "id": endpoint.get("id"),
                "group": endpoint.get("group"),
                "path": path,
                "expected_methods": expected_methods,
                "actual_methods": actual_methods,
                "found": found,
                "missing_methods": missing_methods,
                "unexpected_methods": unexpected_methods,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
        "summary": {
            "total": len(entries),
            "found": found_count,
            "missing_path_count": len(missing_paths),
            "method_mismatch_count": len(method_mismatches),
            "missing_paths": missing_paths,
            "method_mismatches": method_mismatches,
        },
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate route contract snapshot for Phase 11 guardrails."
    )
    parser.add_argument(
        "--manifest",
        default=".planning/phases/11-baseline-contract-guardrails/11-endpoint-manifest.json",
        help="Path to endpoint manifest JSON",
    )
    parser.add_argument(
        "--out",
        default=".planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json",
        help="Snapshot output path",
    )
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    out_path = Path(args.out)

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")

    manifest, endpoints = _load_manifest(manifest_path)
    route_map = _collect_routes()
    snapshot = _build_snapshot(endpoints, route_map)

    output = {
        "phase": manifest.get("phase", "11"),
        "name": manifest.get("name", "baseline-contract-guardrails"),
        "source_manifest": str(manifest_path).replace("\\", "/"),
        "snapshot": snapshot,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    summary = snapshot["summary"]
    print(
        "Snapshot written:",
        str(out_path).replace("\\", "/"),
        "| total:",
        summary["total"],
        "| found:",
        summary["found"],
        "| missing_paths:",
        summary["missing_path_count"],
        "| method_mismatches:",
        summary["method_mismatch_count"],
    )


if __name__ == "__main__":
    main()
