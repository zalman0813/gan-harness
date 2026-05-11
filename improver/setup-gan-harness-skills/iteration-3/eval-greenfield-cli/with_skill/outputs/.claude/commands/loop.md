---
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent, TaskCreate, TaskUpdate, TaskList
description: Stage 2 of v3.8 — walk specs/_epic/spec.md sprint plan, per-sprint negotiate contract (generator+evaluator), implement, evaluate. Append to contracts.jsonl. No max round budget; the loop runs until evaluator approves OR operator stops based on cost. Hand off to /finalize when all sprints completed.
argument-hint: "(no args; reads state from specs/_epic/)"
model: sonnet
---

Invoke `.claude/skills/harness-loop/SKILL.md`. The skill owns the phases,
generator/evaluator subagent dispatches, contract negotiation, MAIN
deterministic merge, threshold check. This command only routes control
flow. When command and skill disagree, the skill wins — fix this command.

1. Pre-flight (verify `specs/_epic/spec.md` exists + passes lint; verify
   epic not already done via `epic_status.py --is-done`)
2. Outer loop: while sprints remaining (active-sprint via
   `epic_status.py --active-sprint`):
   - Phase 1 — Negotiate (spawn generator → propose_contract; spawn
     evaluator → review_contract; iterate; agreed → append to
     contracts.jsonl)
   - Phase 2 — Implement (spawn generator with agreed contract; commit;
     SubagentStop hook captures transcript)
   - Phase 3 — Evaluate (spawn evaluator; run verification_plan; emit
     `_evals/S{NN}-R{N}.json`)
   - Phase 4 — Decide (PASS → contracts.jsonl append phase:completed →
     next sprint; FAIL → MAIN merge feedback → next round, no cap)
3. Termination (epic_status.py --is-done == 0 OR operator interrupt)

Next step: /finalize
