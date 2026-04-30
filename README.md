# gan-harness

A language-agnostic AI coding harness driven by a generator-adversary loop:
the **planner** designs vertical-slice features, the **generator** writes code,
the **evaluator** verifies it, and `/finalize` archives the batch into the
codebase as the single source of truth.

The harness core stays language-free; framework adaptation lives in pluggable
**stack skills** (Python, FastAPI, Next.js, AWS CDK, Flutter, etc.).

## Pipeline

```
/prd            grill-driven requirements + glossary draft
  ↓
/plan           blindfold codebase research + planner self-verify
  ↓             writes specs/_batch/feature-list.json + proposed ADRs
/execution-loop generator/evaluator round-based feature delivery
  ↓
/finalize       promote ADRs, regen codemap, archive batch
```

## Quick start

1. Bootstrap a stack skill at `.claude/skills/<your-stack>/`. Invoke `stack-skill-creator` to walk through it.
2. Run `/prd` with a free-form intent dump or batch file path.
3. Run `/plan` — it consumes /prd's outputs and produces `specs/_batch/feature-list.json`.
4. Run `/execution-loop` — it walks features in `depends_on` order.
5. Run `/finalize` when the batch lands, to promote ADRs and archive.

## Project layout

| Path | What lives there |
|---|---|
| `.claude/agents/` | subagent definitions (planner, codebase-fact-finder, generator\*, evaluator\*) |
| `.claude/commands/` | thin command files (`/prd`, `/plan`, `/execution-loop`, `/finalize`) |
| `.claude/skills/` | process skills (plan-workflow, planner-handbook, stack-skill-creator, batch-gc, …) |
| `.claude/schemas/feature-list.schema.json` | the contract `/plan` produces |
| `ARCHITECTURE.md` | invariants (matklad-style) |
| `docs/adr/` | MADR architecture decisions (auto-indexed by `/finalize`) |
| `CONTEXT.md` | Domain ubiquitous language + agent reading protocol (Pocock-style) |
| `app_docs/codemap.md` | auto-regenerated module map |

\* Step 4 components in development; harness currently delivers Steps 1–2.

## Status

Early alpha. Step 1 (feature-list schema) and Step 2 (`/plan` + planner +
self-verify) complete. Steps 3–5 (`/prd` rewrite, generator/evaluator,
`/finalize` ADR lifecycle) in development.
