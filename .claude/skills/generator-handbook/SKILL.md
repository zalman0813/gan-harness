---
name: generator-handbook
description: Doctrine the gan-harness generator agent operates by — conservative-default discipline (don't expand AC silently), anti-under-scope discipline (don't narrow planner's scope), and AC-traceable test authoring (literal AC-ids in test bodies). For deep-module design methodology when picking interface boundaries, see the separate `deep-module-handbook` approach skill which generator also auto-loads via frontmatter `skills:`. Loaded by the generator subagent at startup. Make sure to use this whenever implementing a feature, designing a module's public surface, or authoring tests against acceptance criteria.
---

# Generator Handbook

The generator agent's operating doctrine. Each reference is loaded on demand
when the generator reaches the relevant decision point.

## When the generator consults each reference

| Decision point | Read |
|---|---|
| Designing a module's public surface (functions, types, error modes) | [`deep-module-handbook` skill](../deep-module-handbook/SKILL.md) (foundation.md + the slice file generator-handbook will eventually own) |
| Tempted to add validation / safety / fallback that AC didn't ask for | [references/conservative-defaults.md](references/conservative-defaults.md) |
| Tempted to narrow the feature's scope ("this is bigger than I thought") | [references/anti-under-scope.md](references/anti-under-scope.md) |
| Writing tests that must trace back to AC ids | [references/anti-under-scope.md](references/anti-under-scope.md) § "Test traceability" |

## Loading order

Read `conservative-defaults.md` and `anti-under-scope.md` once at the top
of a feature, before designing. They're short. Re-read whenever you catch
yourself rationalizing scope creep or scope cuts.

`deep-module-handbook` is read when you reach the public-surface design
step — not before.

## What's NOT here

- Stack-specific test idioms (pytest `assert` patterns, jest `expect`
  patterns, dart `group(...)` literals) — those live in the active stack
  skill's references
- Schema details for `feature-list.json` — those live in
  `.claude/schemas/feature-list.schema.json`
- Hook behaviour (what the trace records, what `progress.tsv` columns mean)
  — those live in `.claude/hooks/log_subagent_stop.py` docstring
- Adversarial probe categories — those are evaluator's domain, in
  `evaluator-handbook/references/adversarial-probes.md` (and reading them
  from the generator's process is `block_pretool.py`-blocked)
