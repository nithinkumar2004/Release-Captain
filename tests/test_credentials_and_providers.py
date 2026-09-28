from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from recap.core.errors import RecapError
from recap.core.models import GitAnalysis, RiskAssessment, RunReport
from recap.core.orchestrator import _run_ai
from recap.credentials.ephemeral import CredentialManager
from recap.credentials.models import EphemeralCredential
from recap.llm.base import ProviderError
from recap.llm.hosted import HostedProvider
from recap.llm.http import _NoRedirect, post_json
from recap.security.redaction import redact
from server.hosted_ai.session_tokens import issue_session_token, verify_session_token


class CredentialAndProviderTests(unittest.TestCase):
    def test_credential_is_cleared_and_repr_does_not_reveal_value(self) -> None:
        credential = EphemeralCredential.create("openai", "do-not-print-this")
        self.assertNotIn("do-not-print-this", repr(credential))
        self.assertEqual(credential.reveal(), "do-not-print-this")
        credential.clear()
        with self.assertRaises(RuntimeError):
            credential.reveal()

    def test_prompted_credential_is_per_invocation(self) -> None:
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "environment-value"}, clear=True),
            patch("recap.credentials.ephemeral.getpass", return_value="temporary-key") as prompt,
        ):
            credential = CredentialManager().acquire("openai")
        prompt.assert_called_once()
        self.assertEqual(credential.reveal(), "temporary-key")
        credential.clear()

    def test_noninteractive_credential_requires_environment_secret(self) -> None:
        with (
            patch.dict(os.environ, {}, clear=True),
            self.assertRaisesRegex(ValueError, "OPENAI_API_KEY"),
        ):
            CredentialManager().acquire("openai", allow_prompt=False)

    def test_provider_http_request_uses_authorization_header(self) -> None:
        response = io.BytesIO(json.dumps({"ok": True}).encode())
        captured = {}

        class FakeOpener:
            def open(self, request, timeout):
                captured["request"] = request
                captured["timeout"] = timeout
                return response

        with patch("recap.llm.http.urllib.request.build_opener", return_value=FakeOpener()):
            result = post_json(
                "https://example.invalid", {"Authorization": "Bearer test"}, {"data": "x"}
            )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(captured["request"].get_header("Authorization"), "Bearer test")
        self.assertEqual(captured["timeout"], 60)

    def test_provider_failure_does_not_include_response_body_or_credentials(self) -> None:
        class FailingOpener:
            def open(self, request, timeout):
                raise urllib.error.HTTPError(
                    "https://example.invalid",
                    500,
                    "failure",
                    {},
                    io.BytesIO(b"response echoed private credential"),
                )

        with (
            patch("recap.llm.http.urllib.request.build_opener", return_value=FailingOpener()),
            self.assertRaises(ProviderError) as raised,
        ):
            post_json(
                "https://example.invalid",
                {"Authorization": "Bearer private-credential"},
                {},
            )
        self.assertNotIn("private-credential", str(raised.exception))
        self.assertNotIn("response echoed", str(raised.exception))

    def test_provider_redirects_are_rejected(self) -> None:
        handler = _NoRedirect()
        self.assertIsNone(
            handler.redirect_request(None, None, 302, "found", {}, "https://other.invalid")
        )

    def test_redaction_removes_credentials_and_sensitive_fields(self) -> None:
        result = redact("token=verysecretvalue Authorization: Bearer abc123", ["verysecretvalue"])
        self.assertNotIn("verysecretvalue", result)
        self.assertNotIn("abc123", result)
        self.assertIn("[REDACTED]", result)

    def test_ai_failure_clears_credential_and_does_not_send_it_as_context(self) -> None:
        credential_value = "temporary-ai-credential"
        credential = EphemeralCredential.create("openai", credential_value)
        report = RunReport(
            repository="sample",
            platform="Windows",
            project_type="Python",
            git=GitAnalysis(Path("."), "main", "abc", [], ""),
            checks=[],
            findings=[],
            risk=RiskAssessment(50, "medium", []),
        )

        class FailingProvider:
            def analyze(self, context: str, credential: str) -> str:
                self.context = context
                raise ProviderError("provider unavailable")

        provider = FailingProvider()
        with (
            patch.dict(os.environ, {"RECAP_PROVIDER": "openai"}, clear=True),
            patch("recap.core.orchestrator.CredentialManager.acquire", return_value=credential),
            patch("recap.core.orchestrator.resolve_provider", return_value=provider),
        ):
            _run_ai(report, json_output=True)
        self.assertEqual(credential._value, bytearray())
        self.assertNotIn(credential_value, provider.context)
        self.assertEqual(report.checks[0].status, "failed")
        self.assertNotIn(credential_value, report.checks[0].summary)

    def test_hosted_provider_rejects_plain_http_endpoint(self) -> None:
        with (
            patch.dict(os.environ, {"RECAP_HOSTED_URL": "http://example.invalid"}, clear=True),
            self.assertRaisesRegex(RecapError, "HTTPS"),
        ):
            HostedProvider().analyze("summary", "temporary-token")

    def test_hosted_tokens_are_signed_and_expire(self) -> None:
        signing_material = "a signing secret longer than thirty-two characters"
        with patch("server.hosted_ai.session_tokens.time.time", return_value=100):
            token = issue_session_token("test-user", signing_material, ttl_seconds=20)
        with patch("server.hosted_ai.session_tokens.time.time", return_value=110):
            self.assertTrue(verify_session_token(token, signing_material))
            self.assertFalse(verify_session_token(token + "x", signing_material))
        with patch("server.hosted_ai.session_tokens.time.time", return_value=121):
            self.assertFalse(verify_session_token(token, signing_material))


if __name__ == "__main__":
    unittest.main()
