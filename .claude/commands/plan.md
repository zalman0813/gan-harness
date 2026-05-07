---
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion, TaskCreate, TaskUpdate, TaskList, Agent
description: Stage 2 — planner self-verify + per-Q checkpoint walk. Reads /prd's outputs (specs/_batch/prd.md + specs/_batch/research.md). Produces specs/_batch/feature-list.json + new docs/adr/NNNN-*.md (status:proposed).
argument-hint: "(none — reads /prd's outputs from specs/_batch/)"
model: opus
---

Invoke `.claude/skills/plan-workflow/SKILL.md`. The skill owns the phases,
scripts, and checkpoint logic. This command only routes control flow. When
command and skill disagree, the skill wins — fix this command.

1. Pre-flight (verify `specs/_batch/prd.md`, `specs/_batch/research.md`, schema; abort if missing — `/prd` must run first)
2. Phase 1 — Planner self-verify (spawn `planner` agent; runs three-script trio; max 3 rounds)
3. Phase 2 — Per-Q checkpoint walk (one `AskUserQuestion` per open_question + per proposed ADR; options Approve / Edit / Escalate-or-Reject; re-run trio after each Edit/Reject)

Next step: /execution-loop
