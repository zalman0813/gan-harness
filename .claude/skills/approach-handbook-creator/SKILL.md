---
name: approach-handbook-creator
description: Create a new approach handbook for gan-harness — a distilled methodology capsule (TDD, e2e-testing, hexagonal-architecture, event-sourcing, etc.) that one or more harness agents (planner / generator / evaluator / future agents) load via frontmatter `skills:`. Use when the user says "add a methodology", "create a handbook for <approach>", "I want a TDD handbook", "add e2e testing approach", or asks how to make a cross-cutting methodology available to harness agents. Make sure to use this skill whenever the user wants to formalise a design / testing / architecture approach as a reusable handbook, even if they don't say "skill" or "handbook" explicitly.
---

# Approach Handbook Creator

A process skill that produces a new approach handbook at `.claude/skills/<name>-handbook/`. The output is a routing index (`SKILL.md`) plus a `references/` library containing one mandatory `foundation.md` and zero-or-more `<role>-slice.md` files for the agents that load it.

This skill is **not a stack-skill creator**. Stack skills vendor verbatim official docs (data); approach handbooks distil opinionated doctrine (qualitative rules + applicability + red flags). Don't copy the vendoring playbook — it's the wrong shape.

The exemplar in this repo is `.claude/skills/deep-module-handbook/`. Read it before producing a new one — the structural sections of every approach handbook should mirror it.

## Mandatory before starting

Before creating any directory or fetching any source, surface your assumptions:

ASSUMPTIONS I'M MAKING:
1. <e.g., "handbook name is `tdd` → directory `tdd-handbook`">
2. <e.g., "primary source is Beck *TDD by Example* (2002) + the user's notes at /docs/team-tdd.md">
3. <e.g., "loaders are generator + evaluator; planner is NOT a loader because TDD does not change planner's AC-decomposition stage">
4. <e.g., "scope is Starter — foundation + 1 slice stub, no comprehensive draft">
→ Correct me now or I'll proceed with these.

Do not silently pick loaders on the user's behalf. Loaders dictate which agent prompts must be edited at Step 5; wrong loaders = wrong agents touched.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'm not deep on this methodology, I'll write a reasonable skeleton" | Unfamiliar = stop. Skeletons without primary sources become folklore that rots. Either source from a paper/book/canonical doc the user names, or refuse. |
| "This is internal team practice, no public source exists" | Still write a `Source` field on every red flag (`internal/team-X-2024-Q3-retro` is a valid source). The constraint is auditability, not academic provenance. |
| "Red flags are obvious, citations are bureaucratic" | The schema (Source / Pattern / Trigger / If-fires-recommend / Retirement-criteria) was set by `deep-module-handbook/foundation.md`. Skipping it makes red flags unverifiable and unmergeable into evaluator's uniform handling. |
| "Every loader needs its own slice file" | Wrong by default. A loader needs a slice ONLY when the foundation alone leaves stage-specific actions ambiguous. Many handbooks ship with foundation + 0 or 1 slice. Recommend per-loader; do not auto-create. |
| "I'll fix the agent's frontmatter `skills:` later" | Later = never. A handbook with no loader registered is a dead file. Step 5 is mandatory; refuse to skip it. |

## When the user invokes this skill

Capture intent up front via `AskUserQuestion`. Run the questions sequentially — Q4 depends on Q3's answer.

1. **Handbook name** — kebab-case identifier without the `-handbook` suffix (creator appends it). Examples: `tdd`, `e2e-testing`, `hexagonal-architecture`, `event-sourcing`, `property-based-testing`. Final directory will be `.claude/skills/<name>-handbook/`.
2. **Source of doctrine** — one of:
   - Primary source (the user names a book / paper / canonical doc with citation)
   - Industry consensus + user distillation (creator helps synthesize from multiple sources the user references)
   - Pure user-opinion (rare; flagged in `upstream.md` as `source: user-opinion`, no academic citation)
3. **Loaders** — which agents will load this handbook via their frontmatter `skills:`. Any path under `.claude/agents/*.md` is allowed; creator validates each path exists. Examples: `planner.md`, `generator.md`, `evaluator.md`, or any custom agent.
4. **Per-loader slice decision** — for each loader from Q3, ask whether a `<role>-slice.md` is needed. Creator MUST give a recommendation per loader, not just ask blank. Heuristic for the recommendation:
   - **Recommend slice** when the methodology changes the agent's *actions* at its stage (e.g., TDD changes generator's red-green-refactor cycle → generator-slice yes).
   - **Recommend no slice** when foundation alone gives the agent everything they need (e.g., TDD does not change planner's AC decomposition; planner just needs foundation's red flags → planner-slice no).
   - State the recommendation with one-line reasoning, then let the user confirm or override.
5. **Scope**:
   - Starter — foundation + every confirmed slice as a stub with §-headings only (~30 min)
   - Comprehensive — foundation fully drafted (definitions, applicability, red flags) + every confirmed slice fully drafted (~hours; user supplies or creator drafts from primary sources via WebSearch + WebFetch)

Confirm the full answer set before proceeding.

## Process

### Step 1 — Capture intent

Run Q1–Q5 above. Wait for the full answer set.

### Step 2 — Distil the substantive doctrine

Create `.claude/skills/<name>-handbook/references/`.

Write `references/foundation.md` first. Foundation MUST contain three sections:

- **§Definitions** — the methodology's core terms with one-sentence definitions and qualitative checks (mirror `deep-module-handbook/foundation.md` §1 table format). Cite primary source per row when available.
- **§Applicability** — when to apply this methodology AND when explicitly NOT to (e.g., "TDD does not apply to one-shot exploratory scripts"). The "when not" half is non-negotiable; refusing to bound applicability creates a methodology that gets wrongly applied everywhere.
- **§Red flags** — each flag MUST have all five fields:
  - `Source` — where this flag came from (book/section, paper, blog post, internal retro)
  - `Pattern` — what the flag looks like in code or design
  - `Trigger` — what condition makes you suspect the flag fires
  - `If-fires-recommend` — what action to recommend (open_question, ADR proposal, refactor)
  - `Retirement-criteria` — what evidence would justify removing or relaxing this flag in future
  - This schema is inherited from `deep-module-handbook/foundation.md` § Red flag schema and is uniform across all approach handbooks so evaluator can process them uniformly.

Vendoring rules (different from stack-skill-creator):
- **Distil, don't paraphrase blindly.** A red flag should compress the source's argument into the five fields, not re-quote three paragraphs.
- **Cite primary source on every claim.** If a definition or red flag has no source, it does not get written.
- **Cap `foundation.md` at ~600 lines.** Larger means the handbook is doing too much; split into two handbooks.

If web fetching is needed (industry-consensus source mode), record provenance in `references/upstream.md` (table: file | source URL | revision/SHA | license | fetched_at). For user-opinion mode, `upstream.md` still exists with `source: user-opinion-<YYYY-MM-DD>` rows.

### Step 3 — Write per-role slices (only those confirmed in Q4)

For each loader from Q3 where Q4 confirmed a slice is needed, create `references/<role>-slice.md` (e.g., `generator-slice.md`).

A slice answers: **"In this role's stage, what specific action does the foundation's principle X translate to?"**

Slice rules:
- Reference foundation, do not duplicate it. ("Per foundation §Red flags row TDD-3, when you see <pattern>, do <stage-specific action>.")
- One section per decision point in the role's stage (e.g., generator's "writing the test", "running the test", "refactor step").
- Cap each slice at ~300 lines.
- Loaders WITHOUT a slice are fine — they read only `foundation.md` at run time. Document in SKILL.md's routing table that those loaders read only foundation.

### Step 4 — Write SKILL.md (routing index, not doctrine body)

Copy `templates/handbook-SKILL.md.template` to `.claude/skills/<name>-handbook/SKILL.md`. Substitute these tokens:

- `<name>` — kebab-case from Q1 (without `-handbook` suffix)
- `<Handbook Title>` — title-case display form (e.g., "TDD Handbook")
- `<one-line methodology positioning>`
- `<routing-table-rows>` — one row per loader from Q3, mapping the loader's decision-point to either `references/<role>-slice.md` (if slice exists) or `references/foundation.md` (if no slice)
- `<is-list>` and `<is-not-list>` — the methodology's scope claims
- `<consume-anti-patterns>` — anti-patterns specific to consuming this methodology (e.g., "treating TDD red flags as auto-FAIL")

The template's seven sections (positioning paragraph / decision routing table / loading order / IS / IS NOT / Anti-patterns when consuming / Where the heavy thinking lives) are the locked structure for every approach handbook. Do not omit sections; if a section has no content for this handbook, write `_(none)_` to make the omission explicit and reviewable.

### Step 5 — Register loaders (mandatory; this is what stack-skill-creator does NOT do)

For each agent file from Q3 (e.g., `.claude/agents/generator.md`):

1. Read the agent's frontmatter.
2. If frontmatter has no `skills:` key, add it as a YAML list.
3. Append `<name>-handbook` to the list. If already present, skip (idempotent).
4. Show the user the diff (before/after frontmatter) for each agent file edited.
5. Wait for user confirmation before writing the edit, OR — if the user pre-authorised in Q3 — apply directly and report which files changed.

A handbook without a registered loader is a dead file. Refuse to finish Step 5 if any Q3 loader was skipped.

### Step 6 — Self-validate

Run minimal checks (inline, not a separate script):

- `SKILL.md` frontmatter has `name` + `description`.
- `SKILL.md` description names the loaders explicitly (so the description itself documents who loads it — mirrors `deep-module-handbook` description shape).
- `references/foundation.md` exists and has §Definitions, §Applicability, §Red flags headings.
- Every red flag in `foundation.md` has all five fields (Source / Pattern / Trigger / If-fires-recommend / Retirement-criteria). Grep for any flag missing `Source:` and refuse to ship.
- For each loader from Q3 that confirmed a slice in Q4: `references/<role>-slice.md` exists.
- For each loader from Q3 (slice or not): the agent's `frontmatter skills:` contains `<name>-handbook`.
- `references/upstream.md` exists with at least one row.
- No file in `references/` exceeds the section caps (foundation ≤600, slice ≤300).

Print summary: handbook path, loader count, slice count, foundation LOC, red-flag count, agent files modified at Step 5.

### Step 7 — Hand off

Tell the user:

> The approach handbook is at `.claude/skills/<name>-handbook/`. It is registered on <list of agent files>. Those agents will load it on their next invocation via the harness loader chain. To revise the doctrine, edit `references/foundation.md`. To revise role-specific application, edit the relevant `references/<role>-slice.md`. To retire a red flag, document the retirement evidence in the flag's `Retirement-criteria` field and remove the row.

## Anti-patterns

- **Putting doctrine in `SKILL.md`** — `SKILL.md` is the routing index. Substantive content lives in `references/`. A heavy `SKILL.md` defeats progressive disclosure.
- **Cross-role slice reading** — slices are role-isolated. Generator should not read `evaluator-slice.md` (and vice versa). Document this prohibition in `SKILL.md` § Loading order. The creator does not enforce it at write time but should mirror the deep-module-handbook prohibition language verbatim.
- **Red flags without `Source` field** — folklore flags rot. Refuse to write a flag that names no source (even `internal/team-retro-2026-Q1` is acceptable; the constraint is having something to point to).
- **Auto-creating per-loader slices** — slices are elective per Q4. Default is no slice; the creator must justify each slice it recommends.
- **Skipping Step 5 (loader registration)** — a handbook with no loader is a dead file. The creator MUST refuse to claim done if any Q3 loader's frontmatter was not updated.
- **Treating this as a stack-skill-creator clone** — the substrate (distilled doctrine) and validation contract (red-flag schema, loader registration) are different. Don't import stack-skill-creator's `## Commands` table step or vendoring "verbatim" rule.
- **Including a `## Commands` table** — that is a stack-skill artefact (the harness gate contract). Approach handbooks have no machine command contract; they're prose-and-tables read by agent prompts.

## Examples

### Example 1 — Add `e2e-testing-handbook` (loaders: generator + evaluator)

```
User: "I want a handbook for e2e testing via computer-use or playwright CLI."
Creator: AskUserQuestion sequence:
  Q1: name → e2e-testing
  Q2: source → industry consensus (Playwright docs + Anthropic computer-use docs)
       + user distillation
  Q3: loaders → generator, evaluator
  Q4: per-loader slice:
       generator-slice → RECOMMENDED YES (writes test, picks driver per feature shape)
       evaluator-slice → RECOMMENDED YES (judges L5 AC coverage, distinguishes
         flaky-by-driver vs flaky-by-test)
  Q5: scope → starter
Creator:
  Writes references/foundation.md (definitions of e2e vs integration vs smoke;
    applicability: when L5 AC is justified vs over-built; red flags: e.g.
    "selector by visual coordinates without semantic backup")
  Writes references/generator-slice.md stub (driver selection table,
    test-id discipline)
  Writes references/evaluator-slice.md stub (smoke-flake triage)
  Writes SKILL.md from template
  Updates .claude/agents/generator.md and .claude/agents/evaluator.md
    frontmatter `skills:` to include e2e-testing-handbook
  Validates
  Reports: handbook at .claude/skills/e2e-testing-handbook/, 2 loaders,
    2 slices, foundation 180 LOC, 6 red flags, 2 agent files modified
```

### Example 2 — Add `tdd-handbook` (loaders: planner + generator + evaluator, but planner-slice NOT created)

```
User: "Add a TDD handbook."
Creator: AskUserQuestion:
  Q1: name → tdd
  Q2: source → primary (Beck *TDD by Example* 2002) + user notes
  Q3: loaders → planner, generator, evaluator
  Q4: per-loader slice:
       planner-slice → RECOMMENDED NO ("TDD doesn't change planner's AC
         decomposition; planner only needs foundation's red flags to judge
         whether an AC is test-orderable")
       generator-slice → RECOMMENDED YES (red-green-refactor cycle is
         generator's stage-specific behaviour)
       evaluator-slice → RECOMMENDED YES (judging test-first-vs-test-after
         is evaluator's stage)
       User confirms all three recommendations.
  Q5: scope → comprehensive
Creator:
  Writes foundation.md (Beck-cited definitions, applicability incl. "NOT
    for one-shot exploratory scripts", red flags table)
  Writes generator-slice.md (full red-green-refactor cycle)
  Writes evaluator-slice.md (test-first heuristics)
  Skips planner-slice.md (planner reads only foundation)
  SKILL.md routing table notes "planner → references/foundation.md only"
  Updates planner.md, generator.md, evaluator.md frontmatter skills:
  Validates
  Reports: 3 loaders, 2 slices, planner reads foundation only
```

### Example 3 — Add `hexagonal-architecture-handbook` (loaders: planner only)

```
User: "Add hexagonal architecture as a planner-side methodology."
Creator: AskUserQuestion:
  Q1: name → hexagonal-architecture
  Q2: source → primary (Cockburn 2005 hexagonal pattern) + Vaughn Vernon
       *Implementing DDD* port-adapter chapters
  Q3: loaders → planner
  Q4: planner-slice → RECOMMENDED YES (hexagonal directly changes how
       planner draws module boundaries in feature-list.json)
  Q5: scope → starter
Creator:
  Writes foundation.md (port/adapter definitions; applicability:
    when business logic > infrastructure cost; red flags: e.g.
    "domain layer imports framework class")
  Writes planner-slice.md stub
  SKILL.md notes "loader: planner only"
  Updates planner.md frontmatter skills: → adds hexagonal-architecture-handbook
  Validates
  Reports: 1 loader, 1 slice, 1 agent file modified
```

## What's intentionally NOT in this skill

- **No `## Commands` table** — that is a stack-skill artefact (the harness gate contract); approach handbooks have no machine contract.
- **No vendoring of verbatim official docs** — distillation is the substrate; if the user wants verbatim docs they want a stack skill, not a handbook.
- **No automatic loader inference** — loaders MUST be explicit (Q3); the creator does not guess from the methodology name.
- **No slice auto-creation** — slices are elective per loader (Q4); default is no slice with foundation-only consumption.
- **No ADR writing** — that is `plan-workflow`'s job at /plan time. The handbook may *recommend* an ADR be raised when a red flag fires, but the creator does not write ADRs itself.
- **No lint enforcement target** — methodology heuristics are design-time doctrine, not runtime gates. The handbook's red flags fire at design / review time and produce open_questions; they do not become CI checks. Mirrors `deep-module-handbook` § "What this skill is NOT".
