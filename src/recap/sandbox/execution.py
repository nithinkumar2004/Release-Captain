from recap.core.models import CheckResult


def sandbox_status(command_will_run: bool) -> CheckResult:
    if command_will_run:
        return CheckResult(
            "sandbox",
            "unsupported",
            "No OS-level sandbox is configured; project test code runs with the current user's permissions.",
        )
    return CheckResult(
        "sandbox",
        "skipped",
        "No project command was executed; recap does not claim sandbox isolation.",
    )
