from __future__ import annotations

import json
import os
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from server.hosted_ai.app import HostedAIHandler
from server.hosted_ai.session_tokens import issue_session_token


class HostedServerTests(unittest.TestCase):
    def test_authenticates_and_redacts_before_upstream_call(self) -> None:
        signing_secret = "hosted signing secret with at least thirty-two chars"
        upstream_secret = "server-upstream-private-key"
        session_token = issue_session_token("test-user", signing_secret)
        server = ThreadingHTTPServer(("127.0.0.1", 0), HostedAIHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_address[1]}/v1/analyze",
                data=json.dumps({"summary": "api_" + "key=sample-private-value"}).encode(),
                headers={"Authorization": f"Bearer {session_token}"},
                method="POST",
            )
            fake_response = {"choices": [{"message": {"content": "review complete"}}]}
            with (
                patch.dict(
                    os.environ,
                    {
                        "RECAP_HOSTED_SESSION_SECRET": signing_secret,
                        "OPENROUTER_API_KEY": upstream_secret,
                    },
                ),
                patch("server.hosted_ai.app.post_json", return_value=fake_response) as upstream,
                urllib.request.urlopen(request, timeout=5) as response,
            ):
                payload = json.loads(response.read())
            self.assertEqual(payload, {"analysis": "review complete"})
            headers = upstream.call_args.args[1]
            sent_summary = upstream.call_args.args[2]["messages"][1]["content"]
            self.assertEqual(headers["Authorization"], f"Bearer {upstream_secret}")
            self.assertNotIn(session_token, str(headers))
            self.assertNotIn("sample-private-value", sent_summary)
            self.assertIn("[REDACTED]", sent_summary)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
