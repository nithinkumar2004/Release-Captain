from recap.core.models import RunReport


def build_release_plan(report: RunReport) -> list[str]:
    actions = [
        f"Review {len(report.git.changed_files)} changed file(s) on branch {report.git.branch}.",
        f"Resolve all high-severity security findings ({len(report.findings)} detected).",
        f"Address failed or skipped checks before release (risk: {report.risk.level}, {report.risk.score}/100).",
    ]
    if report.ai_summary:
        actions.append(
            "Consider the optional AI review below; verify recommendations against repository evidence."
        )
    return actions
