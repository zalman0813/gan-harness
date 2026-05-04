---
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent, TaskCreate, TaskUpdate, TaskList
description: Stage 3 — walk specs/_batch/feature-list.json, drive generator ↔ evaluator pairs (max 3 rounds per feature), set feature.status. Outputs specs/_batch/progress.tsv + per-feature eval JSONs + per-round traces. Hand off to /finalize when done.
argument-hint: "(none — reads /plan's outputs from specs/_batch/)"
model: opus
---

Invoke `.claude/skills/harness-loop/SKILL.md`. The skill owns the phases,
the DAG walk, and the round-loop logic. This command only routes control
flow. When command and skill disagree, the skill wins — fix this command.

1. Pre-flight (verify `specs/_batch/feature-list.json` exists + schema valid; abort if missing — `/plan` must run first)
2. Phase 1 — Topological walk (per `todo` feature in DAG order: spawn generator → evaluator pair, max 3 rounds, write terminal `feature.status`, cascade `blocked-by-ancestor` to downstream)
3. Phase 2 — Summary (counts by status; pointer to /finalize)

Next step: /finalize
