# Skill Architecture — gan-harness skill classification doctrine

The four tiers a skill must belong to, what each tier means, and where
doctrine lives. Every new skill picks exactly one tier; cross-tier
duplication is forbidden.

Companion doctrine: `agent-prompt-doctrine.md` (universal constraint
layer every worker prompt embeds).

## Why this exists

Skills proliferate. Without a classification taxonomy, naming drifts,
scope creeps, and the same content gets duplicated across multiple
skills.

This doctrine refactors and extends the prior dandan-app-fullstack
`skill-capsule-architecture` (which separated portable workflow from
project behavior in three tiers). gan-harness extends to four tiers
because we explicitly distinguish:

- agent-specific behavior (e.g., generator's conservative-default
  decision discipline)
- methodology that crosses agents (e.g., deep-module principles applied
  by planner, generator, AND evaluator at different stages)

Without that split, "approach" content gets duplicated into every
agent handbook that uses it.

## The four tiers

### 1. Workflow skill — drives a slash command

Purpose: orchestrate one slash command's phases.
Naming: `<verb>-workflow` (or noun describing the operation, like
`stack-skill-creator`).
Loaded by: thin command file `.claude/commands/<verb>.md` invokes it.
Lifecycle: rev with the command's pipeline shape.

Examples in this repo:
- `prd-workflow` — drives `/prd`
- `plan-workflow` — drives `/plan`
- `batch-gc` — drives `/finalize` (will be rewritten in T9)
- `stack-skill-creator` — drives `stack skill` creation
- (T8 future) `harness-loop` — drives `/execution-loop`

### 2. Agent handbook — one agent's intrinsic behavior

Purpose: how a specific agent behaves regardless of task — its
rationalizations to fight, its checklists, its self-verify discipline.
Naming: `<agent>-handbook`.
Loaded by: agent definition `.claude/agents/<agent>.md` via frontmatter
`skills:`. Loaded deterministically at agent startup.
Lifecycle: rev with the agent's role.

Examples:
- `planner-handbook` — planner's behavior (vertical-slice rule,
  three-script self-verify, ADR lifecycle, decomposition discipline)
- (T8 future) `generator-handbook` — generator's behavior
  (conservative-default for ambiguity, test-first, "don't add what
  AC didn't ask for")
- (T8 future) `evaluator-handbook` — evaluator's behavior (QA
  independence from generator's reasoning, AC-as-contract,
  PASS/FAIL/DEFERRED verdict discipline)

### 3. Approach handbook — a methodology / design philosophy

Purpose: a school of thought that multiple agents apply at the
intersection of their role and the methodology.
Naming: `<methodology>-handbook`.
Loaded by: any agent that needs the methodology, via frontmatter
`skills:`.
Lifecycle: rev with primary literature (when Ousterhout updates,
when DDD canon shifts).

Internal structure:
- `SKILL.md` — routing index (which slice for which agent)
- `references/foundation.md` — shared definitions, applicability,
  primary-source-cited principles, red flags
- `references/<role>-slice.md` × N — how each consuming agent applies
  the methodology in their role

Examples:
- `deep-module-handbook` — Ousterhout/Pocock methodology; planner
  designs around it, generator implements it, evaluator reviews
  against it
- (potential future) `vertical-slice-handbook` — extracted from
  planner-handbook if generator and evaluator also need to reason
  about vertical-slice constraints

### 4. Stack skill — framework / language conventions

Purpose: vendored idioms for a specific tech stack.
Naming: `<stack-name>` kebab-case (e.g., `python-fastapi`,
`nextjs-supabase`, `cdk-typescript`).
Created by: `stack-skill-creator` skill.
Loaded by: agents that touch code in that stack, via runtime decision
based on which stack the active project uses.
Lifecycle: rev when the upstream stack ships changes.

Always vendored from upstream docs (with `references/upstream.md`
provenance log). Never paraphrased.

## Where does X go? — quick test

A specific piece of doctrine belongs to exactly one tier. Use these
tests in order:

1. **Does it orchestrate a slash command's phases?** → workflow skill
2. **Is it stack-specific (Python idiom, React pattern)?** → stack skill
3. **Is it a methodology applicable to multiple agents at different
   stages?** → approach handbook
4. **Is it about a single agent's intrinsic behavior in any task?** →
   agent handbook

If none apply: re-examine. The doctrine probably belongs in
`agent-prompt-doctrine.md` (universal constraint) or `README.md` § Core
design concepts (system-level positioning), not in a skill.

### Concrete examples

| Doctrine | Tier | Reasoning |
|---|---|---|
| Generator's "conservative-default decision table" | Agent handbook (`generator-handbook`) | Only generator applies it; it's about how generator handles ambiguity in any spec |
| Deep-module principles | Approach handbook (`deep-module-handbook`) | Three agents use it: planner designs deep modules; generator implements with hidden complexity; evaluator reviews depth |
| `__init__.py` barrel pattern | Stack skill (`python-*`) | Pure Python convention |
| PRD's grill protocol | Workflow skill (`prd-workflow`) | Orchestrates `/prd` phases |
| ADR three-test gate | Agent handbook (`planner-handbook`) | Planner is the only agent that proposes ADRs |
| Vertical-slice rule | Currently agent handbook (`planner-handbook`); could become approach handbook if T8 generator and evaluator also need it | Tier may be revisited as scope grows |

## Composition pattern

```
.claude/agents/planner.md            ← responsibility (system prompt body)
  frontmatter:
    skills:
      - planner-handbook             ← agent's intrinsic behavior
      - deep-module-handbook         ← approach methodology

.claude/agents/generator.md (T8)     ← responsibility
  frontmatter:
    skills:
      - generator-handbook           ← agent's intrinsic behavior
      - deep-module-handbook         ← approach methodology

.claude/agents/evaluator.md (T8)     ← responsibility
  frontmatter:
    skills:
      - evaluator-handbook           ← agent's intrinsic behavior
      - deep-module-handbook         ← approach methodology

.claude/skills/python-fastapi/       ← stack skill, loaded ad-hoc
```

The agent's responsibility (identity, role, when-to-do-what,
output-shape) lives in the agent definition body. Doctrine lives in
skills.

### Loading discipline (deterministic vs ad-hoc)

- Frontmatter `skills:` triggers deterministic load of each skill's
  `SKILL.md` body at agent startup. Always present in agent context.
- References inside a skill are progressive disclosure — agent reads
  them on-demand following SKILL.md's routing instructions.
- Stack skills are typically loaded ad-hoc (agent decides based on
  the active project's stack), not via frontmatter.

## Anti-patterns

- **Kitchen sink skill** — bundling behavior + approach + workflow
  into one skill. Symptom: SKILL.md has phases AND rationalization
  tables AND methodology principles. Fix: split into separate skills,
  one per tier.

- **Wrong tier** — putting generator-only conservative-default into
  an approach handbook. Symptom: only one agent ever consumes the
  content. Fix: move to that agent's handbook.

- **Cross-tier duplication** — same content lives in approach handbook
  AND consuming agent's handbook. Symptom: edit one, drift apart.
  Fix: approach handbook owns the principle; agent handbook only
  adds role-specific application.

- **Workflow skill containing runtime decision logic** — workflow
  skills drive a slash command's phases; they should not contain
  branching logic that runs after the command's main flow. Fix:
  extract runtime logic to an agent or a different workflow skill.

- **Approach handbook without per-role slices** — if every consuming
  agent reads the same monolithic content, it's probably agent-handbook
  content. Slices justify the approach tier. Fix: either add slices
  or downgrade to agent handbook.

- **Stack skill paraphrasing upstream** — vendoring means copying the
  canonical text, not summarizing. Summaries lose the literal idioms
  downstream agents grep for. Fix: re-vendor verbatim with provenance.

## Existing inventory

| Skill | Tier | Loaded by | Status |
|---|---|---|---|
| `prd-workflow` | Workflow | `/prd` command | T7 done |
| `plan-workflow` | Workflow | `/plan` command | T2-T6 done |
| `batch-gc` | Workflow | `/finalize` command | Will be rewritten in T9 |
| `stack-skill-creator` | Workflow | stack skill creation flow | T10 done |
| `planner-handbook` | Agent handbook | `planner` agent (frontmatter) | T2-T6 done |
| `deep-module-handbook` | Approach handbook | `planner` agent (frontmatter) today; `generator` + `evaluator` future | This commit |
| `generator-handbook` | Agent handbook | `generator` agent (T8) | Future — houses conservative-default |
| `evaluator-handbook` | Agent handbook | `evaluator` agent (T8) | Future — houses QA independence + verdict discipline |
| `harness-loop` | Workflow | `/execution-loop` command (T8) | Future — DAG order, max 3 rounds, DEFERRED skip-downstream |
| `<stack-name>` (e.g., `python-fastapi`) | Stack skill | Ad-hoc by any agent touching that stack | Created on demand by `stack-skill-creator` |

## What this file is NOT

- A skill (no `name`/`description` frontmatter — loaded by reference,
  not auto-invoked)
- A schema (no machine validation — humans + reviewers enforce)
- An ADR (decisions to add a new tier MAY also produce an ADR if
  hard-to-reverse)

## Updating this doctrine

Triggers for update:
- New skill tier observed (a shape that doesn't fit four tiers) →
  add tier or fold the new shape into existing
- New shared anti-pattern observed across multiple skills → add
  to § Anti-patterns
- Existing inventory grows → keep table current; this is the SSoT
  for "what skills exist and what tier each is"

When updating:
1. Edit this file
2. If tiers changed: audit existing skills against the new taxonomy;
   flag any skill in the wrong tier
3. Note the change rationale in commit message
