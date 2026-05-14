---
name: harness-loop
description: Drive Stage 2 of the gan-harness v3.8 — walk the sprint plan in specs/_epic/spec.md, per sprint negotiate a contract (generator+evaluator), implement, evaluate against the contract's verification_plan + 4 archetype criteria. Append to contracts.jsonl. No max round budget; the loop runs until evaluator approves or operator stops based on cost. Make sure to use this skill whenever /loop runs, when the user asks to execute the spec, or when handoff from /init to /finalize needs the running app + verdicts.
disable-model-invocation: false
---

# harness-loop

Stage 2 of v3.8. Walks `specs/_epic/spec.md`'s sprint plan. Per sprint:

1. Negotiate contract (generator ↔ evaluator)
2. Implement (generator)
3. Evaluate (evaluator)
4. PASS → next sprint; FAIL → another round (no cap)

This is the v2 GAN loop from Anthropic's harness research: per-sprint
negotiation followed by behavioral verification. There is **no escalate**
mechanism — the loop runs until evaluator approves or the operator stops
the run externally based on cost.

## Mandatory before starting

ASSUMPTIONS I'M MAKING:
1. `specs/_epic/spec.md` exists and has been approved at `/init`.
2. The active stack skill provides a running app and the test runner
   commands the evaluator's `verification_plan` will reference.
3. The user has not set a hard cost budget I should respect (if they
   have, the operator will halt externally — I don't enforce it).

If `specs/_epic/spec.md` is missing, ABORT. /init must run first.

## Common rationalisations

| Rationalization | Reality |
|---|---|
| "Round 5 evaluator FAIL is close enough, mark as completed" | No. PASS is binary; the evaluator decides, not the loop driver. |
| "Generator's been on this sprint a while, let me lower the threshold" | No. Thresholds were negotiated at contract time; lowering them is a contract amendment that requires evaluator approval. |
| "I'll skip negotiation and let generator just implement against spec.md" | No. Per-sprint negotiation is load-bearing in v2; it's how high-level spec becomes testable contract. Skipping = generator is implementing against vague intent. |
| "Sprint 3 has 30 findings, I'll pause and ask the user" | No. There is no escalate. Pass findings to generator; let them strategic-decide refine vs pivot. The user is opted out of per-round decisions. |
| "Evaluator returned approve; I'll skip writing the contracts.jsonl entry" | No. contracts.jsonl is the source of truth for sprint state. Without the entry, epic_status.py thinks the sprint isn't done. |
| "Standards axis has the same finding round-on-round, contract keeps changing — I'll prioritise contract because it's the user-facing axis" | No. Per-axis anti-oscillation: same finding on the same axis 3 rounds → mandatory pivot for that axis. The generator strategic-decides by reading raw `_evals/*.json`; MAIN does not rerank or filter findings. |

## Inputs

- `specs/_epic/spec.md` — the immutable rubric (vision + features + sprint
  plan + 4 criteria).
- `specs/_epic/contracts.jsonl` — append-only log of negotiated contracts.
  Driver reads to find current sprint state; generator/evaluator read for
  context.
- `python .claude/skills/harness-loop/scripts/epic_status.py` — derive
  current state (active sprint, completion).
- Active stack skill (auto-discovered via `.claude/skills/<stack>/`).
- Hooks:
  - `block_pretool.py` PreToolUse — enforces spec.md immutability,
    contracts.jsonl append-only, agent-private path blindfolds.
  - `log_subagent_stop.py` SubagentStop — captures `transcript_path` per
    subagent stop, writes `_traces/S{NN}-{gen|eval}-R{N}.jsonl` with line
    range markers, appends row to `progress.tsv`.

## Process

### Phase 0 — Pre-flight

1. Verify `specs/_epic/spec.md` exists.
2. Read `epic_status.py --json` to determine state.
3. If `epic_done` is true, ABORT with: "epic already complete; run
   /finalize".
4. Note the `active_sprint` (call it S).

### Phase 1 — Negotiate (per sprint S)

Both agents auto-load `deep-module-handbook` via their frontmatter — at
NEGOTIATE time, generator follows `generator-slice §1.5` (per-module
commitments inside `done_looks_like[]`) and evaluator follows
`evaluator-slice §1.5` (spot-check checklist + APPROVE / REQUEST_CHANGES
/ REJECT vocabulary). The contract-mechanics handbooks
(generator-handbook / evaluator-handbook) compose with these slices,
not replace them.

For round R = 1, 2, 3, ... (no cap):

1. **Spawn generator** with prompt: "Propose contract for sprint S.
   Read spec.md and recent contracts.jsonl. Use propose_contract tool to
   write `_pending/S{NN}-draft-v{R}.yaml`."
2. **Spawn evaluator** (separate fresh ctx) with prompt: "Review the
   contract draft at `_pending/S{NN}-draft-v{R}.yaml`. Use review_contract
   tool to write `_pending/S{NN}-review-v{R}.yaml` with verdict approve |
   amend_request | reject."
3. **Check verdict**:
   - approve → MAIN merges draft into `contracts.jsonl` with timestamp
     and `phase: agreed`. Proceed to Phase 2.
   - amend_request → generator re-spawns with prompt: "Amend draft per
     review at v{R}." Increment R, loop.
   - reject → generator re-spawns with broader rethink: "Contract
     rejected. Propose new contract from scratch." Increment R, loop.
4. After 5 negotiation rounds without agreement, the evaluator should
   `approve` the strongest available draft (negotiation cannot itself
   loop forever). If not, surface this rare event in stdout for operator
   visibility.

### Phase 2 — Implement (per sprint S, given agreed contract)

For implementation round IR = 1, 2, 3, ... (no cap):

1. **Spawn generator** with prompt: "Implement sprint S per agreed
   contract. Read spec.md, contracts.jsonl[latest agreed for S], and (if
   IR ≥ 2) `_evals/S{NN}-R{IR-1}.json` (the evaluator's raw dual-axis
   verdict — no MAIN merge) and `_traces/S{NN}-gen-R{IR-1}.jsonl`.
   Strategic-decide refine vs pivot based on prior round."
2. Generator writes code, runs inner gate, commits.
3. SubagentStop hook captures transcript → `_traces/S{NN}-gen-R{IR}.jsonl`.

### Phase 3 — Evaluate (per sprint S, after generator commit)

1. **Spawn evaluator** (fresh ctx) with prompt: "Verify sprint S round
   IR. Read in locked order: spec.md → contracts.jsonl[latest agreed for
   S] → `_traces/S{NN}-gen-R{IR}.jsonl[start:end]` → git diff. Run
   verification_plan + matrix sensor. Emit `_evals/S{NN}-R{IR}.json`
   with **dual-axis** shape per evaluator.md VERIFY mode (contract_axis
   + standards_axis + top-level verdict)."
2. Evaluator runs `gate_eval.py` (in evaluator-handbook scripts) which
   actually executes the verification.
3. Evaluator writes `_evals/S{NN}-R{IR}.json` with the dual-axis
   envelope: `contract_axis.{criteria, findings, verdict}`,
   `standards_axis.{matrix_sensor, module_design_verification, findings, verdict}`,
   plus top-level `verdict` = AND of the two.
4. SubagentStop hook captures evaluator's transcript →
   `_traces/S{NN}-eval-R{IR}.jsonl`.

### Phase 4 — Decide

Read `_evals/S{NN}-R{IR}.json` top-level `verdict`:

- **verdict: PASS** (both `contract_axis.verdict` AND
  `standards_axis.verdict` are `PASS`) → MAIN appends `phase: completed`
  entry to `contracts.jsonl` with `evidence_ref` pointing into the
  transcript slice. Loop back to Phase 0 to find next active sprint (or
  done).
- **verdict: FAIL** (either axis FAIL) → increment IR, loop back to
  Phase 2. The next-round generator reads `_evals/S{NN}-R{IR}.json`
  directly (both `contract_axis.findings[]` and
  `standards_axis.findings[]` verbatim). **MAIN does not merge, rerank,
  truncate, or translate the findings.** This mirrors Anthropic's
  generator-evaluator design (Harness design for long-running
  application development): "Communication was handled via files: one
  agent would write a file, another agent would read it" — there is no
  middleman that could dilute the evaluator's authority by re-ordering
  or capping its output.

### Termination

Loop terminates when:
- `epic_status.py --is-done` returns 0 (all sprints `phase: completed`)
- OR operator interrupts externally (Ctrl+C) — there is no internal halt

### Cost monitoring (operator-side, not enforced)

The harness has no max-rounds cap. Operator monitors token spend
externally. If a sprint is stuck on the same finding **on the same
axis** for 3+ rounds:
- generator is supposed to pivot per the per-axis anti-oscillation rule
  (generator-handbook): "same finding-on-same-axis 3 rounds → mandatory
  pivot for that axis." A finding that appears in contract-axis R1 then
  standards-axis R2 then contract-axis R3 is NOT three matches — the
  anti-oscillation trigger is per-axis-per-finding.
- if generator is genuinely stuck, operator decides whether to interrupt
- the harness driver does NOT decide

## Outputs

- `specs/_epic/contracts.jsonl` — append-only contract log.
- `specs/_epic/_pending/S{NN}-{draft|review|amendment}-v{N}.yaml` —
  ephemeral negotiation artefacts.
- `specs/_epic/_evals/S{NN}-R{N}.json` — per-round evaluator verdict.
  Next-round generator reads this directly on FAIL; no derived
  feedback.md exists.
- `specs/_epic/_traces/S{NN}-{gen|eval}-R{N}.jsonl` — hook-captured
  transcripts.
- `specs/_epic/progress.tsv` — hook-appended metric rows.

## Anti-patterns

**Skipping negotiation phase.** Per-sprint contract is load-bearing in
v2. Without it, generator implements against vague spec; evaluator has
no rubric to check against; both work blindfolded.

**Letting MAIN edit contracts.jsonl in place.** Append-only. New entries
go on new lines. Editing an existing entry is a hook violation.

**Running QA against spec.md instead of the contract.** spec.md is
high-level. Per-sprint contract is the rubric. QA reads contract.

**Operator-interrupted runs leaving state inconsistent.** When operator
Ctrl+Cs mid-sprint, the next /loop invocation should resume from where
it stopped. epic_status.py derives that — the latest `phase` per sprint.

**Spawning generator without giving it the active sprint id.** Generator
needs to know which sprint to work on. Use `epic_status.py
--active-sprint` and pass into the spawn prompt.

**Spawning generator and evaluator in the same fresh context.** They
must be in separate fresh-context subagents (Anthropic v2 cognitive
separation). Don't reuse one for both.

## Scripts

- `scripts/epic_status.py` — derive current state (active sprint, done,
  rounds_seen). Used by the loop driver and by external operators
  monitoring progress.
- `scripts/gate_eval.py` (TODO Phase D+, evaluator-handbook owns the
  actual implementation) — runs the verification_plan against running
  app and emits `_evals/S{NN}-R{N}.json`.
