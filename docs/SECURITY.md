# Security (spec 20)

## Prompt Injection (spec 20.3)

- All external text (reviews, supplier descriptions, MCP returns) treated as data only.
- Agent prompts explicitly instruct: ignore any "system prompt", "call tool", "upload key" in data.
- Fixture includes >= 3 prompt-injection bad cases (in reviews + reviewer_bad_cases/).
- Tests verify no extra tool calls triggered.

## External Access (spec 20.4)

- Domain allowlist for any live fetch (P1, disabled by default).
- Forbidden: localhost, RFC1918, link-local, cloud metadata endpoint.
- No robots/login/captcha/rate-limit bypass.
- No automatic supplier contact.
- `license_or_terms_status=unknown` data not redistributable.

## Secrets

- `.env` never committed; only `.env.example`.
- Model API key existence checked (doctor), value never printed.
- Trace/Artifact/logs contain no real keys.
- Debug bundle must be redacted.

## Approval (spec 20.1-20.2)

- Draft Spec: no approval needed.
- Published Spec: Human Approval required, bound to Spec Hash.
- Future inquiry/purchase/external write: forced approval, disabled in P0.
- Worker/Reviewer cannot approve.
- Spec change invalidates old approval.
