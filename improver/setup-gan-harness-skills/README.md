# setup-gan-harness-skills improver workspace

**Status**: maintainer-only (excluded from `copy_substrate.sh` because it lives outside `.claude/`).
**Pattern**: based on Anthropic's [skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md) iteration loop.

This workspace iterates on `.claude/skills/setup-gan-harness-skills/SKILL.md` (the bootstrap skill that scaffolds gan-harness into a target project) by running a deterministic test case + baseline + grader + human review per iteration.

## Loop summary

```
1. Pick test case (a prompt + an empty target dir scaffold + assertions)
2. Spawn TWO subagents in parallel:
   a. with-skill   → reads .claude/skills/setup-gan-harness-skills/SKILL.md, runs setup
   b. without-skill → no skill, just the prompt → setup-from-scratch attempt
3. Capture outputs to iteration-N/eval-X/{with_skill,without_skill}/
4. Grade each output against eval_metadata.json assertions (text/passed/evidence)
5. Aggregate into benchmark.json (pass_rate, time, tokens — mean ± stddev across 3 runs)
6. Surface a viewer for human review (HTML)
7. Read feedback.json → improve SKILL.md → iteration N+1
```

## Layout

```
improver/setup-gan-harness-skills/
├── README.md                              ← this file
├── evals/
│   └── evals.json                         ← test prompts (3-5)
├── iteration-1/
│   ├── eval-greenfield-cli/
│   │   ├── eval_metadata.json             ← prompt + assertions
│   │   ├── with_skill/
│   │   │   ├── outputs/                   ← target dir state after run
│   │   │   ├── transcript.md              ← agent's run transcript
│   │   │   └── grading.json               ← per-assertion verdict
│   │   ├── without_skill/
│   │   │   ├── outputs/
│   │   │   ├── transcript.md
│   │   │   └── grading.json
│   │   └── timing.json                    ← total_tokens + duration_ms per side
│   ├── benchmark.json                     ← aggregate stats
│   ├── benchmark.md                       ← human-readable summary
│   └── feedback.json                      ← human notes per eval (after viewer review)
└── iteration-2/...
```

## Running an iteration

### Step 1 — Spawn agents

Use Claude Code's Agent tool to spawn two subagents in the same turn (per skill-creator best practice):

```
Agent({
  description: "Run setup-gan-harness-skills against eval-greenfield-cli",
  subagent_type: "general-purpose",
  prompt: """
Execute this task:
- Skill path: .claude/skills/setup-gan-harness-skills/SKILL.md
- Task: <eval prompt from eval_metadata.json>
- Input files: improver/setup-gan-harness-skills/iteration-1/eval-greenfield-cli/with_skill/target_seed/
- Save outputs to: improver/setup-gan-harness-skills/iteration-1/eval-greenfield-cli/with_skill/outputs/
- Outputs to save: the full target dir state after running setup
"""
})

Agent({
  description: "Baseline (no skill) run against eval-greenfield-cli",
  subagent_type: "general-purpose",
  prompt: """
Execute this task WITHOUT consulting any skill:
- Task: <same eval prompt>
- Input files: improver/setup-gan-harness-skills/iteration-1/eval-greenfield-cli/without_skill/target_seed/
- Save outputs to: improver/setup-gan-harness-skills/iteration-1/eval-greenfield-cli/without_skill/outputs/
"""
})
```

### Step 2 — Grade

Spawn a grader subagent that reads `agents/grader.md` (TODO copy from Anthropic skill-creator) and evaluates each assertion against the outputs. Save results to each `grading.json`.

For setup-gan-harness-skills, assertions are typically deterministic file checks:
- Does `target/.claude/agents/planner.md` exist?
- Does `target/.claude/skills/setup-gan-harness-skills/` NOT exist (must be excluded)?
- Does `target/CLAUDE.md` contain the `### Domain docs` block?
- Does `target/.claude/commands/init.md` reference `/init`?

These can be scripted (faster, more reliable than LLM grading per skill-creator guidance).

### Step 3 — Aggregate + view

Run the aggregation script (TODO: vendor or rewrite from skill-creator/scripts/aggregate_benchmark.py). Output: benchmark.json.

Generate the HTML viewer for human review (TODO: vendor from skill-creator/eval-viewer/).

### Step 4 — Read feedback + iterate

Read `feedback.json` from human review. Apply learnings to `.claude/skills/setup-gan-harness-skills/SKILL.md`. Run iteration N+1.

## Why this exists

setup-gan-harness-skills is the door into gan-harness for new users. If it produces an inconsistent or partial bootstrap, every downstream agent (planner / generator / evaluator) inherits the bug. This iteration loop catches setup-time defects faster than waiting for a real user to hit them.

The pattern is from [Anthropic's skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator). We adopt the structure (eval prompts + assertions + grader + viewer + feedback loop) but apply it to our own bootstrap skill.

## Open work (TODO)

- [ ] Vendor `agents/grader.md` from skill-creator
- [ ] Vendor `scripts/aggregate_benchmark.py` from skill-creator
- [ ] Vendor `eval-viewer/generate_review.py` from skill-creator
- [ ] Run iteration 1 against the seeded eval cases below
- [ ] Document expected pass rate floor (target: 80%+ on greenfield-cli before considering setup-skills "stable")
