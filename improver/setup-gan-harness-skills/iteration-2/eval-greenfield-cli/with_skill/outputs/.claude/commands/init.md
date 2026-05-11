---
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, AskUserQuestion, TaskCreate, TaskUpdate, TaskList, Agent
description: Stage 1 of v3.8 — turn free-form user intent into specs/_epic/spec.md (immutable high-level spec). Default behaviour grills via AskUserQuestion; --no-grill bypasses. Single human checkpoint post-spec via AskUserQuestion (approve / revise / abort), bypassed by --no-confirm. Optionally dispatches codebase-fact-finder subagents in parallel for brownfield epics. Replaces v1's /prd + /plan combo.
argument-hint: "[intent dump or path] [--no-grill] [--no-confirm] [--archetype <name>]"
model: opus
---

Invoke `.claude/skills/init-workflow/SKILL.md`. The skill owns the phases,
planner subagent dispatch, fact-finder spawn logic, lint, and checkpoint.
This command only routes control flow. When command and skill disagree,
the skill wins — fix this command.

1. Pre-flight (verify `specs/_epic/` does not exist or has been archived;
   abort if previous epic still live)
2. Spawn planner agent with the intent dump + flags. Planner grills via
   AskUserQuestion (default), optionally dispatches fact-finder for
   brownfield, drafts `specs/_epic/spec.md`, self-verifies via
   `python .claude/skills/init-workflow/scripts/spec_lint.py`. Iterate
   until lint PASSes.
3. Final approval checkpoint (single AskUserQuestion: approve / revise /
   abort). Bypassed by `--no-confirm`. On revise, planner re-engages with
   feedback. On abort, delete `specs/_epic/`.

Next step: /loop
