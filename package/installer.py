"""Simple dependency installer for the project."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIREMENTS = ROOT / "requirements.txt"


def run_step(description: str, command: list[str]) -> None:
	"""Run a shell step and surface failures immediately."""
	print(f"\n==> {description}")
	print("$", " ".join(command))
	subprocess.check_call(command)


def main() -> int:
	if not REQUIREMENTS.exists():
		print(f"requirements file not found at {REQUIREMENTS}")
		return 1

	try:
		run_step("Upgrading pip", [sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
		run_step(
			"Installing project dependencies",
			[sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS)],
		)
	except subprocess.CalledProcessError as exc:
		print(f"Command failed with exit code {exc.returncode}")
		return exc.returncode or 1

	print("\nAll dependencies installed successfully.")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
