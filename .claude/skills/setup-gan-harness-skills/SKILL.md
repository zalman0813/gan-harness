---
name: setup-gan-harness-skills
description: One-time bootstrap that scaffolds the gan-harness substrate into a target project — copies the .claude/ tree, injects an ## Agent skills block into CLAUDE.md or AGENTS.md, chain-calls stack-skill-creator for each detected stack, and wires produced stack skill names into planner / generator / evaluator frontmatter `skills:` lists. Pocock-style 5-step flow (Explore / Ask one-at-a-time / Confirm / Write / Done). Lazy-creates CONTEXT.md / CODEMAP.md / docs/adr/ on demand by downstream stages, never preempts. Use when the user runs this skill to initialize a fresh target project for gan-harness.
disable-model-invocation: true
---

# Setup gan-harness skills

One-time bootstrap. Drop a fresh target repo into the state where
`/prd → /plan → /execution-loop → /finalize` works out of the box.

This skill is **user-invoked only** (`disable-model-invocation: true`)
because it makes large, hard-to-undo writes (copies a `.claude/` tree
+ edits memory-loaded files like `CLAUDE.md`).

## Mandatory before starting

ASSUMPTIONS I'M MAKING:
1. <e.g., "the source path the user will give me is a clean gan-harness clone, not their working dev tree">
2. <e.g., "this Claude Code session's cwd IS the target repo">
3. <e.g., "the target repo is a git repo (so we can read `git remote`)">
→ Correct me now or I'll proceed with these.

If the user invokes me from inside the gan-harness source repo by
mistake (target == source), ABORT with diagnostic. I write to target,
not to myself.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "User didn't choose, sane default is fine" | For load-bearing decisions (stack, layout, memory file), ask. For purely cosmetic, default may be fine but say which I picked. |
| "This file might be needed later, I'll create a stub now" | Lazy creation. No empty stubs for `CONTEXT.md` / `CODEMAP.md` / `docs/adr/index.md` — producer creates on first real content. |
| "User's edits to `README.md` / `CLAUDE.md` look wrong" | Not my call to revise. They own per-project decisions. I only inject the `## Agent skills` block; I never touch surrounding sections. |
| "Stack detection found nothing, I'll guess from filenames" | No. If detection is empty, surface that to the user and let them name the stack — or skip stack wiring entirely. Inventing a stack creates a wrong skill that drifts forever. |
| "Section walk is tedious; I'll bulk-ask everything in one prompt" | No. One `AskUserQuestion` per section, with explainer first. The interactive cadence IS the contract; bulk-ask collapses it. |
| "Agent frontmatter edit is mechanical; I'll inline the change without a script" | Use `wire_stack_skills.py`. Mechanical edits go through the script so behaviour is reproducible and testable. |

## When to use

- A fresh target repo (or one without `.claude/`) needs gan-harness
- The user explicitly invokes `/setup-gan-harness-skills` (this skill is
  not auto-loaded)

## When NOT to use

- Target already has a populated `.claude/` from a prior gan-harness setup
  — manual edits, not a re-run, are the right path
- Mid-batch (`specs/_batch/` non-empty) — finish or abort the batch first
- The user is inside the gan-harness source repo itself

## Inputs

- **Source path** (asked from user via AskUserQuestion in Section B) —
  absolute path to a gan-harness clone. The skill reads `.claude/`,
  `README.md` excerpt, and validates this path looks like gan-harness
  (presence of `docs/maintainer/design/agent-prompt-doctrine.md`).
- **Target path** = `$PWD` of the Claude Code session.
- **Templates** under `.claude/skills/setup-gan-harness-skills/templates/`:
  - `README.template.md`
  - `claude-md-skills-block.template.md`

## Outputs (target side)

After successful run:

- `target/.claude/` — full copy of source `.claude/` minus exclusions
  (`setup-gan-harness-skills/` itself, `__pycache__`, `.DS_Store`)
- `target/README.md` — from template (only if target had none)
- `target/CLAUDE.md` or `target/AGENTS.md` — `## Agent skills` block
  injected (created if neither existed; updated in-place if one did)
- `target/.claude/skills/<stack-name>/` × N — one per confirmed stack,
  produced by chain-called stack-skill-creator
- `target/.claude/agents/{planner,generator,evaluator}.md` — frontmatter
  `skills:` list extended with each new stack name
- `target/specs/_batch/.gitkeep`, `target/specs/completed/.gitkeep`

NOT created (lazy by downstream stages):
- `target/CONTEXT.md` (created at first /finalize archive merge)
- `target/CODEMAP.md` (created at first /finalize regen)
- `target/docs/adr/` (created at first /plan when planner writes an ADR)

## Process

### Phase 1 — Explore (silent)

Run preflight to gather state:

```
python3 .claude/skills/setup-gan-harness-skills/scripts/preflight.py \
    --target "$PWD"
```

Outputs env-style key=value lines:
- `IS_GIT=true|false`
- `GIT_REMOTE=<url or empty>`
- `HAS_CLAUDE_MD=true|false`
- `HAS_AGENTS_MD=true|false`
- `HAS_DOT_CLAUDE=true|false`
- `HAS_README=true|false`
- `BATCH_NON_EMPTY=true|false`  ← non-trivial collision

If `BATCH_NON_EMPTY=true` → ABORT immediately with:
"specs/_batch/ has live batch artefacts. Finish /finalize or remove
the batch before re-running setup."

If `HAS_DOT_CLAUDE=true` → ABORT:
"target already has .claude/. setup is for fresh targets; manual edits
are the right path for an existing setup."

### Phase 2 — Ask one section at a time

Walk these in order. Each section starts with a one-sentence explainer
the user can act on without reading docs.

#### Section A — Source path

> Setup needs to read gan-harness's `.claude/` tree to copy it here.
> Where is your gan-harness clone?

`AskUserQuestion(header="Source", question="Absolute path to gan-harness clone?")`.
Free-text answer.

Validate: `<source>/docs/maintainer/design/agent-prompt-doctrine.md` exists.
If not, re-ask ("That doesn't look like a gan-harness checkout — try again
or Cancel.").

#### Section B — Project identity

> The README.md template needs a project name and one-line description.
> These appear at the top of the README and in the `## Agent skills` block.

Two AskUserQuestion calls (one per field): `name` (kebab-case slug) and
`one_line_description`.

#### Section C — Memory file

> Claude Code reads either `CLAUDE.md` or `AGENTS.md` (never both) at
> session start to learn project context. Setup will inject an
> `## Agent skills` block describing the gan-harness pipeline.

Branch on Phase 1's `HAS_CLAUDE_MD` / `HAS_AGENTS_MD`:
- both false → AskUserQuestion: "Create CLAUDE.md or AGENTS.md?"
- one exists → use it (no question; tell user "I'll edit your existing X.md")
- both exist → ABORT (Pocock rule: never have both; ask user to pick one
  manually before re-running)

#### Section D — Stacks (detect + chain-call)

Run stack detection:

```
python3 .claude/skills/setup-gan-harness-skills/scripts/detect_stacks.py \
    --target "$PWD"
```

Output: JSON list of `{manifest, suggested_skill_name, evidence}`.

For each detected stack, AskUserQuestion:
- **Confirm** — chain-call stack-skill-creator with the suggested name
- **Rename** — user provides corrected skill name; chain-call with that
- **Skip** — don't build a stack skill for this manifest

If detection found zero manifests, AskUserQuestion: "No stack detected.
Skip stack wiring for now (you can run stack-skill-creator manually
later) / Force a stack name (advanced)?".

For each confirmed/renamed stack:

```
Skill(skill="stack-skill-creator", args="--name=<stack-name> --target=$PWD")
```

Wait for it to return. Collect all produced stack skill names into
`STACKS_TO_WIRE` for Phase 4.

### Phase 3 — Confirm (show drafts)

Show the user a single confirmation block:

```
Ready to write to <target>:

  README.md           : <new from template / skip — already exists>
  CLAUDE.md           : <inject ## Agent skills block>
  .claude/            : copy from <source>/.claude/ (excluding setup-gan-harness-skills/)
  Stack skills        : <list of names from Section D>
  Wire stacks into    : agents/{planner,generator,evaluator}.md `skills:`
  Empty containers    : specs/_batch/.gitkeep, specs/completed/.gitkeep

Approve / Edit / Abort
```

`AskUserQuestion`. On Edit, surface a sub-question (which item to tweak)
and loop. On Abort, exit cleanly with no writes.

### Phase 4 — Write

Run in order. Stop on first error.

#### 4a. Copy substrate

```
bash .claude/skills/setup-gan-harness-skills/scripts/copy_substrate.sh \
    --src <source> \
    --dst "$PWD"
```

Copies `.claude/` from source, with exclusions hard-coded in the script.
Idempotent: skips files already at destination (Phase 1 guarantees no
`.claude/` collision, but the script defends anyway).

#### 4b. README.md (if not present)

If `HAS_README=false`, render
`.claude/skills/setup-gan-harness-skills/templates/README.template.md`
with `{{project_name}}` and `{{one_line_description}}` substituted.
Write to `$PWD/README.md`.

If `HAS_README=true`, skip (the user owns their README).

#### 4c. Memory file `## Agent skills` block

Render
`.claude/skills/setup-gan-harness-skills/templates/claude-md-skills-block.template.md`
with `{{project_name}}` substituted. Then:

- If a `## Agent skills` section already exists in the chosen memory
  file (`CLAUDE.md` or `AGENTS.md`), update it in-place. Do not touch
  surrounding sections.
- Else append the rendered block at the end of the file.
- If neither memory file exists, create the chosen one with frontmatter
  + the rendered block.

This MUST preserve user edits to other sections of the file.

#### 4d. Wire stack skills into agent frontmatter

```
python3 .claude/skills/setup-gan-harness-skills/scripts/wire_stack_skills.py \
    --agents-dir "$PWD/.claude/agents" \
    <stack-name-1> <stack-name-2> ...
```

The script edits frontmatter `skills:` of `planner.md`, `generator.md`,
`evaluator.md`. Idempotent (won't double-add). Skips
`codebase-fact-finder.md` (stack-agnostic blindfold research).

If `STACKS_TO_WIRE` is empty (Section D entirely skipped), no-op.

#### 4e. Empty container sentinels

```
mkdir -p specs/_batch specs/completed
touch specs/_batch/.gitkeep specs/completed/.gitkeep
```

### Phase 5 — Done

Print final report:

```
═══════════════════════════════════════════════════════════════
setup-gan-harness-skills complete — <project_name>
═══════════════════════════════════════════════════════════════

Wrote .claude/                        ✓
Wrote README.md                       <✓ / skipped — existed>
Updated <CLAUDE.md|AGENTS.md>         ✓ (## Agent skills block)
Built stack skills                    <list or "none">
Wired stacks into agent frontmatter   <✓ / skipped — no stacks>
Sentinels                             specs/{_batch,completed}/.gitkeep

Lazy (will be created when first needed):
  CONTEXT.md      ← first /finalize archive merge
  CODEMAP.md      ← first /finalize regen
  docs/adr/       ← first /plan ADR proposal

Next: /prd  (start your first batch)
═══════════════════════════════════════════════════════════════
```

## Anti-patterns

- **Copying setup-gan-harness-skills itself to the target.** It's
  bootstrap-only; copy_substrate.sh excludes it. Never weaken that
  exclusion.
- **Pre-creating `CONTEXT.md` / `CODEMAP.md` / `docs/adr/`.** Lazy
  per locked decision. Stubs are lies.
- **Editing surrounding sections of an existing CLAUDE.md / AGENTS.md /
  README.md.** Setup only owns the `## Agent skills` block (and a fresh
  README from template if missing). Anything else is the user's.
- **Using both CLAUDE.md AND AGENTS.md.** Pocock rule: pick one. Setup
  refuses to proceed if both exist (manual cleanup needed first).
- **Bulk-asking all sections at once.** Walk one-at-a-time, each with
  explainer first. The walk IS the UX contract.
- **Inventing a stack when detection finds nothing.** Skip wiring;
  surface to user. A wrong stack skill drifts forever.

## Done when

- [ ] Phase 1 preflight clean (no live batch, no `.claude/` collision)
- [ ] Sections A–D walked; each answer recorded
- [ ] Phase 3 confirm Approve received
- [ ] `.claude/` copied (minus setup-gan-harness-skills, `__pycache__`)
- [ ] README.md present (template-rendered or pre-existing)
- [ ] CLAUDE.md or AGENTS.md has `## Agent skills` block
- [ ] Stack skills (if any) built + wired into agent frontmatter
- [ ] `specs/_batch/.gitkeep` + `specs/completed/.gitkeep` present
- [ ] Final report printed; `/prd` suggested
