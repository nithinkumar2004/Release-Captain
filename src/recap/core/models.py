from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class GitAnalysis:
    root: Path
    branch: str
    commit: str
    changed_files: list[str]
    diff_summary: str


@dataclass(slots=True)
class CheckResult:
    name: str
    status: str
    summary: str
    details: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SecurityFinding:
    severity: str
    path: str
    rule: str
    summary: str


@dataclass(slots=True)
class RiskAssessment:
    score: int
    level: str
    factors: list[str]


@dataclass(slots=True)
class RunReport:
    repository: str
    platform: str
    project_type: str
    git: GitAnalysis
    checks: list[CheckResult]
    findings: list[SecurityFinding]
    risk: RiskAssessment
    ai_summary: str | None = None
    release_status: str = "not_started"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["git"]["root"] = str(self.git.root)
        return data
