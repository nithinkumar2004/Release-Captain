from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from recap.analysis.dependencies import analyze_dependencies
from recap.analysis.git import analyze_git
from recap.analysis.risk import assess_risk
from recap.audit.records import create_audit_record
from recap.core.errors import RecapError
from recap.core.models import CheckResult, RunReport
from recap.credentials.ephemeral import CredentialManager
from recap.detection.environment import platform_name
from recap.detection.project import detect_project
from recap.detection.repository import find_repository
from recap.llm.base import ProviderError
from recap.llm.resolver import PROVIDERS, resolve_provider
from recap.release.executor import ReleaseExecutor
from recap.release.planner import build_release_plan
from recap.sandbox.execution import sandbox_status
from recap.security.redaction import redact
from recap.security.scanner import scan_secrets
from recap.testing.runner import run_tests

PROVIDER_CHOICES = ("openrouter", "openai", "anthropic", "hosted")


def run_recap(
    path: Path,
    *,
    no_ai: bool = False,
    json_output: bool = False,
    run_project_tests: bool = False,
    approve_release: bool = False,
) -> RunReport:
    root = find_repository(path.resolve())
    project_type = detect_project(root)
    git = analyze_git(root)
    secret_scan = scan_secrets(root)
    findings = secret_scan.findings
    dependency_check = analyze_dependencies(root)
    if run_project_tests:
        test_check = run_tests(root, project_type)
    else:
        test_check = CheckResult(
            "tests",
            "skipped",
            "Not run. Use --run-tests to execute detected project tests (repository code is not sandboxed).",
        )
    checks = [
        CheckResult("repository", "passed", f"Git repository found at {root}."),
        CheckResult("project", "passed" if project_type != "Unknown" else "skipped", project_type),
        test_check,
        sandbox_status(run_project_tests),
        dependency_check,
        CheckResult(
            "security",
            "incomplete" if secret_scan.skipped_files else "failed" if findings else "passed",
            f"{len(findings)} possible hard-coded secret(s) found; "
            f"{secret_scan.skipped_files} file(s) could not be inspected."
            if secret_scan.skipped_files
            else f"{len(findings)} possible hard-coded secret(s) found."
            if findings
            else "No matching hard-coded-secret patterns found.",
            [
                f"{secret_scan.skipped_files} file(s) were unreadable, non-UTF-8, or above the scan size limit."
            ]
            if secret_scan.skipped_files
            else [],
        ),
    ]
    risk = assess_risk(git.changed_files, checks, findings)
    report = RunReport(
        repository=root.name,
        platform=platform_name(),
        project_type=project_type,
        git=git,
        checks=checks,
        findings=findings,
        risk=risk,
    )

    ai_needed = risk.level in {"medium", "high"} or any(
        check.status in {"failed", "incomplete"} for check in checks
    )
    if ai_needed and not no_ai:
        _run_ai(report, json_output=json_output)

    print_plan = build_release_plan(report)
    report.release_status = _handle_release(
        report, approve_release, print_plan, json_output=json_output
    )
    report.checks.append(
        CheckResult(
            "release",
            "skipped",
            "No release target is configured; no release action was executed."
            if report.release_status == "not_configured"
            else report.release_status.replace("_", " "),
        )
    )
    report.risk = assess_risk(git.changed_files, report.checks, findings)
    report.checks.append(
        CheckResult("audit", "passed", "Credential-free in-memory audit record created.")
    )
    audit_record = create_audit_record(report)
    if json_output:
        payload = report.to_dict()
        payload["release_plan"] = print_plan
        payload["audit"] = audit_record
        print(json.dumps(payload, indent=2))
    else:
        _print_report(report, print_plan, audit_record)
    return report


def _run_ai(report: RunReport, *, json_output: bool) -> None:
    interactive = sys.stdin.isatty() and not json_output
    provider_name = "" if interactive else os.environ.get("RECAP_PROVIDER", "").strip().lower()
    if interactive:
        print("\nAI analysis may help with this result. Choose a provider:")
        for index, name in enumerate(PROVIDER_CHOICES, start=1):
            print(f"  {index}. {name}")
        print(f"  {len(PROVIDER_CHOICES) + 1}. Continue without AI")
        selection = input("Select: ").strip()
        if selection == str(len(PROVIDER_CHOICES) + 1):
            report.checks.append(CheckResult("ai", "skipped", "AI analysis declined."))
            return
        if selection.isdigit() and 1 <= int(selection) <= len(PROVIDER_CHOICES):
            provider_name = PROVIDER_CHOICES[int(selection) - 1]
        else:
            raise RecapError("Invalid AI provider selection.")
    if not provider_name:
        report.checks.append(
            CheckResult(
                "ai",
                "skipped",
                "AI analysis needed but no provider selected; set RECAP_PROVIDER or run interactively.",
            )
        )
        return
    if provider_name not in PROVIDERS:
        raise RecapError(f"Unsupported RECAP_PROVIDER value: {provider_name}.")

    manager = CredentialManager()
    credential = manager.acquire(provider_name, allow_prompt=sys.stdin.isatty() and not json_output)
    try:
        context = (
            f"Project type: {report.project_type}\n"
            f"Changed file count: {len(report.git.changed_files)}\n"
            f"Check statuses: {', '.join(f'{c.name}={c.status}' for c in report.checks)}\n"
            f"Security finding count: {len(report.findings)}\n"
            f"Risk: {report.risk.level} ({report.risk.score}/100)\n"
            "Do not assume access to source code. Identify only risks supported by this summary."
        )
        report.ai_summary = redact(
            resolve_provider(provider_name).analyze(context, credential.reveal()),
            [credential.reveal()],
        )
        report.checks.append(
            CheckResult("ai", "passed", f"Analysis completed via {provider_name}.")
        )
    except ProviderError as exc:
        report.checks.append(CheckResult("ai", "failed", str(exc)))
    finally:
        credential.clear()


def _handle_release(
    report: RunReport, approved: bool, plan: list[str], *, json_output: bool
) -> str:
    if not approved:
        if sys.stdin.isatty() and not json_output:
            print(
                f"\nRisk: {report.risk.level.upper()} ({report.risk.score}/100); "
                f"potential security findings: {len(report.findings)}."
            )
            print("\nProposed release plan:")
            for index, item in enumerate(plan, start=1):
                print(f"  {index}. {redact(item)}")
            answer = input(
                "\nApprove this plan? No release target is configured, so approval cannot publish. [y/N] "
            ).strip()
            approved = answer.lower() in {"y", "yes"}
        else:
            return "not_approved"
    if not approved:
        return "rejected"
    status = ReleaseExecutor().execute(report)
    return "not_configured" if status == "not_configured" else status


def _print_report(report: RunReport, plan: list[str], audit: dict[str, object]) -> None:
    print(f"\nRECAP — {report.repository}")
    print(f"Platform: {report.platform} | Project: {report.project_type}")
    print(f"Branch: {report.git.branch} | Commit: {report.git.commit}")
    print(f"Changed files: {len(report.git.changed_files)}")
    for check in report.checks:
        print(f"{check.status.upper():7} {check.name}: {redact(check.summary)}")
    for finding in report.findings:
        print(
            f"FINDING {finding.severity.upper()} {finding.path}: {finding.summary} ({finding.rule})"
        )
    print(f"Risk: {report.risk.level.upper()} ({report.risk.score}/100)")
    for factor in report.risk.factors:
        print(f"  - {factor}")
    if report.ai_summary:
        print("\nAI review (verify independently):")
        print(redact(report.ai_summary))
    print("\nRelease plan:")
    for index, item in enumerate(plan, start=1):
        print(f"  {index}. {redact(item)}")
    print(f"Release status: {report.release_status.replace('_', ' ')}")
    print(f"Audit summary created: {audit['timestamp']}")
