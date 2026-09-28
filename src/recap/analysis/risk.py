from recap.core.models import CheckResult, RiskAssessment, SecurityFinding


def assess_risk(
    changed_files: list[str], checks: list[CheckResult], findings: list[SecurityFinding]
) -> RiskAssessment:
    score = 0
    factors: list[str] = []
    if not changed_files:
        factors.append("No uncommitted changes detected.")
    else:
        score += min(20 + max(0, len(changed_files) - 1) * 2, 40)
        factors.append(f"{len(changed_files)} changed file(s) detected.")
    failed = [check for check in checks if check.status == "failed"]
    skipped = [
        check
        for check in checks
        if check.status == "skipped" and check.name in {"tests", "security", "dependencies"}
    ]
    incomplete = [check for check in checks if check.status == "incomplete"]
    if failed:
        score += 35
        factors.append(f"{len(failed)} check(s) failed.")
    if skipped:
        score += min(10 * len(skipped), 20)
        factors.append(f"{len(skipped)} check(s) were skipped.")
    if incomplete:
        score += min(20 * len(incomplete), 40)
        factors.append(f"{len(incomplete)} check(s) completed with incomplete coverage.")
    if findings:
        score += min(25 * len(findings), 50)
        factors.append(f"{len(findings)} potential security finding(s) detected.")
    score = min(score, 100)
    level = "low" if score < 30 else "medium" if score < 65 else "high"
    return RiskAssessment(score=score, level=level, factors=factors)
