---
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion, TaskCreate, TaskUpdate, TaskList, Agent
description: Stage 1 of v3.8 — turn free-form user intent into specs/_epic/spec.md (immutable high-level spec). Main session drives a revision loop where planner produces specs/_epic/_grill.html (toggle-based contract); user reviews in browser + pastes PLANNER REVISION / APPROVE blobs; main session re-spawns planner each round until APPROVE; planner then writes spec.md. Brownfield fact-finder dispatched by planner in parallel.
argument-hint: "[intent dump or path] [--no-grill] [--no-confirm] [--archetype <name>]"
model: opus
---

Invoke `.claude/skills/init-workflow/SKILL.md`. The skill owns the phases,
planner subagent dispatch, revision loop, fact-finder spawn logic, lint,
and final approval handoff. This command only routes control flow. When
command and skill disagree, the skill wins — fix this command.

1. **Pre-flight** — verify `specs/_epic/` does not exist or has been
   archived; abort if previous epic still live.

2. **Spawn planner `--produce-grill`** with the intent dump + flags.
   Planner runs stack discovery, draws best-guess answers for every
   toggle group, optionally dispatches fact-finder for brownfield,
   writes `specs/_epic/_grill.html`, and returns
   `GRILL READY: <path>`.

3. **Surface the grill to the user**:
   - Print the absolute path of `_grill.html`.
   - On darwin, call `open <path>` so the file launches in the default
     browser.
   - Tell the user: "review the toggles; when satisfied, click 'Copy as
     prompt — approve' and paste here. To revise instead, click 'Copy as
     prompt — revise' and paste here."

4. **Revision loop** (main session owns this loop, not the planner):
   - Wait for the user's next message.
   - Parse the first non-empty line:
     - Starts with `PLANNER REVISION:` → re-spawn planner
       `--produce-grill` with the full blob in the prompt. Planner
       regenerates `_grill.html`. Loop back to step 3.
     - Starts with `PLANNER APPROVE:` → exit loop, go to step 5.
     - Anything else → treat as free-form revision feedback, wrap it
       as a `PLANNER REVISION: \n- Free text: ...` blob, re-spawn
       planner. Loop back to step 3.
   - Hard cap: 12 revision rounds. After round 12 without APPROVE,
     surface a `BLOCKED` notice and offer the user the choice between
     abort or continue.

5. **Finalize** — spawn planner `--finalize` with the
   `PLANNER APPROVE:` blob in the prompt. Planner reads `_grill.html`
   + the blob, writes `specs/_epic/spec.md`, runs `spec_lint.py`, and
   returns `DONE: specs/_epic/spec.md (lint PASS; ...)`.

6. **Handoff** — print: `init complete. Epic: <slug>. Sprints: N planned.
   Next: /loop`. The pre-commit hook (`block_pretool.py`) now rejects any
   further Write/Edit on `spec.md` from generator / evaluator / fact-
   finder. `/loop` can begin.

### `--no-grill` short-circuit

When the user invokes `/init --no-grill`, skip steps 3-4 (no
browser-review loop). After step 2 produces `_grill.html`, immediately
re-spawn planner `--finalize` with planner's own recommended choices as
the auto-approve blob. The HTML stays as audit trail. Use only for CI /
scripted re-creation.

### `--no-confirm` no longer exists

The dual-flag `--no-grill --no-confirm` from v3.8.0 is replaced by
`--no-grill` alone; there is no "skip grill but keep confirm" mode (the
confirm step IS the grill loop under the new design). Backwards-compat
shim: if a script passes `--no-confirm` without `--no-grill`, treat as
`--no-grill` and emit a one-line deprecation warning.

Next step: /loop
