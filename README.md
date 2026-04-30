# gan-harness

A language-agnostic AI coding harness driven by a generator-adversary loop:
the **planner** designs vertical-slice features, the **generator** writes code,
the **evaluator** verifies it, and `/finalize` archives the batch into the
codebase as the single source of truth.

The harness core stays language-free; framework adaptation lives in pluggable
**stack skills** (Python, FastAPI, Next.js, AWS CDK, Flutter, etc.).

## Pipeline

```
/prd            grill in MAIN session + blindfold codebase research
  ↓             writes specs/_batch/prd.md + specs/_batch/research.md
/plan           planner self-verify + per-Q checkpoint walk
  ↓             writes specs/_batch/feature-list.json + proposed ADRs
/execution-loop generator/evaluator round-based feature delivery
  ↓
/finalize       promote ADRs, lazy-create CONTEXT.md, regen codemap, archive batch
```

## Quick start

1. Bootstrap a stack skill at `.claude/skills/<your-stack>/`. Invoke `stack-skill-creator` to walk through it.
2. Run `/prd` with a free-form intent dump (or empty — grill will ask).
3. Run `/plan` — it consumes /prd's outputs and produces `specs/_batch/feature-list.json`.
4. Run `/execution-loop` — it walks features in `depends_on` order.
5. Run `/finalize` when the batch lands, to promote ADRs and archive.

## Project layout

| Path | What lives there |
|---|---|
| `.claude/agents/` | subagent definitions (planner, codebase-fact-finder, generator\*, evaluator\*) |
| `.claude/commands/` | thin command files (`/prd`, `/plan`, `/execution-loop`, `/finalize`) |
| `.claude/skills/` | process skills (plan-workflow, planner-handbook, prd-workflow, stack-skill-creator, batch-gc, …) |
| `.claude/schemas/feature-list.schema.json` | the contract `/plan` produces |
| `ARCHITECTURE.md` | invariants (matklad-style) |
| `CONTEXT.md` | domain ubiquitous language (Pocock-style substrate) |
| `docs/adr/` | MADR architecture decisions (auto-indexed by `/finalize`) |
| `app_docs/codemap.md` | auto-regenerated module map |

\* Step 4 components in development; harness currently delivers Steps 1–3.

## Status

Early alpha. Steps 1–3 done (feature-list schema; `/plan` + planner +
self-verify; `/prd` + grill + blindfold research). Steps 4–5 in
development (generator/evaluator round loop, `/finalize` rewrite).
