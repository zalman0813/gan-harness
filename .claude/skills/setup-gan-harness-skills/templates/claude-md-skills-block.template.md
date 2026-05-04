## Agent skills

This project uses gan-harness for AI-driven feature development.

### Pipeline

- `/prd` — grill user intent + blindfold codebase research → `specs/_batch/prd.md` + `research.md`
- `/plan` — vertical-slice features + proposed ADRs → `specs/_batch/feature-list.json`
- `/execution-loop` — generator ↔ evaluator pairs (max 3 rounds per feature)
- `/finalize` — promote ADRs, merge Domain terms into `CONTEXT.md`, regen `CODEMAP.md`, archive batch

### Domain docs

- `CONTEXT.md` — domain ubiquitous language (lazy-created on first /finalize)
- `docs/adr/` — accepted architectural decisions (lazy-created on first /plan)
- `CODEMAP.md` — module navigation (regenerated each /finalize)

### Conventions

- One batch at a time under `specs/_batch/`; archived to `specs/completed/<slug>/` on /finalize
- ADR three-test gate: hard-to-reverse + surprising + real-trade-off (see `planner-handbook`)
- No `tech-debt` / `risks` lists — every concern resolves into an ADR, an open_question, or a feature
- Vertical slices only (UI → API → service → DB if full-stack); horizontal phasing rejected
