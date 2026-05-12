---
name: init-workflow
description: Drive Stage 1 of the gan-harness v3.8 — turn free-form user intent into specs/_epic/spec.md (immutable high-level spec) plus optional fact-finder research, ready for /loop to consume. Replaces v1's prd-workflow + plan-workflow combo. Make sure to use this skill whenever /init runs, when the user asks to start a new epic, or when handoff to /loop needs a finalized spec.md and tech-stack confirmation.
disable-model-invocation: false
---

# init-workflow

Stage 1 of v3.8. Single skill, single agent (planner), single human
checkpoint. Replaces the v1 two-stage `/prd` + `/plan` combo because that
combo was producing over-prescribed specs that downstream agents couldn't
work around.

## Mandatory before starting

ASSUMPTIONS I'M MAKING:
1. The user has provided an intent dump (free-form text) and a target tech
   stack (or wants the planner to grill for it).
2. `specs/_epic/` does not yet exist (or has been archived from the
   previous epic). If it exists with content, ABORT — `/finalize` must
   run first to archive the previous epic.
3. The relevant stack skill already exists at `.claude/skills/<stack>/`.
   If not, the user needs to run `stack-skill-creator` first.

## Common rationalisations

| Rationalization | Reality |
|---|---|
| "Specs/_epic/ has stale content from a prior session, I'll just overwrite" | No. stale content = the prior epic didn't archive cleanly. Run /finalize on it first. |
| "The user said 'no grill', so I won't ask anything" | --no-grill means trust the dump as-is, but you still verify schema-required fields exist (archetype, success criteria). If the dump is missing them, surface back to user — don't silently make them up. |
| "The user gave a frontend prompt but I think backend criteria are better" | Archetype follows the user's intent; if you disagree, raise it as a question, not a unilateral decision. |
| "I'll write the spec inline and skip lint" | spec_lint MUST pass before checkpoint. Lint failure = the spec violates the contract; it can't be approved. |
| "I'll skip fact-finder for this brownfield because the codebase is small" | Brownfield always uses fact-finder. The blindfold pattern is what keeps planner-bias out of research. |

## Inputs

- User intent dump (free-form text; from the slash command's `$ARGUMENTS`).
- Optional flags from the user: `--no-grill`, `--no-confirm`, `--archetype <name>`.
- `CONTEXT.md` (existing domain language).
- `docs/adr/index.md` (existing accepted architectural decisions).
- `specs/epics/` (recent archived epics for context, optional).
- For brownfield only: existing source code (read-only access; fact-finder
  subagents do this in parallel with blindfold protocol).

## Process

### Phase 0 — Pre-flight

1. If `specs/_epic/` exists with content, ABORT with: "previous epic
   not archived; run /finalize first".
2. Create `specs/_epic/` directory.
3. Parse user flags: `--no-grill`, `--no-confirm`, `--archetype <name>`.

### Phase 1 — Spawn planner agent

The planner agent (auto-loads `planner-handbook`, `adr-lifecycle`) does
the actual work. Pass it the intent dump and any flags. Note: planner
does NOT load `deep-module-handbook` in v3.8 — module-level cognition
is a /loop sprint-contract concern handled by generator and evaluator,
not planner.

The planner will:
- Grill the user via `AskUserQuestion` (unless `--no-grill`).
- Optionally spawn `codebase-fact-finder` subagents in parallel (only for
  brownfield; greenfield skips).
- Draft `specs/_epic/spec.md` per the schema at
  `.claude/schemas/spec.schema.md`.
- Self-verify with `python .claude/skills/init-workflow/scripts/spec_lint.py
  specs/_epic/spec.md`. Iterate until PASS.
- Optionally write `docs/adr/NNNN-*.md` with `status: proposed` (rare).

### Phase 2 — Final approval checkpoint

Unless `--no-confirm` is set, present the spec.md to the user via
`AskUserQuestion` with three options:

- **Approve** → spec is locked. Hook (`block_pretool.py`) will reject
  any further Write/Edit on `specs/_epic/spec.md` from generator /
  evaluator / fact-finder. /loop can begin.
- **Revise** → planner re-engages with the user's specific feedback,
  re-drafts, re-lints. Loops back to Phase 2.
- **Abort** → delete `specs/_epic/`, exit cleanly.

### Phase 3 — Hand off

Write a one-line summary to stdout:
```
init complete. Epic: <slug>. Sprints: N planned. Next: /loop
```

## Outputs

- `specs/_epic/spec.md` — the immutable spec.
- `specs/_epic/_research/<query-id>.md` × N — only for brownfield epics.
- `docs/adr/NNNN-*.md` × M — only when ADR-worthy decisions emerged.
  `status: proposed`. Promoted at `/finalize`.

That's all. No `feature-list.json`. No granular AC. No per-sprint
contract. Those come from `/loop`.

## Anti-patterns

**Producing a spec that fails lint.** The spec must PASS `spec_lint.py`
before it can be approved. If lint flags an issue, fix it; don't
"override".

**Skipping the human checkpoint when the user didn't explicitly
opt-in.** `--no-confirm` is opt-in. Default is one human checkpoint.

**Filling in archetype/criteria from training priors.** If the dump
doesn't say what archetype, ask. If the dump doesn't say success
criteria, ask. The planner-handbook lists the 5 questions you must
resolve.

**Skipping fact-finder for brownfield.** Blindfold research is what
keeps planner-bias out of code-state observation. If brownfield, always
dispatch.

**Writing prd.md or feature-list.json.** Those are v1 artefacts. v3.8
has spec.md only.

## Scripts

- `scripts/spec_lint.py <path>` — validates spec.md against L01-L07.
  Exit 0 on PASS; exit 1 with JSON-on-stderr findings on FAIL.
