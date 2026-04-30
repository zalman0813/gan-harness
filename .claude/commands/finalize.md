---
allowed-tools: Read, Edit, Write, Bash, Grep, Glob, AskUserQuestion, Agent
description: Post-batch ceremony — drain dreamer proposals via AskUserQuestion, promote glossary/codemap, archive batch to specs/completed/{slug}/, spawn doc-garden agent
argument-hint: [path-to-feature-list (default: docs/feature-list.json)]
model: sonnet
---

Invoke the batch-gc skill (which owns the /finalize ceremony).

FEATURE_LIST: $ARGUMENTS or docs/feature-list.json (default)

Post-batch ceremony after all features reach terminal state (DONE or
BLOCKED) AND gen-dreamer + eval-dreamer have produced
`docs/progress/DREAM-gen.md` + `docs/progress/DREAM-eval.md`.

Four phases + commit:

1. **Dreamer Review** — parse P-NN proposals from DREAM-*.md; walk each
   through `AskUserQuestion(approve / reject / edit)`; apply approved
   changes to capsules / SKILL.md / anti-patterns / prunes.
2. **Promote** — glossary-draft merge into `CONTEXT.md`; codemap
   sync for new feature dirs; feature-barrel backlog pass into
   `docs/tech-debt-tracker.md`.
3. **Archive** — parse slug from `specs/_batch/plan.md` H1; move all
   spec + batch artifacts into `specs/completed/{slug}/`; summarize raw
   `docs/progress/F*-progress-R*.md` + `F*-eval-R*.md` into
   `BATCH_SUMMARY.md`; delete raw progress files.
4. **Scan** — spawn `doc-garden` agent for post-finalize drift scan;
   findings land in `docs/tech-debt-tracker.md`.
5. **Commit** — single `chore(finalize):` commit covering applied
   proposals + archived batch + scan findings.

Next step: `/prd` (for next batch).
