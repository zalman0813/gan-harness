# gan-harness — maintainer instructions for Claude

This repo is a **template / scaffolder**: `setup-gan-harness-skills`
copies parts of it to other projects. When working in this repo, you
MUST keep two namespaces separate, or you will silently leak
maintainer-only refs into the prompts that get shipped to target
projects.

@CONTEXT.md

## Behavioral foundation

These four lines shape *how* you work on every task in this repo, before any
project-specific rule below. They are the behavioral layer; the footgun rules
in the next section are the thin project layer on top.

1. **Don't assume. Don't hide confusion. Surface tradeoffs.**
   When a request is ambiguous (scope, format, target stack, which file),
   list the assumptions and ask before coding. Models are trained on
   completion, not on pausing — override that default.

2. **Minimum code that solves the problem. Nothing speculative.**
   Build for today's requirement, not tomorrow's. No premature abstraction,
   no "in case we later need it" config layers. If a senior engineer would
   call the design overcomplicated for what was asked, simplify.

3. **Touch only what you must. Clean up only your own mess.**
   Every changed line traces to the request. Don't reformat unrelated code,
   don't tighten validation that wasn't the bug, don't rename adjacent
   variables. If your own changes orphan an import or variable, clean those
   up; pre-existing dead code is the user's call.

4. **Define success criteria. Loop until verified.**
   Before starting non-trivial work, restate the goal as verifiable checks
   (a failing test that reproduces the bug, a lint command that must pass,
   the AC literal-id that must appear in a passing test). After each step,
   re-run the check. "Done" means verified — not "I think I'm done."

Source: <https://github.com/forrestchang/andrej-karpathy-skills> (distilled
from Karpathy's January 2026 thread on agent failure modes).

When a project-specific rule below conflicts with one of these, the
project-specific rule wins for that scope — but cite which line you're
overriding and why, so the override is auditable.

## Critical: maintainer-only vs target-copied paths

| Path | Setup-copied to target? | If you write here, audience is |
|---|---|---|
| `.claude/agents/`, `.claude/skills/`, `.claude/hooks/`, `.claude/scripts/`, `.claude/commands/` | **YES (full copy)** — except `.claude/skills/setup-gan-harness-skills/` itself (bootstrap-only, hard-excluded by `copy_substrate.sh`) | the target project's runtime — the target does NOT have `docs/maintainer/`, does NOT see gan-harness's own ADRs |
| `.claude/skills/setup-gan-harness-skills/` | NO (excluded by `copy_substrate.sh`; also fail-safe rm + post-copy assertion) | gan-harness maintainers — runs IN gan-harness, validates source has `docs/maintainer/design/agent-prompt-doctrine.md` as marker |
| `templates/README.template.md`, `templates/claude-md-skills-block.template.md` | YES (rendered into target's files) | target maintainer |
| `README.md` | NO (target gets its own from template) | gan-harness contributors |
| `CONTEXT.md` (this file's ubiquitous-language sibling) | NO (target lazy-creates its own) | gan-harness maintainers + Claude in this repo |
| `CLAUDE.md` (this file) | NO (target gets its own via skills-block injector) | gan-harness maintainers + Claude in this repo |

Source of truth for the boundary: `setup-gan-harness-skills/scripts/copy_substrate.sh` (rsync exclusion list).

## Footgun rules — ALWAYS check these before writing prompts/skills

1. **Never reference `docs/maintainer/...` from any file that gets copied to target.**
   Those files get copied to target projects where `docs/maintainer/` does not exist. Every `[link](docs/maintainer/...)`, every `@docs/maintainer/...`, every prose ref becomes a broken link on every setup.
   - Sole exception: files under `.claude/skills/setup-gan-harness-skills/` are excluded from copy, so they MAY ref `docs/maintainer/` (e.g., to validate that the source path looks like a gan-harness checkout). To verify exclusion before referencing, check `.claude/skills/setup-gan-harness-skills/scripts/copy_substrate.sh` exclusion list.

3. **Don't write target-project-specific content into `CONTEXT.md`.**
   This `CONTEXT.md` is gan-harness's own ubiquitous language for maintainer use. Target projects lazy-create their own `CONTEXT.md` describing THEIR domain (their User, their Order, their Customer) — they do NOT inherit this one.
   - Pure gan-harness *mechanism* terms (e.g., `ac_coverage gate`, `Quarantine entry`, `harness-loop`) belong in the prompts under `.claude/` that explain the mechanism inline — NOT in any `CONTEXT.md`.
   - This `CONTEXT.md` only holds gan-harness's own ubiquitous-language concepts (Vertical slice, Feature, AC, ADR, Open question, Stack skill, Batch).

4. **`docs/maintainer/design/agent-prompt-doctrine.md` is design guidance, not a runtime SSoT.**
   The doctrine file is a maintainer-facing design memo describing the constraint shape (Mandatory before starting / Common Rationalizations / Anti-patterns + universal rules + per-agent catalogue). It is NOT loaded at runtime by any agent, skill, or hook. Each `.claude/agents/*.md` and worker `SKILL.md` is self-contained — it inlines its own constraint sections in its own voice.
   - Do NOT make any worker prompt point back at the doctrine file (no `[link](...)`, no `@path`, no prose ref).
   - Do NOT treat the doctrine catalogue as authoritative — when prompt and catalogue disagree, the prompt wins. The catalogue is a cross-agent overview for human maintainers.
   - When updating an agent's behavior: edit the agent prompt directly (that is what runs). Optionally update the doctrine catalogue to keep the overview current — the reverse direction (memo first, then sync) is wrong.
   - Verify before commit: `grep -r "agent-prompt-doctrine" .claude/ templates/` must return zero results. The same applies to any other file under `docs/maintainer/` — they are maintainer-only.

5. **Audit copy boundary BEFORE adding any cross-file ref or new doctrine entry.**
   Before writing `[link](...)` or `@path` in any markdown file, ask: "Is the target file copied to target projects? Is the source file copied to target projects?" If the answer differs, the link is wrong.

## Why these rules exist

A previous round added `(per ADR-0003)` refs throughout `.claude/agents/`, `.claude/skills/`, `.claude/hooks/`, on the assumption that ADRs are shared across maintainer + target. They are not. After `setup-gan-harness-skills` ships those files to a target project, the target's agent loads a prompt full of broken refs. The fix was tedious; the discipline is cheap.

Rule 4 codifies a related discipline that was implicit until now: the doctrine file's own self-prescriptive sentences ("every worker prompt carries a one-line pointer back here", "sync the affected agent prompt(s) — copy the row(s) verbatim") were never followed at runtime — the actual worker prompts are self-contained. Rule 4 makes the discipline explicit so future Claudes don't try to "fix" the inconsistency in the wrong direction.
