---
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion, TaskCreate, TaskUpdate, TaskList, Agent
description: Stage 1 — grill user intent in MAIN session + blindfold codebase research → produces specs/_batch/prd.md (per-batch PRD, all R as H2 sections) + specs/_batch/research.md (codebase facts with base_commit + timestamp). One human checkpoint post-grill.
argument-hint: "[intent dump or path to intent file] (optional — grill will ask if empty)"
model: opus
---

Invoke `.claude/skills/prd-workflow/SKILL.md`. The skill owns the phases,
subagent dispatches, checkpoint logic, and lint. This command only routes
control flow. When command and skill disagree, the skill wins — fix this
command.

1. Pre-flight (verify `specs/_batch/` is empty or only contains stale `_research-queue.md`; abort if `prd.md` / `feature-list.json` already present)
2. Phase 1 — Grill in MAIN session (load `prd-workflow/references/grill-protocol.md`; interview user one question at a time; reframe vague targets; produce `specs/_batch/prd.md` + `specs/_batch/_research-queue.md`)
3. Phase 2 — Post-grill checkpoint (single `AskUserQuestion {Approve / Revise / Abort}`)
4. Phase 3 — Codebase research dispatch (spawn `codebase-fact-finder × N` in parallel ≤6/turn, blindfold = `prd.md`)
5. Phase 4 — Synth (compile `specs/_batch/research.md`; run `prd_lint.py`; delete transient queue + findings dir)

Next step: /plan
