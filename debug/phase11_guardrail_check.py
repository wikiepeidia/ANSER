import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = PROJECT_ROOT / ".planning/phases/11-baseline-contract-guardrails/11-guardrail-report.md"
SNAPSHOT_OUT = (
    ".planning/phases/11-baseline-contract-guardrails/11-endpoint-snapshot.json"
)

SNAPSHOT_CMD = [
    sys.executable,
    "scripts/phase11_route_snapshot.py",
    "--out",
    SNAPSHOT_OUT,
]

CONTRACT_CMD = [
    sys.executable,
    "-m",
    "pytest",
    "tests/contracts",
    "-q",
]


def _run_command(command):
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )


def _format_block(text):
    normalized = (text or "").strip()
    if not normalized:
        return "(no output)"
    return normalized


def _write_report(snapshot_result, contract_result, overall_status):
    generated_at = datetime.now(timezone.utc).isoformat()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    contract_status = "NOT RUN"
    contract_command = " ".join(CONTRACT_CMD)
    contract_stdout = "(not run)"
    contract_stderr = "(not run)"
    contract_exit = "N/A"

    if contract_result is not None:
        contract_status = "PASS" if contract_result.returncode == 0 else "FAIL"
        contract_stdout = _format_block(contract_result.stdout)
        contract_stderr = _format_block(contract_result.stderr)
        contract_exit = str(contract_result.returncode)

    snapshot_status = "PASS" if snapshot_result.returncode == 0 else "FAIL"

    report = f"""# Phase 11 Guardrail Report

Generated: {generated_at}

## Snapshot
- Command: {' '.join(SNAPSHOT_CMD)}
- Status: {snapshot_status}
- Exit Code: {snapshot_result.returncode}

### Stdout
```
{_format_block(snapshot_result.stdout)}
```

### Stderr
```
{_format_block(snapshot_result.stderr)}
```

## Contract Tests
- Command: {contract_command}
- Status: {contract_status}
- Exit Code: {contract_exit}

### Stdout
```
{contract_stdout}
```

### Stderr
```
{contract_stderr}
```

## Overall Gate
- Status: {overall_status}
- Rule: Phase 12 extraction remains blocked unless Overall Gate is PASS.
"""

    REPORT_PATH.write_text(report, encoding="utf-8")


def main():
    snapshot_result = _run_command(SNAPSHOT_CMD)

    if snapshot_result.returncode != 0:
        _write_report(snapshot_result, None, "FAIL")
        print("Guardrail check failed during snapshot step.")
        print(f"Report: {REPORT_PATH.as_posix()}")
        return 1

    contract_result = _run_command(CONTRACT_CMD)
    overall_pass = contract_result.returncode == 0

    _write_report(snapshot_result, contract_result, "PASS" if overall_pass else "FAIL")

    if overall_pass:
        print("Guardrail check passed.")
    else:
        print("Guardrail check failed during contract test step.")

    print(f"Report: {REPORT_PATH.as_posix()}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
