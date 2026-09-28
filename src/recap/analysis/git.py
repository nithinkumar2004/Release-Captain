from __future__ import annotations

import subprocess
from pathlib import Path

from recap.core.errors import RecapError
from recap.core.models import GitAnalysis


def _git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.CalledProcessError as exc:
        raise RecapError(f"Git command failed: git {' '.join(args[:2])}") from exc
    except subprocess.TimeoutExpired as exc:
        raise RecapError("Git analysis timed out.") from exc
    return result.stdout


def analyze_git(root: Path) -> GitAnalysis:
    branch = _git(root, "branch", "--show-current").strip() or "(detached HEAD)"
    try:
        commit = _git(root, "rev-parse", "--short", "HEAD").strip()
    except RecapError:
        commit = "(no commits yet)"
    status = _git(root, "status", "--short", "--untracked-files=all")
    changed = [line[3:].strip() for line in status.splitlines() if len(line) >= 4]
    diff = "\n".join(
        part
        for part in (_git(root, "diff", "--stat"), _git(root, "diff", "--cached", "--stat"))
        if part.strip()
    )
    return GitAnalysis(
        root=root, branch=branch, commit=commit, changed_files=changed, diff_summary=diff.strip()
    )
