---
name: escalation
description: Shared schema and protocol for writing specs/_batch/_escalations/F{NN}-{gen|eval}-R{N}.json when env (not code) blocks an agent. Loaded by generator and evaluator on demand when they hit a human-fixable env block — auth expired, missing local config, external service unreachable, port collision.
---

# Escalation

When env blocks the work and no code change can fix it, write an escalation file and stop. The harness-loop reads the file, asks the operator, and re-spawns the agent on confirmation.

## When to escalate (vs FAIL)

Classification heuristic: **would the same code pass on a freshly prepared dev box?**

- Yes (a teammate could clone, set up env, and the test would pass) → env block → **escalate.**
- No (the test would fail anywhere, regardless of env) → code defect → **FAIL** as normal.

When in doubt, prefer FAIL. False-FAIL costs an R2 round; false-escalate costs operator attention — operator attention is the more expensive resource.

## File path

```
specs/_batch/_escalations/F{NN}-{gen|eval}-R{N}.json
```

`{gen|eval}` matches the agent type writing the file. One file per (agent, feature, round).

## Schema

```json
{
  "kind": "auth-required",
  "what_blocked": "L5 smoke for AC-23 cannot run: STS GetCallerIdentity returned 'expired token'. The page under test fetches /api/x backed by STS+DDB; without credentials the smoke produces CredentialsError, not a code-attributable assertion failure.",
  "human_action": "Run `saml2aws login --profile <your-profile>` in another terminal, then click Done. The agent re-spawns at the same round and retries with refreshed credentials.",
  "auto_resume": true
}
```

Fields:

- `kind` — one of `auth-required` / `service-unreachable` / `missing-config` / `manual-data-fixture` / `other`. Used by harness-loop to group similar escalations.
- `what_blocked` — concrete description of what failed and why it's env not code. Cite the actual error string you saw.
- `human_action` — exactly what the operator must do, written for someone paged at 2am: command, expected confirmation, what happens after Done.
- `auto_resume: true` (default) — re-spawn same agent / same feature / same round on Done. The re-spawn is a fresh-context subagent — write `what_blocked` with enough detail that the next instance can pick up.
- `auto_resume: false` — only when re-running this agent makes no sense even after the human action. Rare.

## What happens after you write it

You stop. Return without verdict / without commit. The harness-loop:

1. Reads the file.
2. Asks the operator via AskUserQuestion: `[<kind>] <what_blocked> · <human_action>` — options "Done", "Skip this feature", "Abort batch".
3. On **Done**: deletes the escalation file, re-spawns same agent / same round (counter NOT incremented).
4. On **Skip**: feature → `deferred` with note `operator-skipped: <kind>`.
5. On **Abort**: batch exits.

## Discipline

- One escalation per agent run. Two env blocks → one file covering both, not two files.
- Don't escalate for things you control. "I don't have time to write more probes" is a verdict, not an escalation.
- Don't escalate when uncertain whether it's env or code. If you can't decide, FAIL with the uncertainty documented.
- Write `human_action` as a runbook entry, not a stack trace.
