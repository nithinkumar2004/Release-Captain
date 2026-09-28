from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from recap.core.models import RunReport
from recap.security.redaction import redact


def create_audit_record(report: RunReport) -> dict[str, Any]:
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "repository": report.repository,
        "commit": report.git.commit,
        "risk": {"score": report.risk.score, "level": report.risk.level},
        "checks": [{"name": item.name, "status": item.status} for item in report.checks],
        "release_status": report.release_status,
        "ai_summary": redact(report.ai_summary) if report.ai_summary else None,
    }
