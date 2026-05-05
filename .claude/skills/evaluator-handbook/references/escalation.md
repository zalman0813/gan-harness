# Escalation — when an agent needs human help

Both generator and evaluator can hit failures that no amount of code
change will fix — expired auth, missing local config, external service
unreachable. The harness has a structured way to surface these to the
operator (the human running `/execution-loop`) without polluting the
verdict semantics.

## When to escalate (vs FAIL)

The classification heuristic: **would the same code pass on a freshly
prepared dev box?**

- Yes (a teammate could clone, set up env, and the test would pass) → it's
  a human / env block. **Escalate.**
- No (the test would fail anywhere, regardless of env) → it's a code
  defect. **FAIL** as normal.

Concrete examples:

| Symptom | Class | Action |
|---|---|---|
| `STS GetCallerIdentity` returns "expired token" | env | escalate `auth-required` |
| Playwright cannot connect to `localhost:3000` (server didn't start) — and the server's failure is due to missing `.env` | env | escalate `missing-config` |
| Playwright cannot connect because `playwright.config.ts` has no `webServer` block | code | FAIL — generator misconfigured the e2e setup |
| Test asserts `<button data-testid="submit">` but generator wrote `<button id="submit">` | code | FAIL — selector mismatch |
| `pnpm install` fails with `ENETUNREACH` to npm registry | env | escalate `service-unreachable` |
| API call returns 401 because the spec assumed a session cookie not yet implemented | code | FAIL |

When in doubt: **prefer FAIL**. False-FAIL costs an R2 round; false-escalate
costs the operator's attention. Operator attention is the more expensive
resource.

## File to write

```
specs/_batch/_escalations/F{NN}-{gen|eval}-R{N}.json
```

Schema:

```json
{
  "kind": "auth-required",
  "what_blocked": "L5 smoke for AC-23 cannot run: STS GetCallerIdentity returned 'expired token'. The page under test fetches /api/monitor/blocked which goes through STS-backed DynamoDB; without valid creds the smoke produces 'CredentialsError', not a code-attributable assertion failure.",
  "human_action": "Run `saml2aws login --profile <your-profile>` in another terminal, then click Done. The evaluator will re-spawn and retry L5 with the refreshed creds.",
  "auto_resume": true
}
```

Field meanings:

- `kind` — one of: `auth-required`, `service-unreachable`, `missing-config`,
  `manual-data-fixture`, `other`. Used by harness-loop to group similar
  escalations and (eventually) to power retry policies.
- `what_blocked` — concrete description of what failed and why it's env
  rather than code. Cite the actual error string you saw.
- `human_action` — exactly what the operator must do, written for someone
  who is paged at 2am. Include the command, the expected confirmation, and
  what happens after they click "Done".
- `auto_resume: true` — the harness will re-spawn this agent at the same
  round (no round counter increment) once the operator confirms. Use
  `false` only if re-running this agent makes no sense even after the
  human action — rare; usually `true`.

## What happens after you write it

You stop. Return without verdict / without commit. The harness-loop's
escalation handler:

1. Reads the file
2. Asks the operator via AskUserQuestion: `[<kind>] <what_blocked> · <human_action>` — options "Done", "Skip this feature", "Abort batch"
3. On **Done**: deletes the escalation file, re-spawns you (same agent
   type, same feature, same round). The re-spawn is a fresh-context
   subagent, so include enough detail in the file that the next
   instance can pick up immediately.
4. On **Skip**: feature → `deferred` with note `operator-skipped: <kind>`. Cascade applies to downstream features.
5. On **Abort**: batch exits.

## Discipline

- One escalation per agent run. If you find two env blocks, fix the
  description to cover both, return one file. Spamming files defeats
  the operator's signal-to-noise ratio.
- No escalation for "unsure if env or code". If you can't decide, FAIL
  with the unsure call documented; let R2 generator either fix or
  surface the env block more clearly.
- Don't escalate for things you control. "I don't have time to write
  more probes" is not an escalation; it's a verdict.
- The escalation file is **machine-read first** by the harness-loop, but
  also human-readable. Write `human_action` as if posting to a
  team-runbook channel — not as a stack trace.
