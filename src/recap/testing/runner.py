from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from recap.core.models import CheckResult
from recap.security.redaction import redact

TEST_COMMANDS: dict[str, tuple[str, ...]] = {
    "Python": ("python", "-m", "unittest", "discover", "-v"),
    "Node.js": ("npm", "test"),
    "Rust": ("cargo", "test"),
    "Go": ("go", "test", "./..."),
    ".NET": ("dotnet", "test"),
}


def test_command(project_type: str) -> tuple[str, ...] | None:
    if project_type.startswith("Multiple: "):
        return None
    return TEST_COMMANDS.get(project_type)


def run_tests(root: Path, project_type: str, timeout_seconds: int = 300) -> CheckResult:
    command = test_command(project_type)
    if command is None:
        return CheckResult("tests", "skipped", "No unambiguous test command is configured.")
    if not _command_exists(command[0]):
        return CheckResult("tests", "skipped", f"Required tool {command[0]!r} was not found.")
    started = time.monotonic()
    env = {
        key: value
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
        if (value := os.environ.get(key))
    }
    env.update({"CI": "1", "NO_COLOR": "1", "PYTHONNOUSERSITE": "1"})
    env["PYTHONPATH"] = str(root / "src")
    try:
        result = subprocess.run(
            list(command),
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return CheckResult("tests", "failed", f"Test command timed out after {timeout_seconds}s.")
    elapsed = round(time.monotonic() - started, 1)
    summary = (
        f"{'Passed' if result.returncode == 0 else 'Failed'} ({elapsed}s): {' '.join(command)}"
    )
    output = (result.stdout + "\n" + result.stderr).strip().splitlines()
    details = [redact(line) for line in output[-20:]]
    return CheckResult("tests", "passed" if result.returncode == 0 else "failed", summary, details)


def _command_exists(command: str) -> bool:
    from shutil import which

    return which(command) is not None
