---
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion, TaskCreate, TaskUpdate, TaskList, Agent
description: Stage 4 — close out a /execution-loop batch. Archive path (all passed) promotes ADRs, merges Domain terms, regens CODEMAP, archives to specs/completed/{slug}/, single commit. Retro path (any deferred) walks open_questions per AskUserQuestion, routes fixes to planner agent, resets features to todo for re-run.
argument-hint: "(none — reads specs/_batch/feature-list.json)"
model: sonnet
---

Invoke `.claude/skills/finalize-workflow/SKILL.md`. The skill owns the
phases, scripts, and branch logic. This command only routes control flow.
When command and skill disagree, the skill wins — fix this command.

1. Pre-flight (`scripts/preflight.py` — verifies feature-list, all features
   terminal, prd.md present; outputs `SLUG`, `BRANCH=archive|retro`)
2. If `BRANCH=retro`: walk each deferred feature's open_questions via
   AskUserQuestion (Approve / Edit / Escalate); spawn `planner` agent with
   scoped amendment prompt; reset affected features to `todo`; report and
   stop (no commit)
3. If `BRANCH=archive`: single AskUserQuestion checkpoint (Approve / Edit
   slug / Abort); promote ADRs (`finalize_adr.py`); merge Domain terms
   (`merge_domain_terms.py`); regen CODEMAP (`regen_codemap.py`);
   summarize + archive (`summarize_batch.py` + `archive_batch.sh`); single
   `chore(finalize):` commit; report

Next step:
- Archive path → `/prd` (for next batch)
- Retro path → `/execution-loop` (re-run features just reset to todo)
