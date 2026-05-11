---
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion, TaskCreate, TaskUpdate, TaskList, Agent
description: Stage 3 of v3.8 — close out a /loop epic. Archive-only path (v3.8 removed retro path along with escalate). Verifies all sprints completed via epic_status.py --is-done; promotes proposed ADRs to accepted; merges new domain terms into CONTEXT.md; regenerates CODEMAP.md; archives specs/_epic/ → specs/epics/<slug>/. Single git commit.
argument-hint: "(none — reads specs/_epic/)"
model: sonnet
---

Invoke `.claude/skills/finalize-workflow/SKILL.md`. The skill owns the
phases and scripts. This command only routes control flow. When command
and skill disagree, the skill wins — fix this command.

1. Pre-flight (`epic_status.py --is-done` → exit 0; refuse otherwise with
   "/loop must complete first")
2. Phase 1 — Promote ADRs (`finalize_adr.py`: proposed → accepted +
   retroactive supersedes backfill + index regen)
3. Phase 2 — Merge domain terms (`merge_domain_terms.py`: spec.md → CONTEXT.md, idempotent, lazy-creates)
4. Phase 3 — Regen CODEMAP (`regen_codemap.py`: barrel docstrings → CODEMAP.md)
5. Phase 4 — Archive (`archive_batch.sh`: mv specs/_epic/* → specs/epics/<slug>/)
6. Phase 5 — Single commit (`git add docs/adr/ CONTEXT.md CODEMAP.md specs/epics/<slug>/`)
7. Phase 6 — Summary (epic name, sprints completed, ADRs promoted, terms added, archive path)

Next step: /init (for next epic)
