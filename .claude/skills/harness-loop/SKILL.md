---
name: harness-loop
description: Drive Stage 3 of the gan-harness — walk the depends_on DAG of specs/_batch/feature-list.json one feature at a time, spawn generator → evaluator pairs up to 3 rounds per feature, write per-feature status, and produce a batch summary pointing at /finalize. The contract is locked at /plan time; this stage only executes. Make sure to use this skill whenever /execution-loop runs, when the user asks to execute a batch's feature list, or when handoff from /plan to /finalize needs implementations + verdicts.
---

# Harness Loop

The orchestration skill for `/execution-loop`. Walks `specs/_batch/feature-list.json`,
drives generator ↔ evaluator pairs, writes terminal `feature.status`. Stops when
all features are terminal (passed / deferred / blocked-by-ancestor).

## Mandatory before starting

ASSUMPTIONS I'M MAKING:
1. <e.g., "specs/_batch/feature-list.json was produced by /plan and validates against the schema">
2. <e.g., "the active stack skill provides L1/L2 commands compatible with feature.test_contract">
3. ...
→ Correct me now or I'll proceed with these.

If `specs/_batch/feature-list.json` is missing or fails schema validation,
ABORT. /plan must run first.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "Round 3 evaluator FAIL is close enough, mark as passed" | No. Three rounds is the budget; FAIL after R3 → status `deferred`. /finalize handles. |
| "Generator hit an error, I'll re-spawn without counting the round" | No. Every spawn counts. Three rounds total. |
| "Evaluator says DEFERRED but I disagree, I'll override" | No. Verdict is the evaluator's call. The harness records and moves on. |
| "This feature's dependency is `deferred`, but I think it could still work, let me try" | No. `blocked-by-ancestor` cascades automatically. Override = ignoring the open question that caused the upstream defer. |
| "I'll skip writing the row to progress.tsv since the trace already records this" | No. progress.tsv is the human-facing summary; trace is auditable detail. Both required. |

## Inputs

- `specs/_batch/feature-list.json` — the contract; planner-locked at /plan
- `specs/_batch/_traces/current-context.json` — written by this skill before
  each spawn so the SubagentStop hook knows which (feature, round) the
  trace belongs to
- Active stack skill (auto-discovered via `.claude/skills/<stack>/`) — for
  L1/L2/L5 conventions when generator/evaluator delegate
- `block_pretool.py` PreToolUse hook — blocks reads of the other agent's
  private paths
- `log_subagent_stop.py` SubagentStop hook — writes
  `specs/_batch/_traces/F{NN}-{gen|eval}-trace-R{N}.md`, appends a row
  to `specs/_batch/progress.tsv`, and writes per-round token-usage JSON
  next to the trace

## Process

### Phase 0 — Pre-flight

1. Verify `specs/_batch/feature-list.json` exists and parses as JSON.
2. Validate against `.claude/schemas/feature-list.schema.json` (use
   `jsonschema` if installed; else best-effort parse + structural check).
3. Read all features. Build the DAG via `depends_on`. Detect cycles —
   abort if any.
4. Detect any feature already at terminal status from a prior run
   (`passed` / `deferred` / `blocked-by-ancestor`). These are skipped.
5. Ensure `specs/_batch/_traces/` and `specs/_batch/_evals/` exist.

### Phase 1 — Topological walk

Repeat until no `todo` features remain (or the queue is exhausted by
upstream cascades):

1. **Pick next feature.** Find the lowest-id feature with `status: todo`
   whose every `depends_on` entry has `status: passed`. If none:
   - If any `todo` feature has any `deferred` / `blocked-by-ancestor`
     dependency → mark THIS feature `blocked-by-ancestor`, continue.
   - If no eligible feature exists at all → exit Phase 1.
2. **Round loop** (rounds 1, 2, 3):
   1. Write `specs/_batch/_traces/current-context.json`:
      ```json
      {"feature": "F03", "round": 1}
      ```
      The hook reads this on subagent stop.
   2. **Spawn generator.** `Agent(subagent_type="generator", prompt="Implement
      feature F03 from specs/_batch/feature-list.json. This is round 1.")`.
      Wait for return.
      - On generator error / timeout → mark feature `deferred`, break
        round loop, log to progress.tsv with note `"generator-error"`.
   3. **Spawn evaluator.** `Agent(subagent_type="evaluator", prompt="Evaluate
      feature F03 round 1 implementation against specs/_batch/feature-list.json
      and the eval JSON contract.")`. Wait for return.
      - On evaluator error / timeout → mark feature `deferred`, break,
        note `"evaluator-error"`.
   4. **Read verdict** from `specs/_batch/_evals/F03-R1.json` (the
      evaluator's eval JSON). Pull `verdict` field (PASS/FAIL/DEFERRED).
      AC literal coverage is part of the evaluator's grading process —
      a missing AC-NN literal in the test body produces an `expectations[]`
      row with `passed: false`, contributing to FAIL.
   5. **Branch on verdict:**
      - `PASS` → set `feature.status = "passed"` in feature-list.json;
        break round loop.
      - `DEFERRED` → set `feature.status = "deferred"`; break round loop.
      - `FAIL` and `round < 3` → continue round loop (round += 1).
      - `FAIL` and `round == 3` → set `feature.status = "deferred"`
        (treated same as DEFERRED for /finalize purposes); break.

   The previous "ac_coverage gate short-circuit before evaluator spawn"
   step has been removed. Generator self-checks AC literals in
   `gate_gen_precommit.py`; evaluator independently re-verifies as part
   of its grading. The hook layer no longer runs ac_coverage.
3. **Cascade.** When a feature hits `deferred` or `blocked-by-ancestor`,
   immediately mark every direct downstream feature (i.e. every feature
   whose `depends_on` includes this id) as `blocked-by-ancestor`. The
   cascade is transitive — re-run the cascade pass until no change.

### Phase 2 — Summary

When Phase 1 exits, count features by status and emit:

```
Batch <batch_slug> — execution summary

passed: N
deferred: M
blocked-by-ancestor: K

Next: /finalize  (handles archive vs retro path based on these statuses)
```

If any features are `deferred` (or `blocked-by-ancestor`), the
/finalize retro path will surface them per-Q via AskUserQuestion. The
operator's expected next action: review `progress.tsv` + the deferred
features' eval JSONs, then run `/finalize`.

## Outputs

- `specs/_batch/feature-list.json` — every feature has terminal status
- `specs/_batch/_traces/F{NN}-{gen|eval}-trace-R{N}.md` per round (hook-written)
- `specs/_batch/_evals/F{NN}-R{N}.json` per evaluator run (evaluator-written)
- `specs/_batch/progress.tsv` — append-only flat log; one row per agent stop (hook-written)
- Final summary in MAIN session output (counts + next-step pointer)

## Anti-patterns

**Spawning both agents in parallel.** Generator must finish committing
before evaluator runs — evaluator reads `git diff <base>..HEAD`.
Sequential, not parallel.

**Re-running a round.** If evaluator returned, the round is over. No
"that didn't seem right, let me re-spawn." If you disagree with the
verdict, the next operator-facing action is /finalize's retro walk.

**Editing feature-list.json before round 3.** Only the harness-loop
itself writes `feature.status`. Generator and evaluator must not touch
feature-list.json. If they do, the schema's `additionalProperties:
false` doesn't help — generator/evaluator must self-discipline.

**Skipping the cascade pass.** When a feature hits `deferred`, every
downstream must immediately become `blocked-by-ancestor` so the next
loop iteration sees the cascade. Forgetting this causes the harness to
pointlessly run rounds for downstream features that will fail anyway.

**Forgetting to write current-context.json.** The hook needs (feature,
round) to name the trace file correctly. Skipping the context write
results in trace files at `specs/_batch/_traces/<agent>-<ts>.md` (the
fallback path), which breaks the harness-loop's per-(feature, round)
lookup downstream. Always write it before each spawn.
