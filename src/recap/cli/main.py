from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from recap import __version__
from recap.core.errors import RecapError
from recap.core.orchestrator import run_recap
from recap.security.redaction import redact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="recap",
        description="Analyze a Git repository locally and prepare a human-reviewed release plan.",
    )
    parser.add_argument(
        "--directory",
        "-C",
        type=Path,
        default=Path.cwd(),
        help="Repository path (default: current directory).",
    )
    parser.add_argument(
        "--no-ai",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run the detected project test command. Repository code is not sandboxed.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Write the report as JSON and do not prompt interactively.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    run_tests = args.run_tests
    if not run_tests and sys.stdin.isatty() and not args.json_output:
        answer = input(
            "Run detected project tests? This executes repository code without a sandbox. [y/N] "
        ).strip()
        run_tests = answer.lower() in {"y", "yes"}
    try:
        report = run_recap(
            args.directory,
            no_ai=args.no_ai,
            json_output=args.json_output,
            run_project_tests=run_tests,
        )
        return 1 if any(check.status in {"failed", "incomplete"} for check in report.checks) else 0
    except (RecapError, OSError, ValueError, EOFError) as exc:
        message = redact(str(exc))
        if args.json_output:
            print(json.dumps({"error": message}), file=sys.stderr)
        else:
            print(f"recap: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
