# gan-harness

A language-agnostic AI coding harness driven by a generator-evaluator
adversarial loop. Four commands — `/prd` `/plan` `/execution-loop`
`/finalize` — walk one batch from intent to merged code. The harness
core stays language-free; framework adaptation lives in pluggable
**stack skills** (Python, FastAPI, Next.js, AWS CDK, Flutter, etc.).
gan-harness sits in the **outer-harness** slot of Böckeler's three-layer
model — wrapped around the coding agent, not part of it.

## 1. Pipeline

```
/prd            grill in MAIN session + blindfold codebase research
  ↓             writes specs/_batch/prd.md + specs/_batch/research.md
/plan           planner self-verify + per-question checkpoint walk
  ↓             writes specs/_batch/feature-list.json + proposed ADRs
/execution-loop generator ↔ evaluator round-based feature delivery
  ↓             writes specs/_batch/progress.tsv + per-round eval JSONs
/finalize       promote ADRs, lazy-create CONTEXT.md, regen codemap, archive batch
```

### `/prd` — intent → verifiable spec

Grill the user in the MAIN session, dispatch blindfold `codebase-fact-finder`
agents in parallel for codebase questions, synthesize into a per-batch PRD.
**Inputs**: free-form intent dump (optional). **Outputs**:
`specs/_batch/prd.md` (one H2 section per R, six required sub-sections each)
+ `specs/_batch/research.md` (codebase facts with `base_commit` + timestamp).
**Single human checkpoint**: post-grill confirmation (Approve / Revise / Abort).

### `/plan` — spec → feature contract

`planner` subagent decomposes into vertical-slice features, runs the
three-script self-verify trio (`plan_validator` + `lift_capabilities` +
`plan_lint`), then MAIN walks every `open_question` and every proposed
ADR through one `AskUserQuestion` apiece (Approve / Edit / Escalate).
**Outputs**: `specs/_batch/feature-list.json` (the immutable contract
`/execution-loop` consumes) + `docs/adr/NNNN-*.md` × M with
`status: proposed`.

### `/execution-loop` — contract → code

Walk features in `depends_on` DAG order. Per feature: spawn `generator`
→ `evaluator` pairs in fresh-context subagents, up to 3 rounds. Verdict
triad: **PASS** / **FAIL** / **DEFERRED**. PASS → next feature; 3-round
FAIL → `status: deferred`; downstream features cascade to
`blocked-by-ancestor`. **Outputs**: `specs/_batch/progress.tsv` +
`_evals/F{NN}-R{N}.json` per round + `_traces/` from hooks.

### `/finalize` — close the batch

Branches on `feature.status` distribution. **Archive path** (all passed):
promote ADRs (`proposed` → `accepted` + retroactive `superseded_by`
backfill), merge Domain terms from `prd.md` into `CONTEXT.md`
(lazy-create on first batch), regen `CODEMAP.md` from barrel-file
docstrings, archive `specs/_batch/*` → `specs/completed/<slug>/`.
**Retro path** (any deferred): walk `open_questions` per
`AskUserQuestion`, hand fixes to the planner agent, reset affected
features to `status: todo` for a manual re-run of `/execution-loop`.

For per-stage detail (grill rules, `prd_lint` L01-L06, ADR three-test
gate, adversarial probe categories) see the corresponding
`.claude/skills/<workflow>/SKILL.md` and its `references/`.

## 2. Components

The harness is one **outer-harness** layer composed of four agent
roles, four skill tiers, and a fleet of computational sensors.

### 2.1 Agents (`.claude/agents/`)

Subagents are spawned in fresh context per invocation (no in-session
memory carry-over — Huntley's Ralph Wiggum semantics). MAIN orchestrates
the workflow; subagents do focused work and return.

| Agent | One-line responsibility | Used in | Auto-loaded skills |
|---|---|---|---|
| `planner` | Designs vertical-slice features + proposes ADRs | `/plan` | `planner-handbook`, `deep-module-handbook` |
| `codebase-fact-finder` | Answers ONE blindfold research question with file:line evidence | `/prd` | (none — stack-agnostic) |
| `generator` | Implements ONE feature as a vertical slice + writes tests | `/execution-loop` | `generator-handbook`, `deep-module-handbook` |
| `evaluator` | Verifies ONE feature against spec + emits structured eval JSON | `/execution-loop` | `evaluator-handbook`, `deep-module-handbook` |

Agents are **stack-agnostic** in the prompt body. Stack-specific tokens
(test runner, lint command, module-layout idiom) come from the active
stack skill at runtime.

### 2.2 Skills (`.claude/skills/`)

Four-tier taxonomy. Workflow skills orchestrate stages; agent handbooks
encode single-agent doctrine; approach handbooks encode cross-agent
methodology; stack skills vendor language/framework conventions.

| Tier | Examples | Role |
|---|---|---|
| Workflow | `prd-workflow`, `plan-workflow`, `harness-loop`, `finalize-workflow`, `stack-skill-creator`, `approach-handbook-creator`, `setup-gan-harness-skills` | Stage orchestrator (drives one `/cmd`) |
| Agent handbook | `planner-handbook`, `generator-handbook`, `evaluator-handbook` | Doctrine + references for ONE agent |
| Approach handbook | `deep-module-handbook` | Cross-agent methodology (Ousterhout + Pocock-DDD) |
| Stack | `python-fastapi`, `typescript-nextjs`, … (target-specific) | Language/framework idioms (vendored) |

`setup-gan-harness-skills` is **bootstrap-only** — it runs in the
gan-harness clone to copy `.claude/` into a target project, and is
hard-excluded from that copy by `copy_substrate.sh`.

### 2.3 Sensors (`.claude/hooks/` + skill `scripts/`)

The outer harness is a **cybernetic governor** — guides feed forward
into agents, sensors feed back from their output. **Computational
sensors** are deterministic (linters, schema validators, grep-for-AC-id);
**inferential sensors** are LLM-backed (the four agents above, when
their job is to verify or research). Computational sensors are heavily
underused in AI builds (Böckeler) — this project leans hard on them
before reaching for LLM-as-judge.

Computational sensors, grouped by stage:

| Stage | Sensor | Checks |
|---|---|---|
| `/prd` | `prd_lint.py` | PRD structural lint (L01 H1 / L02 R sections / L03 sub-sections / L04 Cohn stories / L05 AC checkboxes / L06 forbidden top-level) |
| `/plan` | `plan_validator.py` | JSON Schema 2020-12 + DAG cycles + `depends_on` resolve + priority ordering |
| `/plan` | `lift_capabilities.py` | Duplicate IDs (feature/AC/Q) + `decision_refs[]` resolve + `eval_anchors`/`must_not` uniqueness |
| `/plan` | `plan_lint.py` | Design lint (L10a phase-named features rejected / L10b UI features need `l5_smoke_path`) |
| `/execution-loop` | `.claude/hooks/block_pretool.py` | PreToolUse hook — blocks adversarial reads (generator ↔ evaluator private paths, fact-finder ↔ ticket) |
| `/execution-loop` | `.claude/hooks/log_subagent_stop.py` | SubagentStop hook — writes `_traces/F{NN}-{gen\|eval}-trace-R{N}.md` + per-round usage JSON + appends `progress.tsv` row |
| `/execution-loop` | `generator-handbook/scripts/gate_gen_precommit.py` | Generator's pre-commit batch — lint.fix → lint.check → typecheck → test.unit → AC literal coverage (inlined) → module ACL (inlined) |
| `/execution-loop` | `evaluator-handbook/scripts/gate_eval_postcommit.py` | Evaluator's L1 + L2 (+ optional L5) wrapper. Does NOT re-run AC coverage; the evaluator's grading process re-verifies AC literals adversarially |
| `/finalize` | `preflight.py` | Branch decision (archive vs retro) + quarantine expiry block |
| `/finalize` | `finalize_adr.py` | ADR `proposed` → `accepted` promotion + retroactive `superseded_by` backfill + `index.md` regen |
| `/finalize` | `merge_domain_terms.py` | Domain terms from `prd.md` H2 sections → `CONTEXT.md` (idempotent, lazy-creates) |
| `/finalize` | `regen_codemap.py` | Barrel-file docstrings → `CODEMAP.md` (lazy-creates) |
| `/finalize` | `archive_batch.sh` | Move `specs/_batch/*` → `specs/completed/<slug>/` |
| `/finalize` | `summarize_batch.py` | Per-batch summary from `feature-list.json` + eval JSONs |

All scripts are pure stdlib Python or POSIX shell. PASS/FAIL only — no
WARN, no STRICT, no PASS_WITH_TODO. The four agents (planner,
fact-finder, generator, evaluator) serve as the inferential sensors.

## 3. Three layers of constraint

Three independent layers of discipline shape what every agent does and
how every prompt is written. Each layer answers a different question.

### 3.1 Behavioral layer — the four lines

Generic AI-coding discipline, cross-stack, generic-LLM. Carried in
maintainer `CLAUDE.md` as the `Behavioral foundation`:

> 1. Don't assume. Don't hide confusion. Surface tradeoffs.
> 2. Minimum code that solves the problem. Nothing speculative.
> 3. Touch only what you must. Clean up only your own mess.
> 4. Define success criteria. Loop until verified.

Source: [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills)
(60k★) distilled from Karpathy's January 2026 thread on agent failure
modes; expanded analysis in [Liu's *The 4 Lines Every CLAUDE.md Needs*](https://levelup.gitconnected.com/the-4-lines-every-claude-md-needs-2717a46866f6).

**Line 4 in this project has a budget cap**: the loop is bounded at
3 rounds per feature; on round-3 FAIL the feature lands at
`status: deferred`. The cap exists because unbounded looping in a
multi-agent harness oscillates and burns cost — the *spirit* of Line 4
(verify, don't ship blind) is preserved by the deterministic sensors
in § 2.3.

### 3.2 Mechanism layer — seven universal rules

Harness-specific hard rules, schema-enforced and lint-enforced. Every
worker prompt inlines whichever rules apply to its role:

1. **No `deferred` punt.** Open questions resolve in the current batch
   or batch scope is wrong. Schema enum rejects `deferred` as a
   `resolution_kind`.
2. **No silent inference.** If a fact isn't established, surface as
   ambiguity or assumption — don't fill from training priors.
3. **PASS/FAIL only.** No WARN, no STRICT, no PASS_WITH_TODO. Lint
   scripts emit one of two states.
4. **No outsourcing without recommendation.** Ambiguities surface with
   the agent's recommended resolution + rationale; humans approve /
   edit / escalate, never decide blind.
5. **Lint is the contract.** Fix the source design when checks fight
   you, never patch around the check.
6. **Vertical slices, not horizontal phases.** Features cross every
   layer the requirement implies (`plan_lint L10a` rejects phase-named
   features).
7. **No fabricated provenance.** Quote what actually existed in input;
   surface interpretations under explicit `ASSUMPTIONS I'M MAKING`.

The **three-section worker-prompt structure** every agent inlines —
*Principles* (with mandatory assumption-surfacing) / *Common
Rationalizations* / *Anti-patterns* — is a domain instantiation of the
seven-section pattern visible in [Anthropic's own Claude Design system
prompt](https://github.com/elder-plinius/CL4R1T4S/blob/main/ANTHROPIC/Claude-Design-Sys-Prompt.txt)
(identity / capabilities / workflow / output / verification / …).

### 3.3 Design layer — deep modules + Pocock-DDD

Code-shape methodology, applied at design time by every agent that
touches `module_path` or interface boundaries. Loaded as the
`deep-module-handbook` approach skill.

- **Deep modules** (Ousterhout, Parnas): narrow interface hiding deep
  implementation. *No* quantitative threshold (the previous
  `depth_score ≥ 5` gate was dropped — Ousterhout gives no numeric
  anchor; the Unix I/O example with ~5 calls is a function count, not
  a depth ratio). All checks are qualitative red flags with
  primary-source citations.
- **Pocock-calibrated DDD**: Ubiquitous Language + Bounded Context +
  ADR adopted; entities / aggregates / value objects / domain events
  *not* adopted. ADR triggers from this layer are limited to "new or
  modified bounded-context boundary".
- **Information hiding** (Parnas) and the **deletion test** (Pocock)
  drive interface decisions: if a future read can be deleted without
  changing public behaviour, the public surface is too wide.

### 3.4 Design philosophy

From Pocock's [*Software Fundamentals Matter More Than Ever*](https://www.youtube.com/watch?v=v4F1gFy-hqg)
(AI Engineer, April 2026):

> **Code is not cheap.** Specs-to-code that re-runs the compiler on
> every fix produces ever-worse code (software entropy). Good
> codebases matter *more* in the AI age, not less.
>
> **Rate of feedback is your speed limit** (Pragmatic Programmer).
> Don't outrun your headlights — small deliberate steps with verified
> feedback.
>
> **Strategic vs tactical** (Ousterhout). AI is a great tactical
> programmer; humans must operate strategically — design the
> interface, delegate the implementation. "Invest in the design of
> the system every day" (Kent Beck).

This project picks **post-hoc verification** (generator writes code +
tests, evaluator verifies after) over TDD test-first; the survey of
GAN-style harnesses in our research bundle showed 7/7 are post-hoc.
The "rate of feedback = speed limit" principle still applies — enforced
through `gen_local_gate` (<5s pre-commit check), the `ac_coverage`
cascade, and the 3-round budget per feature.

## 4. Invariants

Hard rules that hold across every stage. Violating any one of these
indicates the design is wrong, not the rule.

- **Codebase as SSoT.** Alive docs (`CONTEXT.md`, ADRs, `CODEMAP.md`,
  `feature-list.json`) supplement only what code cannot express.
- **Language-free core.** `.claude/skills/{prd-workflow, plan-workflow,
  planner-handbook, harness-loop, finalize-workflow}/` MUST NOT contain
  language- or framework-specific tokens. Stack idioms live exclusively
  in `.claude/skills/<stack>/`.
- **Zero debt.** No `risks` / `tech_debt` / `cross_r_risks` field in any
  artefact. Every concern resolves to (a) a proposed ADR via the
  three-test gate, (b) an `open_question`, or (c) a feature/AC. Schema's
  `additionalProperties: false` mechanically rejects rogue debt fields.
- **ADR immutability.** Accepted ADR bodies are never edited. To revise,
  write a new ADR with `supersedes: [old_id]`; `/finalize` retroactively
  backfills `superseded_by` on the predecessor.
- **Vertical slices only.** Features cross all relevant layers
  end-to-end (UI → API → service → DB if full-stack). `plan_lint.py L10a`
  rejects horizontal-phase features.
- **Skill-shaped agent behaviour.** No agent code lives outside skills;
  agent prompts inline their constraint sections in their own voice
  (no cross-link to maintainer doctrine memos).
- **Single human checkpoint per stage.** Exactly one `AskUserQuestion`
  gate per stage: `/prd` post-grill / `/plan` per-Q walk / `/execution-loop`
  per-round verdict / `/finalize` pre-archive sweep. (The per-Q walk
  uses many `AskUserQuestion` calls but is one logical checkpoint.)

## 5. References

External sources this design draws on, and where each ref lands in
this README.

| Source | Lifted | Lands in |
|---|---|---|
| [Karpathy 4-lines series](https://x.com/karpathy/status/2015883857489522876) — [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) — [Liu's *The 4 Lines Every CLAUDE.md Needs*](https://levelup.gitconnected.com/the-4-lines-every-claude-md-needs-2717a46866f6) | Behavioral-layer four-line preamble; failure-mode framing (assumption / over-abstraction / scope creep); "behavioral constraints outperform feature checklists" | § 3.1 |
| [Anthropic Claude Design system prompt (CL4R1T4S)](https://github.com/elder-plinius/CL4R1T4S/blob/main/ANTHROPIC/Claude-Design-Sys-Prompt.txt) | Worker-prompt structured sectioning (identity / capabilities / workflow / output / verification) — domain-instantiated as Principles / Rationalizations / Anti-patterns | § 3.2 |
| Pocock, [*Software Fundamentals Matter More Than Ever*](https://www.youtube.com/watch?v=v4F1gFy-hqg) (18-min talk, AI Engineer 2026-04) | "Code is not cheap" / "rate of feedback is your speed limit" / strategic-vs-tactical division of labour | § 3.4 |
| [Pocock skills repo](https://github.com/mattpocock/skills) | grill-with-docs protocol; ADR three-test gate; deep-module discipline; setup-skills pattern; `disable-model-invocation: true` for setup skills | § 1 (`/prd`), § 3.3 |
| Böckeler, [*Harness Engineering for Coding Agents*](https://martinfowler.com/articles/harness-engineering.html) | inner / outer / orchestrator three-layer model; guides + sensors vocabulary; "computational sensors are heavily underused" thesis | Top intro, § 2.3 |
| Rajasekaran (Anthropic), [*Harness design for long-running app dev*](https://www.anthropic.com/engineering/harness-design-long-running-apps) | planner / generator / evaluator triangle; GAN-inspired adversarial loop; sprint-construct retroactively dropped in V2 (we adopted that retreat) | § 1, § 2.1 |
| Anthropic, [*Effective harnesses for long-running agents*](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) | feature-list.json as immutable contract; structured handoff between sessions | § 1 (`/plan`) |
| [Anthropic skill-creator](https://github.com/anthropics/skills/tree/main/skills/skill-creator) | Evaluator eval JSON schema (`text` / `passed` / `evidence` / `claims` / `eval_feedback`) — fields kept verbatim for tooling compatibility | § 2.1 evaluator |
| Karpathy, [*autoresearch*](https://github.com/karpathy/autoresearch) | Flat append-only `progress.tsv`; git-as-state; rejection of agent-authored narrative reports | § 1 (`/execution-loop`) |
| [OpenAI Symphony](https://github.com/openai/symphony) | Naming the orchestrator as a separate layer; `WORKFLOW.md`-style in-repo policy file; workspace lifecycle hooks | Top intro; future scaling reference |
| Ousterhout, *A Philosophy of Software Design* + Parnas, *Information hiding* | Deep-module principle (narrow interface, deep implementation); information hiding | § 3.3 |
| Huntley, [*Ralph Wiggum*](https://ghuntley.com/ralph) | External-loop reload-each-iteration semantics — why subagent spawns are fresh-context per round, not in-session stop-hook re-feeds | § 2.1 |
| matklad, [*ARCHITECTURE.md*](https://matklad.github.io/2021/02/06/ARCHITECTURE.md.html) | "absence-of-X" invariants framing; terse-list discipline | § 4 |
| Horthy, [*Everything We Got Wrong About Research-Plan-Implement*](https://www.youtube.com/watch?v=YwZR6tc7qYg) | Blindfold research; vertical slices not horizontal phases; plan as transient tactical doc | § 1, § 2.1 (`fact-finder`) |
| Osmani, [*spec-driven-development*](https://github.com/addyosmani/agent-skills/blob/main/skills/spec-driven-development/SKILL.md) | `ASSUMPTIONS I'M MAKING` pattern; reframe-vague-targets for measurable success criteria | § 1 (`/prd` grill), § 3.2 |

## 6. Quick start

1. Bootstrap a stack skill at `.claude/skills/<your-stack>/`. Invoke
   `stack-skill-creator` to walk through it.
2. Run `/prd` with a free-form intent dump (or empty — grill will ask).
3. Run `/plan` — consumes `/prd`'s outputs, produces
   `specs/_batch/feature-list.json`.
4. Run `/execution-loop` — walks features in `depends_on` DAG order,
   max 3 rounds per feature.
5. Run `/finalize` — promotes ADRs, merges Domain terms, regens
   codemap, archives the batch.

To drop the harness into a fresh project, run the
`setup-gan-harness-skills` skill from inside a gan-harness clone — it
copies `.claude/` into the target, scaffolds stack skills, and wires
agent frontmatter.

## 7. Status

Steps 1–5 done (May 2026):

- `feature-list.schema.json` (the contract) ✓
- `/plan` + `planner` agent + `planner-handbook` ✓
- `/prd` + grill protocol + blindfold research ✓
- `/execution-loop` + `generator` + `evaluator` + `harness-loop` ✓
- `/finalize` (ADR promotion + Domain-term merge + codemap + archive) ✓

Side bundles delivered: `stack-skill-creator`, `setup-gan-harness-skills`,
`deep-module-handbook`, mechanical-sensor batch (T16: 8 ADRs + 5
sensors + self-tests + e2e smoke).

Open: T15 e2e bundle (PBT lane + `playwright-cli` + computer-use bundle
for evaluator L5), T17 dreamer (post-batch proposal agents).

Past handoff state lived in `TODO.md`; from now on, design changes
flow through ADRs and git history.
