from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from recap.core.models import SecurityFinding

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "token-assignment",
        re.compile(
            r"""(?i)\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*"""
            r"""(?:"[^"\r\n]{12,}"|'[^'\r\n]{12,}'|[A-Za-z0-9_./+=-]{12,}(?=\s*(?:#|$)))"""
        ),
    ),
    ("cloud-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
)
SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "venv",
}
MAX_FILE_BYTES = 1_000_000


@dataclass(slots=True)
class SecretScanResult:
    findings: list[SecurityFinding]
    skipped_files: int


def scan_secrets(root: Path) -> SecretScanResult:
    findings: list[SecurityFinding] = []
    skipped_files = 0

    def record_walk_error(_error: OSError) -> None:
        nonlocal skipped_files
        skipped_files += 1

    for base, directories, filenames in os.walk(root, onerror=record_walk_error, followlinks=False):
        directories[:] = [
            name
            for name in directories
            if name not in SKIP_DIRS and not (Path(base) / name).is_symlink()
        ]
        for filename in filenames:
            path = Path(base) / filename
            if path.is_symlink():
                continue
            try:
                if path.stat().st_size > MAX_FILE_BYTES:
                    skipped_files += 1
                    continue
                with path.open("rb") as source:
                    raw_content = source.read(MAX_FILE_BYTES + 1)
                if len(raw_content) > MAX_FILE_BYTES:
                    skipped_files += 1
                    continue
                content = raw_content.decode("utf-8")
            except (OSError, UnicodeError):
                skipped_files += 1
                continue
            for line_number, line in enumerate(content.splitlines(), start=1):
                for rule, pattern in SECRET_PATTERNS:
                    if pattern.search(line):
                        findings.append(
                            SecurityFinding(
                                severity="high",
                                path=f"{path.relative_to(root)}:{line_number}",
                                rule=rule,
                                summary="Possible hard-coded secret detected; value is not displayed.",
                            )
                        )
                        break
    return SecretScanResult(findings, skipped_files)
