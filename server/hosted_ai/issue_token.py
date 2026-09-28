from __future__ import annotations

import argparse
import os

from server.hosted_ai.session_tokens import issue_session_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a short-lived hosted-AI session token.")
    parser.add_argument("subject", help="Account/user identifier")
    parser.add_argument("--ttl", type=int, default=900, help="Lifetime in seconds (max 3600)")
    args = parser.parse_args()
    secret = os.environ.get("RECAP_HOSTED_SESSION_SECRET", "")
    token = issue_session_token(args.subject, secret, args.ttl)
    print(token)


if __name__ == "__main__":
    main()
