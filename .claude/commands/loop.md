---
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent, TaskCreate, TaskUpdate, TaskList
description: Stage 2 of v3.8 — at /loop start, draft per-sprint research questions + user approves. Then walk specs/_epic/spec.md sprint plan; per sprint dispatch fresh fact-finder + negotiate contract (generator+evaluator) + implement + evaluate. Evaluator emits next_action (proceed | refine | restart_sprint | escalate_to_user); MAIN obeys verbatim. Append to contracts.jsonl. No max round budget; the loop runs until evaluator approves OR operator stops based on cost. Hand off to /finalize when all sprints completed.
argument-hint: "(no args; reads state from specs/_epic/)"
model: sonnet
---

Invoke `.claude/skills/harness-loop/SKILL.md`. The skill owns the phases, generator/evaluator subagent dispatches, contract negotiation, per-sprint research dispatch, MAIN deterministic merge, next_action obedience. This command only routes control flow. When command and skill disagree, the skill wins.

1. **Pre-flight** — verify `specs/_epic/spec.md` exists; verify epic not already done via `epic_status.py --is-done`.

2. **Phase 0.5 — research-question drafting (runs ONCE at /loop start)**:
   - MAIN drafts per-sprint blindfold questions based on spec.md + intent.md + prior completed sprints.
   - For each sprint, write `specs/_epic/_research/S{NN}/_questions.json`.
   - Run `question_lint.py` on each (Q01 no goal language / Q02 no design asking / Q03 fact-form opener / Q04 no spec keyword leak).
   - Surface to user grouped by sprint; user APPROVE freezes the files.

3. **Outer loop**: while sprints remaining (active-sprint via `epic_status.py --active-sprint`):
   - **Phase 0.6 — per-sprint research dispatch**: read `_research/S{NN}/_questions.json`; dispatch K `codebase-fact-finder` subagents in parallel (single message, blindfolded by `block_pretool.py` from intent.md / spec.md / prd.md / sibling research). Each writes `_research/S{NN}/<id>.md` with whatever it found (no `confidence` field; generator works with what's there).
   - **Phase 1 — Negotiate**: spawn generator → propose contract (VP length >= 20); spawn evaluator → review_contract → emit `_pending/S{NN}-review-v{R}.yaml` with verdict + next_action (proceed_to_implement | refine_contract | restart_contract); iterate; on `approve` MAIN appends to contracts.jsonl.
   - **Phase 2 — Implement**: spawn generator with agreed contract. On round IR ≥ 2, generator reads `_evals/S{NN}-R{IR-1}.json` and obeys its top-level `next_action` (refine | restart_sprint | escalate_to_user). Commit; SubagentStop hook captures transcript. Optionally run `anchor_ledger.py` + `divergence_diff.py` post-round.
   - **Phase 3 — Evaluate**: spawn evaluator; read trace + diff + audit reports; run verification_plan + matrix sensor; emit `_evals/S{NN}-R{IR}.json` with dual-axis envelope + top-level `next_action`.
   - **Phase 4 — Decide**:
     - PASS (next_action: proceed) → contracts.jsonl append `phase: completed` → next sprint.
     - FAIL with next_action: refine → next round, same approach.
     - FAIL with next_action: restart_sprint → next round, generator reverts and re-designs.
     - FAIL with next_action: escalate_to_user → STOP, surface `_pending/S{NN}-failure-R{IR}.md`, wait for operator decision.

4. **Termination** — `epic_status.py --is-done == 0` OR evaluator escalate OR operator interrupt.

### What changed from v3.8.0

- Research moved here from /init. Phase 0.5 + 0.6 are new.
- Evaluator emits `next_action`; generator obeys verbatim. No more generator strategic-decide refine vs pivot.
- VP threshold: contract must have ≥ 20 verification_plan steps.
- Evaluator has harsh-critic stance + bias toward `restart_sprint` over `refine`.

Next step: /finalize
