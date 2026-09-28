# Release Captain (`recap`)

`recap` is a local-first Python CLI that inspects a Git repository, inventories supported dependency manifests, performs a heuristic hard-coded-secret scan, optionally runs project tests, calculates an explainable risk score, and prepares a human-reviewed release plan.

## Install and run

Requires Python 3.11+ and Git.

```powershell
python -m pip install .
recap
```

Or from a source checkout:

```powershell
python -m pip install -e .
python -m recap
```

Use `recap --help` for command options. The normal entry point is `recap`. Advanced CI options include `--json` for a non-interactive JSON report and `--no-ai` to opt out of AI. AI is only considered when local analysis finds a medium/high risk or a failed check. Provider choice and credentials are requested only on that path.

## Tests and trust boundary

In an interactive run, `recap` asks before running the detected project test command. You can also pass `--run-tests`. This executes repository-controlled code with the current user's permissions. **The current implementation does not provide an OS-level sandbox**; do not run tests from an untrusted repository. Test commands use argument arrays, a timeout, a constrained environment, and no shell, but these are not a security sandbox.

The local secret scanner is heuristic: it reports file/line and rule, never the matched value. It is not a complete secret detector. Large, unreadable, or non-UTF-8 files are reported as uninspected rather than treated as clean. Dependency inventory parses supported manifests but does not query an advisory database or claim that dependencies are vulnerability-free.

## Ephemeral AI credentials

No API key or hosted session token is saved by the CLI to configuration files, `.env`, project state, an OS credential store, a database, or an environment variable that the CLI creates. For interactive use, the credential prompt uses `getpass` and occurs only when AI is needed. A new `recap` process requests credentials again.

Supported providers:

- OpenRouter — `RECAP_OPENROUTER_API_KEY`
- OpenAI — `OPENAI_API_KEY`
- Anthropic — `ANTHROPIC_API_KEY`
- Hosted service — `RECAP_HOSTED_TOKEN` and `RECAP_HOSTED_URL`

In non-interactive CI, set `RECAP_PROVIDER` and the corresponding secret through the CI platform's secret mechanism. `recap` reads the inherited value for that invocation and does not pass it to test subprocesses. For example, configure these variables in the CI job's secret/environment settings; do not place real values in workflow files. `--json` does not prompt. Missing non-interactive credentials are reported as errors when an AI provider has explicitly been selected.

The CLI clears its mutable credential buffer in a `finally` block. Python and HTTP libraries can make immutable in-memory copies; reliable forensic zeroization cannot be guaranteed. Avoid shell arguments for secrets, enable CI log masking, and never enable HTTP wire/debug logging around provider requests.

## Hosted AI service

The optional service is a minimal stdlib HTTP server that accepts signed short-lived session tokens (15 minutes by default), limits request size and per-client request rate, and uses an upstream OpenRouter key held only in the server process environment. It does not include account login, token delivery, persistent rate-limit storage, or TLS termination; put it behind an authenticated account/token-issuance system and a TLS reverse proxy before exposing it publicly.

Configure the service process with `RECAP_HOSTED_SESSION_SECRET` (at least 32 characters) and `OPENROUTER_API_KEY`; optionally set `RECAP_HOSTED_BIND`, `RECAP_HOSTED_PORT`, and `RECAP_HOSTED_MODEL`. Defaults bind to loopback. The operator can issue a short-lived token for out-of-band delivery with:

```powershell
python -m server.hosted_ai.issue_token account-id
```

Do not expose the signing secret or upstream key to the CLI. Deploying the service publicly without TLS, identity integration, and production-grade distributed rate limiting is not supported.

## Release behavior and audit

The tool presents a release plan and requires explicit approval in an interactive session. No release target/adapter is configured in this initial implementation, so approval never publishes or mutates the repository; output states that no release occurred. Audit information is generated in memory and included in the output, not saved to disk. A real release backend and audit-retention policy must be selected before enabling release side effects or durable audit storage.

## Development and validation

```powershell
python -m pip install -e .
python -m unittest discover -s tests -v
```

The test suite does not call external AI providers. Provider API behavior is tested with mocked HTTP transport; hosted service integration requires separately configured credentials and should be exercised in a controlled deployment.
