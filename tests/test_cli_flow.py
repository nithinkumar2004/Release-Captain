from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from recap.core.orchestrator import run_recap


class CliFlowTests(unittest.TestCase):
    def test_json_run_on_unborn_repository_is_local_and_noninteractive(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", str(root)], check=True, capture_output=True)
            (root / "pyproject.toml").write_text(
                "[project]\nname='fixture'\nversion='1.0'\n", encoding="utf-8"
            )
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                report = run_recap(root, no_ai=True, json_output=True)
            payload = json.loads(output.getvalue())
            self.assertEqual(report.git.commit, "(no commits yet)")
            self.assertEqual(payload["project_type"], "Python")
            self.assertEqual(payload["release_status"], "not_approved")
            self.assertEqual(payload["checks"][-1]["name"], "audit")
            self.assertTrue(all(check["status"] != "failed" for check in payload["checks"]))


if __name__ == "__main__":
    unittest.main()
