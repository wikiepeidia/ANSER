"""Run Phase 14 backend coverage gate and write an auditable report."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

REPORT_PATH = Path(
    ".planning/phases/14-backend-branch-integration-checkpoint/14-backend-coverage-report.md"
)
DEFAULT_TEST_TARGETS = ["tests/services", "tests/contracts"]


def parse_args() -> argparse.Namespace:
    """Parse command-line options for the coverage gate."""
    parser = argparse.ArgumentParser(
        description="Execute backend coverage gate for Phase 14."
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=25.0,
        help="Coverage percentage required to pass the gate (default: 25).",
    )
    parser.add_argument(
        "--tests",
        nargs="+",
        default=DEFAULT_TEST_TARGETS,
        help="Pytest target paths to execute.",
    )
    parser.add_argument(
        "--report-path",
        default=str(REPORT_PATH),
        help="Output markdown report path.",
    )
    return parser.parse_args()


def extract_total_coverage(output: str) -> Optional[float]:
    """Extract TOTAL coverage percentage from pytest-cov output text."""
    total_matches = re.findall(r"TOTAL\s+\d+\s+\d+\s+(\d+(?:\.\d+)?)%", output)
    if total_matches:
        return float(total_matches[-1])

    summary_matches = re.findall(r"Total coverage:\s*(\d+(?:\.\d+)?)%", output)
    if summary_matches:
        return float(summary_matches[-1])

    return None


def build_pytest_command(threshold: float, tests: list[str]) -> list[str]:
    """Build pytest command line with coverage gate options."""
    command = [
        sys.executable,
        "-m",
        "pytest",
        *tests,
        "-q",
        "--cov=app",
        "--cov=core",
        "--cov=routes",
        "--cov-config=.coveragerc",
        "--cov-report=term-missing:skip-covered",
        f"--cov-fail-under={threshold}",
    ]
    return command


def write_report(
    report_path: Path,
    command: list[str],
    threshold: float,
    exit_code: int,
    coverage: Optional[float],
    output: str,
) -> None:
    """Write a phase-local markdown artifact for checkpoint traceability."""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    status = "passed" if exit_code == 0 else "failed"
    coverage_text = f"{coverage:.1f}%" if coverage is not None else "N/A"
    timestamp = datetime.now(timezone.utc).isoformat()

    content = "\n".join(
        [
            "# Phase 14 Backend Coverage Gate Report",
            "",
            f"- Timestamp (UTC): {timestamp}",
            f"- Status: {status}",
            f"- Threshold: {threshold:.1f}%",
            f"- Measured Coverage: {coverage_text}",
            f"- Exit Code: {exit_code}",
            "",
            "## Command",
            "",
            "```bash",
            " ".join(command),
            "```",
            "",
            "## Raw Output",
            "",
            "```text",
            output.rstrip() or "(no output)",
            "```",
            "",
            "## Guidance",
            "",
            "- Keep the threshold at or above the current pass line for merge preparation.",
            "- Raise threshold gradually after each stabilization cycle.",
        ]
    )

    report_path.write_text(content + "\n", encoding="utf-8")


def main() -> int:
    """Execute the coverage gate and return pytest exit code."""
    args = parse_args()
    report_path = Path(args.report_path)

    os.environ.setdefault("PYTHONUTF8", "1")
    command = build_pytest_command(args.threshold, args.tests)

    result = subprocess.run(command, capture_output=True, text=True)
    combined_output = "\n".join(
        part for part in [result.stdout, result.stderr] if part.strip()
    )
    coverage = extract_total_coverage(combined_output)

    write_report(
        report_path=report_path,
        command=command,
        threshold=args.threshold,
        exit_code=result.returncode,
        coverage=coverage,
        output=combined_output,
    )

    status = "PASSED" if result.returncode == 0 else "FAILED"
    coverage_text = f"{coverage:.1f}%" if coverage is not None else "N/A"
    print(
        f"Phase 14 coverage gate {status}: threshold={args.threshold:.1f}%, "
        f"coverage={coverage_text}, report={report_path}"
    )

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)

    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
