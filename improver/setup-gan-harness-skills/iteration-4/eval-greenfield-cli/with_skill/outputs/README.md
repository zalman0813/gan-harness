# kvstore

A small kv-store inspector for local JSON config files.

## Built with gan-harness

This project uses [gan-harness](https://github.com/anthropics/gan-harness)
for AI-driven feature development. Three stages, immutable spec, per-sprint
contract negotiation between generator and evaluator, human-out-of-the-loop.

```
/init     → specs/_epic/spec.md (immutable: vision + features + sprint plan + 4 criteria)
   ↓
/loop     → per sprint: negotiate contract → implement → evaluate
            generator ↔ evaluator GAN loop until evaluator approves
            (no max-round cap; operator monitors cost externally)
            Outputs: specs/_epic/contracts.jsonl (append-only) + _evals/ + _traces/
   ↓
/finalize → promote ADRs, merge Domain terms, regen codemap,
            archive specs/_epic/ → specs/epics/<slug>/
```

## Where to start

Run `/init` to begin your first epic. The planner agent will grill you for
intent, tech stack, scope boundaries, success criteria, and target archetype
(frontend / backend / library / cli / data-pipeline / hybrid). Skip the grill
with `--no-grill` if you've already written a complete intent.

## Project conventions

- `CONTEXT.md` — domain ubiquitous language (created lazily after the first epic).
- `docs/adr/` — accepted architectural decisions (also lazy).
- `CODEMAP.md` — module navigation (regenerated at each /finalize).
- `specs/epics/<slug>/` — archived epics for historical reference.
