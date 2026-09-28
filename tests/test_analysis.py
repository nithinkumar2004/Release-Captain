from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from recap.analysis.dependencies import analyze_dependencies
from recap.analysis.risk import assess_risk
from recap.core.models import CheckResult, SecurityFinding
from recap.detection.project import detect_project
from recap.security.scanner import scan_secrets


class AnalysisTests(unittest.TestCase):
    def test_detect_project_from_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text("[project]\nname = 'sample'\n", encoding="utf-8")
            self.assertEqual(detect_project(root), "Python")

    def test_ambiguous_project_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Cargo.toml").write_text("[package]\nname='sample'\n", encoding="utf-8")
            (root / "package.json").write_text("{}", encoding="utf-8")
            self.assertEqual(detect_project(root), "Multiple: Node.js, Rust")

    def test_dependency_inventory_does_not_claim_vulnerability_scan(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                '{"dependencies":{"example-lib":"^1.0"},"devDependencies":{"test-lib":"1"}}',
                encoding="utf-8",
            )
            result = analyze_dependencies(root)
            self.assertEqual(result.status, "passed")
            self.assertIn("no vulnerability database was queried", result.summary)
            self.assertEqual(result.details, ["example-lib", "test-lib"])

    def test_secret_scanner_reports_location_without_secret_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            candidate = "supersecretvalue123"
            (root / ".env").write_text(f"API_KEY='{candidate}'\n", encoding="utf-8")
            findings = scan_secrets(root).findings
            self.assertEqual(len(findings), 1)
            self.assertNotIn(candidate, findings[0].summary)
            self.assertEqual(findings[0].path, ".env:1")

    def test_repository_has_no_literal_secret_matches(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        result = scan_secrets(repository)
        self.assertEqual(result.findings, [])

    def test_secret_scanner_reports_files_above_size_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "large.txt").write_bytes(b"x" * 1_000_001)
            result = scan_secrets(root)
            self.assertEqual(result.skipped_files, 1)

    def test_risk_is_bounded_and_explainable(self) -> None:
        result = assess_risk(
            ["a.py"],
            [CheckResult("tests", "failed", "failed")],
            [SecurityFinding("high", "a.py:1", "token", "secret")],
        )
        self.assertEqual(result.score, 80)
        self.assertEqual(result.level, "high")
        self.assertTrue(result.factors)


if __name__ == "__main__":
    unittest.main()
