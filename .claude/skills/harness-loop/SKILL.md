---
name: harness-loop
description: Drive Stage 2 of the gan-harness v3.8 — walk the sprint plan in specs/_epic/spec.md, dispatch per-sprint research (brownfield), per sprint negotiate a contract (generator+evaluator), implement, evaluate against the contract's verification_plan + 4 archetype criteria. Append to contracts.jsonl. No max round budget; the loop runs until evaluator approves or operator stops based on cost. Make sure to use this skill whenever /loop runs, when the user asks to execute the spec, or when handoff from /init to /finalize needs the running app + verdicts.
disable-model-invocation: false
---

# harness-loop

Stage 2 of v3.8. Walks `specs/_epic/spec.md`'s sprint plan. Per sprint:

1. Research dispatch (brownfield only, per-sprint fresh)
2. Negotiate contract (generator ↔ evaluator)
3. Implement (generator)
4. Evaluate (evaluator emits next_action directive)
5. PASS → next sprint; FAIL → obey next_action (refine | restart_sprint | escalate_to_user)

GAN loop with adversarial pressure between generator and evaluator. No
escalate mechanism beyond evaluator's `next_action: escalate_to_user` —
the loop runs until evaluator approves, evaluator escalates, or operator
stops externally.

## Mandatory before starting

ASSUMPTIONS I'M MAKING:
1. `specs/_epic/spec.md` exists and has been approved at `/init`.
2. `specs/_epic/intent.md` exists (written at /init Phase 0).
3. The active stack skill provides a running app and the test runner commands the evaluator's `verification_plan` will reference.
4. The user has not set a hard cost budget I should respect (if they have, the operator will halt externally).

If `specs/_epic/spec.md` is missing, ABORT. /init must run first.

## Common rationalisations

| Rationalization | Reality |
|---|---|
| "Round 5 evaluator FAIL is close enough, mark as completed" | No. PASS is binary; evaluator decides, not the loop driver. |
| "Generator's been on this sprint a while, let me lower the threshold" | No. Thresholds were negotiated at contract time; lowering them is a contract amendment that requires evaluator approval. |
| "I'll skip negotiation and let generator just implement against spec.md" | No. Per-sprint negotiation is load-bearing; it's how high-level spec becomes testable contract. |
| "Sprint 3 has 30 findings, I'll pause and ask the user" | No. Evaluator emits `next_action`; loop obeys. If evaluator wrote `escalate_to_user`, surface the failure report; otherwise let generator refine or restart per the directive. |
| "Evaluator returned approve; I'll skip writing the contracts.jsonl entry" | No. contracts.jsonl is the source of truth for sprint state. |
| "I'll skip research dispatch for this sprint, generator can read the codebase directly" | No. Per-sprint research gate is the fresh-codebase-state mechanism — questions were approved at /loop start, fact-finder runs per-sprint to reflect current state. Skipping = generator reads stale assumptions. |
| "Generator returned but the next_action says restart_sprint; I'll let it refine instead" | No. Evaluator owns the pivot decision. MAIN obeys `next_action` verbatim. |

## Inputs

- `specs/_epic/spec.md` — the immutable rubric.
- `specs/_epic/intent.md` — user's intent dump (used by MAIN session at /loop start to draft research questions; blindfolded from fact-finder by `block_pretool.py`).
- `specs/_epic/contracts.jsonl` — append-only log of negotiated contracts.
- `specs/_epic/_research/S{NN}/_questions.json` — per-sprint frozen question lists (drafted at /loop start, dispatched per-sprint).
- `python .claude/skills/harness-loop/scripts/epic_status.py` — derive current state.
- `python .claude/skills/harness-loop/scripts/question_lint.py` — deterministic gate on `_questions.json` before user approval.
- Active stack skill (auto-discovered).
- Hooks: `block_pretool.py` (PreToolUse — spec.md / contracts.jsonl / docs/adr / amendment immutability + blindfolds), `log_subagent_stop.py` (SubagentStop — trace + progress.tsv).

## Process

### Phase 0 — Pre-flight

1. Verify `specs/_epic/spec.md` exists.
2. Read `epic_status.py --json` to determine state.
3. If `epic_done` is true, ABORT with: "epic already complete; run /finalize".
4. If `_research/S*/_questions.json` files do NOT yet exist for any sprint, go to Phase 0.5 (research-question drafting); otherwise skip to Phase 1 with the noted `active_sprint`.

### Phase 0.5 — Research-question drafting (runs once at /loop start)

This phase runs ONCE per /loop invocation, before any sprint begins. MAIN session:

1. Read EXACTLY these inputs and nothing else:
   - `specs/_epic/spec.md`
   - `specs/_epic/intent.md`
   - `specs/_epic/contracts.jsonl` (if it exists — for prior completed sprints' agreed contracts)

   **Do NOT** grep / Read any codebase file (no `DESIGN.md`, no `package.json`, no source files under `src/` / `app/` / etc.). Drafting context must stay in the **concept space**, not the **file space**. If MAIN has already seen `DESIGN.md` before this phase, it will leak that knowledge into the question phrasing — see the Q06 lint rule for the deterministic catch, but the prompt-level discipline starts here. The asker is blindfolded from the codebase by convention; fact-finder is blindfolded from the spec+intent by hook (`block_pretool.py`).
2. For each sprint in `## Sprint plan`, draft a list of blindfold codebase-fact-finder questions based on the sprint's User story + Success (user POV) bullets + Smoke check + prior completed sprints' contracts. Greenfield sprints (no codebase dependencies) → empty list. Questions describe the **concept** the sprint needs to know about (e.g., "What color tokens describe form input states for this project?"); they do not name the file the answer lives in (the fact-finder discovers that).
3. Write each sprint's question list to `specs/_epic/_research/S{NN}/_questions.json` using EXACTLY this schema (no extra fields):
   ```json
   {
     "sprint": "S{NN}",
     "questions": [
       {"id": "kebab-case-id", "question": "What ...?", "rationale": "..."}
     ]
   }
   ```

   **Forbidden fields and patterns** (enforced by `question_lint.py`):
   - **No `target_files` field** (Q05). Fact-finder discovers WHERE facts live — telling it the file pre-supposes the answer's location. If the convention isn't where you guessed, you'll get a misleading "not found".
   - **No filename in question text** (Q06). `What ... in DESIGN.md?` / `What ... in package.json?` — both pre-suppose a target file. Rephrase to ask about the concept: `What color tokens are defined for this project?` / `What frontend package manager and workspace configuration does this project use?`. The fact-finder finds the file; the question describes the concept.
   - **No design-asking verbs** (Q02): recommend / suggest / propose / how should / what should / approach for. Fact-finder documents what IS, not what SHOULD be.
   - **No goal language** (Q01): we want / we need / should / would it be good. Pure neutral fact-finding only.
   - **First word must be fact-form** (Q03): What / Which / How / Where / Does / Is / Are / List / Name.

   Note: domain terms from spec.md (e.g., `workspace`, `session`, `snapshot`) ARE allowed in question text — that's how you describe the concept you're researching. The lint does NOT flag spec-vocabulary overlap.
4. Run `python .claude/skills/harness-loop/scripts/question_lint.py specs/_epic/_research/S{NN}/_questions.json` on each file. Any FAIL → fix the question text and rerun. PASS required before proceeding.
5. Print all drafted questions to the user grouped by sprint and ask: "Review the per-sprint questions. Edit / approve / skip any. Type APPROVE to freeze."
6. On user APPROVE, freeze the JSON files (they become read-only by convention; question_lint runs once and never again unless user manually re-edits and re-approves).

After Phase 0.5 settles, proceed to Phase 1 for the active sprint.

### Phase 0.6 — Per-sprint research dispatch (at the start of EACH sprint)

Before Phase 1 (negotiate) for sprint S{NN}:

1. Read `specs/_epic/_research/S{NN}/_questions.json`. Empty `questions: []` → skip to Phase 1.
2. Dispatch K `codebase-fact-finder` subagents **in parallel** — one Agent tool call per question, all in a single message so they execute concurrently. Each subagent prompt MUST be self-contained (subagents start in a fresh context with no view of `intent.md`, `spec.md`, or sibling questions — `block_pretool.py` enforces this blindfold via deny rules). Pass each agent: (a) the `question` verbatim, (b) the `rationale`, (c) the required output path `specs/_epic/_research/S{NN}/<id>.md`.
3. Wait for all K subagents to return. Verify each `_research/S{NN}/<id>.md` exists; if any is missing, re-dispatch only the missing ones. Fact-finder writes what it found; no `confidence` field, no human-in-the-loop for sparse answers — generator works with what's there.

After Phase 0.6, proceed to Phase 1 for sprint S{NN}.

### Phase 1 — Negotiate (per sprint S{NN})

Both agents auto-load `deep-module-handbook` via their frontmatter — generator follows `generator-slice §1.5`, evaluator follows `evaluator-slice §1.5`. The contract-mechanics handbooks (generator-handbook / evaluator-handbook) compose with these slices.

For round R = 1, 2, 3, ... (no cap):

0. **Set trace context** (first action this round, before any spawn): run `python .claude/skills/harness-loop/scripts/epic_status.py --set-context S{NN} {R}`. Skipping ⇒ this round's trace + progress row land as PENDING/Round 0.
1. **Spawn generator** with prompt: "Propose contract for sprint S{NN}. Read spec.md, `_research/S{NN}/*.md`, recent contracts.jsonl. Write `_pending/S{NN}-draft-v{R}.yaml` with verification_plan length >= 20 steps."
2. **Spawn evaluator** (separate fresh ctx) with prompt: "Review the contract draft at `_pending/S{NN}-draft-v{R}.yaml`. Write `_pending/S{NN}-review-v{R}.yaml` with verdict (approve | amend_request | reject) and next_action (proceed_to_implement | refine_contract | restart_contract — mechanically derived from verdict)."
3. **Check verdict + next_action**:
   - `approve` (next_action: proceed_to_implement) → MAIN merges draft into `contracts.jsonl` with timestamp and `phase: agreed`. Proceed to Phase 2.
   - `amend_request` (next_action: refine_contract) → generator re-spawns with prompt: "Amend draft per review at v{R}." Increment R, loop.
   - `reject` (next_action: restart_contract) → generator re-spawns: "Contract rejected. Propose new contract from scratch." Increment R, loop.
4. After 5 negotiation rounds without agreement, surface this rare event in stdout for operator visibility; evaluator should `approve` the strongest available draft on round 5.

### Phase 2 — Implement (per sprint S{NN}, given agreed contract)

For implementation round IR = 1, 2, 3, ... (no cap):

0. **Set trace context** (first action this round, before the spawn): run `python .claude/skills/harness-loop/scripts/epic_status.py --set-context S{NN} {IR}`.
1. **Spawn generator** with prompt: "Implement sprint S{NN} per agreed contract. Read spec.md, contracts.jsonl[latest agreed for S{NN}], `_research/S{NN}/*.md`. On round IR ≥ 2, also read `_evals/S{NN}-R{IR-1}.json` and obey its `next_action` directive (refine | restart_sprint | escalate_to_user) — generator does NOT strategic-decide. Run inner gate, commit once."
2. Generator writes code, runs inner gate, commits. Optionally writes `_pending/S{NN}-commit-R{IR}-rationale.yaml` per `.claude/schemas/rationale.schema.md`.
3. SubagentStop hook captures transcript → `_traces/S{NN}-gen-R{IR}.jsonl`.
4. **Post-round trace strengthening (optional but recommended)**: run `python .claude/skills/harness-loop/scripts/anchor_ledger.py --sprint S{NN} --round {IR}` and `python .claude/skills/harness-loop/scripts/divergence_diff.py --sprint S{NN} --round {IR}`. Reports land in `_audit/S{NN}/`; evaluator reads them during VERIFY.

### Phase 3 — Evaluate (per sprint S{NN}, after generator commit)

0. **Set trace context** (before the spawn): run `python .claude/skills/harness-loop/scripts/epic_status.py --set-context S{NN} {IR}`.
1. **Spawn evaluator** (fresh ctx) with prompt: "Verify sprint S{NN} round IR. Read in locked order: spec.md → contracts.jsonl[latest agreed for S{NN}] → `_traces/S{NN}-gen-R{IR}.jsonl[start:end]` → git diff → `_audit/S{NN}/anchor-ledger-R{IR}.tsv` + `_audit/S{NN}/divergence-R{IR}.md` (if present). Run verification_plan + matrix sensor. Emit `_evals/S{NN}-R{IR}.json` with dual-axis envelope + top-level `next_action`."
2. Evaluator runs verification; on FAIL determines `next_action` per the rules in `.claude/agents/evaluator.md > ## Next-action determination`.
3. Evaluator writes `_evals/S{NN}-R{IR}.json`:
   - `contract_axis.{criteria, findings, verdict}`
   - `standards_axis.{matrix_sensor, module_design_verification, findings, verdict}`
   - top-level `verdict` (AND of two axis verdicts)
   - top-level `next_action` (proceed on PASS; refine | restart_sprint | escalate_to_user on FAIL)
4. SubagentStop hook captures evaluator's transcript → `_traces/S{NN}-eval-R{IR}.jsonl`.

### Phase 4 — Decide

Read `_evals/S{NN}-R{IR}.json`:

- **verdict: PASS** (`next_action: proceed`) → MAIN appends `phase: completed` entry to `contracts.jsonl` with `evidence_ref` pointing into the transcript slice. Loop back to Phase 0 to find next active sprint (or done).
- **verdict: FAIL with next_action: refine** → increment IR, loop back to Phase 2. Generator reads `_evals/S{NN}-R{IR}.json` directly and addresses findings with same approach.
- **verdict: FAIL with next_action: restart_sprint** → increment IR, loop back to Phase 2. Generator reverts touched files to sprint-start state and re-implements with a different approach.
- **verdict: FAIL with next_action: escalate_to_user** → STOP. Surface `_pending/S{NN}-failure-R{IR}.md` (which generator wrote in its next round's escalate path) OR ask generator to write one. Print to stdout: `ESCALATE: sprint S{NN} next_action=escalate_to_user; see _pending/S{NN}-failure-R{IR}.md`. Wait for operator decision.

MAIN does NOT merge, rerank, truncate, or translate the findings or override `next_action`. The evaluator's verdict is authoritative.

### Termination

Loop terminates when:
- `epic_status.py --is-done` returns 0 (all sprints `phase: completed`)
- OR evaluator emits `next_action: escalate_to_user` and operator decides to stop
- OR operator interrupts externally (Ctrl+C)

### Cost monitoring (operator-side, not enforced)

The harness has no max-rounds cap. Operator monitors token spend externally. If a sprint exhausts the operator's budget, halt the loop manually. Evaluator's `escalate_to_user` directive after 4+ rounds without PASS is the harness's built-in signal that human judgement is needed.

## Outputs

- `specs/_epic/contracts.jsonl` — append-only contract log.
- `specs/_epic/_pending/S{NN}-{draft|review}-v{N}.yaml` — ephemeral negotiation artefacts.
- `specs/_epic/_pending/S{NN}-commit-R{N}-rationale.yaml` — optional pre-commit rationale (generator-authored).
- `specs/_epic/_pending/S{NN}-failure-R{N}.md` — escalate failure report (generator-authored when `next_action: escalate_to_user`).
- `specs/_epic/_evals/S{NN}-R{N}.json` — per-round evaluator verdict + `next_action`.
- `specs/_epic/_research/S{NN}/_questions.json` — per-sprint question list (drafted at /loop start, frozen after user approval).
- `specs/_epic/_research/S{NN}/<id>.md` — per-sprint fact-finder output (written per-sprint at Phase 0.6).
- `specs/_epic/_audit/S{NN}/anchor-ledger-R{N}.tsv` — anchor verification ledger.
- `specs/_epic/_audit/S{NN}/divergence-R{N}.md` — un-anchored identifier report.
- `specs/_epic/_traces/S{NN}-{gen|eval}-R{N}.jsonl` — hook-captured transcripts.
- `specs/_epic/progress.tsv` — hook-appended metric rows.

## Anti-patterns

**Skipping negotiation phase.** Per-sprint contract is load-bearing. Without it, generator implements against vague spec; evaluator has no rubric to check against.

**Letting MAIN edit contracts.jsonl in place.** Append-only. New entries go on new lines. Editing an existing entry is a hook violation.

**Running QA against spec.md instead of the contract.** spec.md is high-level. Per-sprint contract is the rubric. QA reads contract.

**Operator-interrupted runs leaving state inconsistent.** When operator Ctrl+Cs mid-sprint, the next /loop invocation should resume from where it stopped. epic_status.py derives that.

**Spawning generator without giving it the active sprint id.** Generator needs to know which sprint to work on. Use `epic_status.py --active-sprint` and pass into the spawn prompt.

**Spawning generator and evaluator in the same fresh context.** They must be in separate fresh-context subagents. Don't reuse one for both.

**Overriding evaluator's `next_action`.** MAIN obeys verbatim. If evaluator wrote `restart_sprint`, generator restarts; if `refine`, generator refines; if `escalate_to_user`, MAIN stops.

**Skipping Phase 0.6 fact-finder dispatch.** Per-sprint research is the fresh-codebase-state mechanism. Even if Phase 0.5 questions look stale, dispatch fresh — fact-finder running at sprint kickoff captures the current codebase (post prior-sprints).

**Dispatching all sprints' fact-finders at /loop start.** No. Questions are drafted upfront and frozen; fact-finder dispatch is per-sprint at Phase 0.6 so answers reflect the codebase state AT THAT SPRINT's start, not /loop start.

**Reading codebase files at Phase 0.5 (drafting time).** No. The asker is blindfolded from the codebase. MAIN reads ONLY `spec.md` + `intent.md` + prior `contracts.jsonl` at drafting time. Grepping / Reading `DESIGN.md`, `package.json`, source files, etc. pollutes the question with location knowledge — questions like `What X in DESIGN.md?` directly reveal MAIN saw that file. The Q06 lint catches the leak in the output, but the discipline starts at the input side: don't read what you don't need.

## Scripts

- `scripts/epic_status.py` — derive current state (active sprint, done, rounds_seen).
- `scripts/question_lint.py` — deterministic gate on `_questions.json` (Q01 no goal language, Q02 no design asking, Q03 fact-form opener required, Q04 no solution-leak from spec.md).
- `scripts/anchor_ledger.py` — post-round anchor verification ledger.
- `scripts/divergence_diff.py` — post-round un-anchored identifier report.
