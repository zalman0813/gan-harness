# {{project_name}}

{{one_line_description}}

## Built with gan-harness

This project uses [gan-harness](https://github.com/anthropics/gan-harness)
for AI-driven feature development. Four stages, locked artefact contract,
human-as-negotiator at every decision boundary.

```
/prd            → specs/_batch/prd.md + research.md
   ↓
/plan           → specs/_batch/feature-list.json + docs/adr/*.md (proposed)
   ↓
/execution-loop → generator ↔ evaluator pairs, max 3 rounds per feature
   ↓
/finalize       → promote ADRs, merge Domain terms, regen codemap, archive
```

## Where to start

Run `/prd` to begin your first batch.

## Project conventions

See `CONTEXT.md` for domain language (created lazily after the first
batch). See `docs/adr/` for accepted architectural decisions (also
lazy). See `CODEMAP.md` for module navigation (regenerated each
finalize).
