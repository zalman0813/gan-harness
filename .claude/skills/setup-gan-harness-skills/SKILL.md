---
name: setup-gan-harness-skills
description: One-time bootstrap that scaffolds the gan-harness substrate into a target project — copies the .claude/ tree, injects a minimal ### Domain docs block into CLAUDE.md or AGENTS.md, chain-calls stack-skill-creator for each detected stack, and wires produced stack skill names into planner / generator / evaluator frontmatter `skills:` lists. Pocock-style 5-step flow (Explore / Ask one-at-a-time / Confirm / Write / Done). Lazy-creates CONTEXT.md / CODEMAP.md / docs/adr/ on demand by downstream stages, never preempts. Use when the user runs this skill to initialize a fresh target project for gan-harness.
disable-model-invocation: true
---

# Setup gan-harness skills

One-time bootstrap. Drop a fresh target repo into the state where
`/init → /loop → /finalize` works out of the box (v3.8).

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
| "User's edits to `README.md` / `CLAUDE.md` look wrong" | Not my call to revise. They own per-project decisions. I only inject the `### Domain docs` block; I never touch surrounding sections. |
| "Stack detection found nothing, I'll guess from filenames" | No. If detection is empty, surface that to the user and let them name the stack — or skip stack wiring entirely. Inventing a stack creates a wrong skill that drifts forever. |
| "Section walk is tedious; I'll bulk-ask everything in one prompt" | No. One `AskUserQuestion` per section, with explainer first. The interactive cadence IS the contract; bulk-ask collapses it. |
| "Agent frontmatter edit is mechanical; I'll inline the change without a script" | Use `wire_stack_skills.py`. Mechanical edits go through the script so behaviour is reproducible and testable. |
| "Add a Pipeline / Conventions / Stack section so the main-session Claude knows what /init /loop etc. do and what gan-harness conventions are" | NO. The block is intentionally minimal (3 bullets pointing at CONTEXT.md / docs/adr/ / CODEMAP.md). Slash commands self-document via SKILL.md when invoked; subagents auto-load their own handbooks; main-session Claude can grep `.claude/commands/`. Pre-explaining bloats CLAUDE.md without giving Claude actionable context. |
| "User asked me to add a principle to `## Principles` section; I'll write it however reads naturally" | NO. Use the Karpathy 5-element format (see § Principle format below). Ad-hoc principle structures rot — they accumulate inconsistencies that make the section unreadable as it grows. The 5 elements (numbered heading / tagline / paragraph / bullets / "The test:" sentence) are non-negotiable. |

## Principle format

When the user asks to add or edit a principle in any project's CLAUDE.md `## Principles` section, follow the Karpathy 5-element format (source: <https://github.com/forrestchang/andrej-karpathy-skills>):

1. `### N. Title` — numbered heading. Increment monotonically; never reuse a number even if a principle is removed (so `git log -S "### 3. "` always finds history).
2. `**Tagline**` — one line, bold, imperative. Should fit on a single line and convey the rule independently.
3. **Explanatory paragraph** — rationale + cost of violating + when it applies. 2–4 sentences. Names the concrete consequence the rule prevents.
4. **4–5 bullets** — concrete actionable directives, each atomic and grep-able. Bullets describe the FORBIDDEN action or the REQUIRED action; not abstract advice.
5. **`The test: …`** — a yes/no self-check Claude can run while writing code. If you can't write a "The test:" sentence for the principle, the principle isn't operational — refine until you can.

**Anti-rationalization**: any principle missing the "The test:" sentence is a slogan, not a rule. Refuse to write a slogan-only principle; either complete the 5 elements or surface as `open_question` to the user.

**Where this format lives at runtime**: each project's `CLAUDE.md` `## Principles` section opens with a `> Format for adding new principles: ...` block-quote preamble that mirrors this. The preamble is per-project (lives in target's CLAUDE.md, not in the injected template) so principles can grow project-by-project without setup re-injection.

## When to use

- A fresh target repo (or one without `.claude/`) needs gan-harness
- The user explicitly invokes `/setup-gan-harness-skills` (this skill is
  not auto-loaded)

## When NOT to use

- Target already has a populated `.claude/` from a prior gan-harness setup
  — manual edits, not a re-run, are the right path
- Mid-epic (`specs/_epic/` non-empty) — finish or abort the epic first
- The user is inside the gan-harness source repo itself

## Inputs

- **Source path** (asked from user via AskUserQuestion in Section B) —
  absolute path to a gan-harness clone. The skill reads `.claude/`,
  `README.md` excerpt, and validates this path looks like gan-harness
  (presence of `<source>/.claude/skills/setup-gan-harness-skills/SKILL.md`
  — that skill is bootstrap-only and excluded from target copies, so
  its presence uniquely identifies a source checkout).
- **Target path** = `$PWD` of the Claude Code session.
- **Templates** under `.claude/skills/setup-gan-harness-skills/templates/`:
  - `README.template.md`
  - `claude-md-skills-block.template.md`

## Outputs (target side)

After successful run:

- `target/.claude/` — full copy of source `.claude/` minus exclusions
  (`setup-gan-harness-skills/` itself, `__pycache__`, `.DS_Store`)
- `target/README.md` — from template (only if target had none)
- `target/CLAUDE.md` or `target/AGENTS.md` — `### Domain docs` block
  injected (created if neither existed; updated in-place if one did)
- `target/.claude/skills/<stack-name>/` × N — one per confirmed stack,
  produced by chain-called stack-skill-creator
- `target/.claude/agents/{planner,generator,evaluator}.md` — frontmatter
  `skills:` list extended with each new stack name
- `target/.git/hooks/pre-commit` — the harness gate, the SOLE enforcement
  point for lint/typecheck/test/ac_coverage on every `git commit`
- `target/specs/_epic/.gitkeep`, `target/specs/epics/.gitkeep`

NOT created (lazy by downstream stages):
- `target/CONTEXT.md` (created at first /finalize archive merge)
- `target/CODEMAP.md` (created at first /finalize regen)
- `target/docs/adr/` (created at first /init when planner writes an ADR)

## Invocation context (interactive vs subagent)

This skill runs in one of two contexts. The two branches differ in how
user input is gathered; the file writes in Phase 4 are identical.

**Interactive mode** — invoked in a main-session Claude with the
`AskUserQuestion` and `Skill` tools available (the normal `/setup-…`
flow). Walk Sections A–D one-at-a-time with `AskUserQuestion`. Build
stack skills in 4b via Mode 1 (`Skill` chain-call to
stack-skill-creator).

**Subagent mode** — invoked as a `general-purpose` or similar subagent
that does NOT have `AskUserQuestion` or `Skill` tools. The operator's
prompt must pre-supply every answer the interactive walk would have
collected:

- Source path (gan-harness clone absolute path)
- Project name (kebab-case slug)
- One-line description
- Memory file choice (`CLAUDE.md` or `AGENTS.md`)
- Stack list (canonical names from Section D's table — operator names
  them explicitly; no detection-driven question loop)

If any of these is absent from the operator's prompt, ABORT with a
diagnostic listing what's missing. Do NOT invent defaults for
load-bearing decisions (stack identity, memory file).

For 4b in subagent mode, use Mode 2 (inline scaffold; see 4b below).

Both modes share Phase 1 preflight, Phase 4 writes, and Phase 5 done
report verbatim. The only differences are Phase 2 (gather inputs) and
4b (build mode).

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
- `EPIC_NON_EMPTY=true|false`  ← non-trivial collision

If `EPIC_NON_EMPTY=true` → ABORT immediately with:
"specs/_epic/ has live epic artefacts. Finish /finalize or remove
the epic before re-running setup."

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

Validate: `<source>/.claude/skills/setup-gan-harness-skills/SKILL.md`
exists. If not, re-ask ("That doesn't look like a gan-harness checkout
— try again or Cancel."). This marker is reliable because the
setup-gan-harness-skills directory is bootstrap-only and excluded from
target copies, so any well-formed target will NOT have it; only a
genuine source checkout will.

#### Section B — Project identity

> The README.md template needs a project name and one-line description.
> These appear at the top of the README. (The injected `### Domain docs`
> block is fixed content; it does not take the project name.)

Two AskUserQuestion calls (one per field): `name` (kebab-case slug) and
`one_line_description`.

#### Section C — Memory file

> Claude Code reads either `CLAUDE.md` or `AGENTS.md` (never both) at
> session start to learn project context. Setup will inject a minimal
> `### Domain docs` block pointing at CONTEXT.md / docs/adr/ / CODEMAP.md
> (3 bullets; no Pipeline / Conventions / Stack subsections — those are
> intentionally omitted; see Common Rationalizations).

Branch on Phase 1's `HAS_CLAUDE_MD` / `HAS_AGENTS_MD`:
- both false → AskUserQuestion: "Create CLAUDE.md or AGENTS.md?"
- one exists → use it (no question; tell user "I'll edit your existing X.md")
- both exist → ABORT (Pocock rule: never have both; ask user to pick one
  manually before re-running)

#### Section D — Stacks (detect-only, decisions collected for Phase 4)

**This section does NOT build any stack skill.** It only records the
user's stack decisions. Actual stack-skill creation happens in Phase 4b,
after `copy_substrate.sh` has built `target/.claude/skills/`. (Running
stack-skill-creator before 4a would write into `target/.claude/skills/`
and then 4a would ABORT because `target/.claude/` already exists.)

Run stack detection:

```
python3 .claude/skills/setup-gan-harness-skills/scripts/detect_stacks.py \
    --target "$PWD"
```

Output: JSON list of `{manifest, suggested_skill_name, evidence}`.

For each detected stack, AskUserQuestion:
- **Confirm** — record the suggested name for Phase 4b
- **Rename** — user provides corrected skill name; record that
- **Skip** — don't build a stack skill for this manifest

**Canonical stack skill names** (use these verbatim — `detect_stacks.py`
emits these from `suggested_skill_name`; if the user types a name, gently
nudge them to the canonical form when there's an obvious match):

| Stack | Canonical name |
|---|---|
| Python — stdlib library | `python-stdlib` |
| Python — CLI app (argparse / click / typer) | `python-cli` |
| Python — FastAPI service | `python-fastapi` |
| Python — Django service | `python-django` |
| Python — Flask service | `python-flask` |
| Python — data pipeline | `python-data` |
| Python — generic (no framework detected) | `python` |
| TypeScript — Next.js frontend | `typescript-nextjs` |
| TypeScript — React frontend | `typescript-react` |
| TypeScript — Node service | `typescript` |
| JavaScript — Express service | `javascript-express` |
| Go — generic | `go` |
| Go — Gin service | `go-gin` |
| Rust — generic | `rust` |
| Dart — Flutter app | `dart-flutter` |
| Ruby — Rails app | `ruby-rails` |
| PHP — Laravel app | `php-laravel` |

If detection found zero manifests, AskUserQuestion with the closed list
of canonical names above (plus "Skip stack wiring"). Free-text answers
are accepted but warn the user if the name doesn't match a known
canonical (typo risk).

Collect every confirmed/renamed name into `STACKS_TO_BUILD` (an in-memory
list the SKILL uses in Phase 4b). If user picks Skip for every stack,
`STACKS_TO_BUILD` is empty — Phase 4b becomes a no-op.

### Phase 3 — Confirm (show drafts)

Show the user a single confirmation block:

```
Ready to write to <target>:

  .claude/            : copy from <source>/.claude/ (excluding setup-gan-harness-skills/)
  Stack skills        : <STACKS_TO_BUILD — built in 4b, after .claude/ exists>
  README.md           : <new from template / skip — already exists>
  CLAUDE.md           : <inject ### Domain docs block>
  Wire stacks into    : agents/{planner,generator,evaluator}.md `skills:`
  Pre-commit hook     : .git/hooks/pre-commit
  Empty containers    : specs/_epic/.gitkeep, specs/epics/.gitkeep

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
The script REFUSES to run if `target/.claude/` already exists (Phase 1
preflight is supposed to have caught that; defense in depth).

**Why this is 4a (first):** `target/.claude/skills/` must exist before
any stack-skill writes to it. Reversing the order — building stack skills
first — causes `copy_substrate.sh` to abort because `target/.claude/`
exists.

#### 4b. Stack-skill build (if `STACKS_TO_BUILD` non-empty)

For each `<stack-name>` in `STACKS_TO_BUILD`, invoke stack-skill-creator
to scaffold `target/.claude/skills/<stack-name>/`.

Two invocation modes; pick the one the current context supports:

**Mode 1 — Skill chain-call (preferred when this SKILL runs in a
main-session Claude with `Skill` tool available):**

```
Skill(skill="stack-skill-creator",
      args="--name=<stack-name> --target=$PWD")
```

Wait for it to return. The chained skill walks its own Pocock-style
flow (detect dialect, ask sensors, write `SKILL.md` with `## Commands`
table + `references/`). The user is in the loop for that skill's
questions.

**Mode 2 — Inline scaffold (fallback when `Skill` tool isn't available,
e.g. this SKILL is being followed by a subagent without skill-invocation
capability):**

Read `<source>/.claude/skills/stack-skill-creator/SKILL.md` directly
and execute its protocol inline as a subroutine within this run.
Produce the same outputs as Mode 1: `target/.claude/skills/<stack-name>/SKILL.md`
(including a `## Commands` markdown table — the harness gate contract),
`references/`. **Do NOT produce `references/upstream.md` in Mode 2** —
that file documents web-fetched provenance, and Mode 2 uses inline
templates (no web fetch).

For each canonical stack name in `STACKS_TO_BUILD`, use the default
toolchain from this table (these defaults short-circuit the questions
stack-skill-creator would otherwise ask):

| Stack | CLI framework / entrypoint | Lint | Typecheck | Test |
|---|---|---|---|---|
| `python-stdlib` | n/a (library) | Ruff | mypy --strict | pytest |
| `python-cli` | argparse (stdlib, no extra dep) | Ruff | mypy --strict | pytest |
| `python-fastapi` | uvicorn + FastAPI router | Ruff | mypy --strict | pytest + httpx |
| `python-django` | manage.py | Ruff | mypy --strict (django-stubs) | pytest-django |
| `python-flask` | flask run | Ruff | mypy --strict | pytest |
| `python-data` | python -m <pkg> (script entry) | Ruff | mypy --strict | pytest |
| `python` | python -m <pkg> | Ruff | mypy --strict | pytest |
| `typescript-nextjs` | Next.js app router | Biome | tsc --strict | vitest |
| `typescript-react` | Vite + React | Biome | tsc --strict | vitest |
| `typescript` | tsc / tsx | Biome | tsc --strict | vitest |
| `javascript-express` | express server | Biome | n/a (JSDoc optional) | vitest |
| `go` | `go run ./cmd/<pkg>` | `go vet` + golangci-lint | (lang built-in) | `go test ./...` |
| `go-gin` | gin router | golangci-lint | (built-in) | `go test ./...` |
| `rust` | `cargo run` | clippy | rustc (built-in) | `cargo test` |
| `dart-flutter` | `flutter run` | dart analyze | (built-in) | flutter test |
| `ruby-rails` | `bin/rails server` | RuboCop | Sorbet (optional) | RSpec |
| `php-laravel` | `php artisan serve` | Pint | PHPStan | PHPUnit |

If the canonical name isn't in the table, ABORT with diagnostic: `"No
canonical inline default for stack '<name>'. Either rename to a known
canonical, or run setup interactively (Mode 1) so stack-skill-creator
can walk the user through tool choice."` — do NOT improvise a toolchain.

`STACKS_TO_BUILD` empty → skip 4b entirely.

#### 4c. README.md (if not present)

If `HAS_README=false`, render
`.claude/skills/setup-gan-harness-skills/templates/README.template.md`
with `{{project_name}}` and `{{one_line_description}}` substituted.
Write to `$PWD/README.md`.

If `HAS_README=true`, skip (the user owns their README).

#### 4d. Memory file `### Domain docs` block

Read
`.claude/skills/setup-gan-harness-skills/templates/claude-md-skills-block.template.md`
verbatim (no token substitution; the template is fixed content). Then:

- If a `### Domain docs` section already exists in the chosen memory
  file (`CLAUDE.md` or `AGENTS.md`), update it in-place. Do not touch
  surrounding sections.
- Else append the block at the end of the file.
- If neither memory file exists, create the chosen one **without any
  YAML frontmatter** — the memory file is plain markdown that Claude
  Code reads on session start, not a skill file. Do not add `---`
  fences. A bare `# <project name>` H1 at the top is optional but
  recommended for human readability.

This MUST preserve user edits to other sections of the file.

#### 4e. Wire stack skills into agent frontmatter

```
python3 .claude/skills/setup-gan-harness-skills/scripts/wire_stack_skills.py \
    --agents-dir "$PWD/.claude/agents" \
    <stack-name-1> <stack-name-2> ...
```

The script edits frontmatter `skills:` of `planner.md`, `generator.md`,
`evaluator.md`. Idempotent (won't double-add). Skips
`codebase-fact-finder.md` (stack-agnostic blindfold research).

If `STACKS_TO_BUILD` is empty (Section D entirely skipped), no-op.

#### 4f. Pre-commit hook (the harness gate's only enforcement point)

Install the project's `.git/hooks/pre-commit` so every `git commit`
automatically runs the gate (lint.fix → lint.check → typecheck →
test.unit → ac_coverage) over the active stack's `## Commands` table
in its SKILL.md. The hook parses the table via
`.claude/scripts/parse_stack_commands.py` (copied with the substrate).
The hook short-circuits to allow normal maintainer commits when no
epic is in flight (`specs/_epic/_traces/current-context.json` absent).

```
bash .claude/skills/setup-gan-harness-skills/scripts/install_pre_commit_hook.sh "$PWD"
```

If the script aborts (target already has a `.git/hooks/pre-commit`),
the operator must reconcile manually before re-running setup. Diff
hint is printed to stderr.

This is the SOLE enforcement point — generator agents do not invoke
the gate manually, and the prompt must not instruct them to.

#### 4g. Empty container sentinels

```
mkdir -p specs/_epic specs/epics
touch specs/_epic/.gitkeep specs/epics/.gitkeep
```

### Phase 5 — Done

Print final report:

```
═══════════════════════════════════════════════════════════════
setup-gan-harness-skills complete — <project_name>
═══════════════════════════════════════════════════════════════

Wrote .claude/                        ✓
Wrote README.md                       <✓ / skipped — existed>
Updated <CLAUDE.md|AGENTS.md>         ✓ (### Domain docs block)
Built stack skills                    <list or "none">
Wired stacks into agent frontmatter   <✓ / skipped — no stacks>
Installed git pre-commit hook         ✓ (.git/hooks/pre-commit)
Sentinels                             specs/{_epic,epics}/.gitkeep

Lazy (will be created when first needed):
  CONTEXT.md      ← first /finalize archive merge
  CODEMAP.md      ← first /finalize regen
  docs/adr/       ← first /init ADR proposal

Next: /init  (start your first epic)
═══════════════════════════════════════════════════════════════
```

## Anti-patterns

- **Copying setup-gan-harness-skills itself to the target.** It's
  bootstrap-only; copy_substrate.sh excludes it. Never weaken that
  exclusion.
- **Pre-creating `CONTEXT.md` / `CODEMAP.md` / `docs/adr/`.** Lazy
  per locked decision. Stubs are lies.
- **Editing surrounding sections of an existing CLAUDE.md / AGENTS.md /
  README.md.** Setup only owns the `### Domain docs` block (and a fresh
  README from template if missing). Anything else is the user's.
- **Bloating the injected block.** The `### Domain docs` block is
  intentionally 3 bullets. Don't add Pipeline / Conventions / Stack
  subsections back in: subagents auto-load their own handbooks; slash
  commands self-document at invocation time; main-session Claude can
  grep `.claude/commands/` if it needs to know what `/init` etc. do.
  Pre-explaining is documentation, not actionable context.
- **Using both CLAUDE.md AND AGENTS.md.** Pocock rule: pick one. Setup
  refuses to proceed if both exist (manual cleanup needed first).
- **Bulk-asking all sections at once.** Walk one-at-a-time, each with
  explainer first. The walk IS the UX contract.
- **Inventing a stack when detection finds nothing.** Skip wiring;
  surface to user. A wrong stack skill drifts forever.

## Done when

- [ ] Phase 1 preflight clean (no live epic, no `.claude/` collision)
- [ ] Sections A–D walked; each answer recorded
- [ ] Phase 3 confirm Approve received
- [ ] 4a `.claude/` copied (minus setup-gan-harness-skills, `__pycache__`)
- [ ] 4b stack skills built into `target/.claude/skills/<name>/` (if any)
- [ ] 4c README.md present (template-rendered or pre-existing)
- [ ] 4d CLAUDE.md or AGENTS.md has `### Domain docs` block (no YAML frontmatter added)
- [ ] 4e stack names wired into planner/generator/evaluator frontmatter
- [ ] 4f `.git/hooks/pre-commit` installed + executable
- [ ] 4g `specs/_epic/.gitkeep` + `specs/epics/.gitkeep` present
- [ ] Final report printed; `/init` suggested
