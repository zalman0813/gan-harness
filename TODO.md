# TODO

Handoff state for resuming gan-harness construction. Read this + `ARCHITECTURE.md` + `CONTEXT.md` + `docs/agent-prompt-doctrine.md` before picking up work.

## 5-step plan progress

| # | Step | Status | Task IDs |
|---|---|---|---|
| 1 | `feature-list.schema.json` (the contract) | ✓ done | (pre-T2) |
| 2 | `/plan` + planner agent + planner-handbook | ✓ done | T2–T6 |
| 3 | `/prd` + per-batch PRD lint | ✓ done | T7 |
| 4 | Generator + evaluator (stack-aware) + harness-loop | □ pending | **T8** |
| 5 | `/finalize` update for new ADR + CONTEXT.md lifecycle | □ pending | **T9** |

Side: T10 stack-skill-creator ✓, T11 Pocock-style CONTEXT + decisions→adr ✓, T12 setup-gan-harness-skills (init scaffolder) □, T13 Pocock-doctrine optimization sweep ✓.

---

## Locked decisions (do not re-litigate)

These were debated and resolved during T13. Future tasks (T7/T8/T9/T12) inherit them. Re-opening any of these requires a new ADR, not a quiet change.

### Pipeline shape

- `/prd` does grill + blindfold codebase research + synth in a single stage. Output: **`specs/_batch/prd.md` + `specs/_batch/research.md`** (batch-level — single files with H2 sections per R, NOT per-R subdirs).
- `/plan` reads those two files only. No Phase 1 research — that's done. Phase 1 = planner self-verify (three-script trio). Phase 2 = per-Q checkpoint walk.
- `/execution-loop` reads `feature-list.json`, writes code.
- `/finalize` consolidates: promote ADRs (proposed → accepted), merge Domain terms from prd.md into CONTEXT.md, regen codemap, archive batch.
- ADR files live in `docs/adr/` from the moment planner writes them (`status: proposed`); /finalize promotes status, never moves files.

### Artefact set (3 active types per batch + master ADRs)

```
specs/_batch/
├── prd.md            # epic-level, all R as H2 sections + Domain terms draft per R
├── research.md       # epic-level, blindfold codebase facts + base_commit + timestamp
└── feature-list.json # planner sharding output

docs/adr/*.md         # M proposed → accepted ADRs, master tree
```

No `requirement.md`, no `glossary-draft.md`, no `questions.md`, no `intake.md`. Those were sketched in earlier rounds and consciously dropped.

### open_question contract

- `resolution_kind` enum has **three** values only: `feature_local`, `architectural`, `glossary`.
- No `deferred`. Every question resolves in-batch or batch scope is wrong.
- `resolution` is a non-empty string at all times — schema enforces. Planner writes their recommendation; user reviews at /plan Phase 2 walk.
- If planner cannot recommend an answer, escalate (do not write null, do not stall).

### ADR three-test gate

Before writing any ADR, all three must be true:
1. Hard to reverse
2. Surprising without context
3. Result of a real trade-off

Any one fails → not an ADR. Route to `spec.business_rules` or `spec.open_questions` instead. See `planner-handbook/references/adr-lifecycle.md` § When to offer an ADR.

### Phase 2 per-Q checkpoint walk (replaces bulk approve)

`/plan` Phase 2 walks every open_question and every proposed ADR individually via `AskUserQuestion`:

- For open_questions: Approve / Edit / **Escalate** (escalate aborts batch back to /prd for re-scope).
- For ADRs: Approve / Edit / Reject (reject removes the ADR file + cleans `decision_refs`; planner re-routes the concern).

After each Edit/Reject, re-run the three-script trio before continuing the walk.

### Doctrine

`docs/agent-prompt-doctrine.md` is the SSoT for the universal constraint layer every worker prompt embeds:

- Mandatory before starting (surface assumptions explicitly)
- Common Rationalizations (per-agent table, 5±2 rows)
- Universal rules (no deferred, no silent inference, no WARN, no outsourcing without recommendation, lint is contract, vertical slices, no fabricated provenance)

Catalogue of all per-agent rationalization tables lives in that file. When adding a new agent, add its table there + copy into the agent prompt. Both must stay in sync.

### Lazy creation (T12 implication)

`setup-gan-harness-skills` (T12) emits ONLY:
- `ARCHITECTURE.md` template (matklad form, invariant placeholders for the user)
- `README.md` template
- `.claude/` tree (copy from harness)
- `specs/_batch/.gitkeep`, `specs/completed/.gitkeep`

It does NOT pre-create:
- `CONTEXT.md` — first /finalize merge creates it lazily
- `docs/adr/` + `index.md` — first ADR proposal creates the dir; first /finalize regen creates index.md
- `app_docs/codemap.md` — first /finalize regen_codemap.py run creates it

---

## T7 — Step 3: `/prd` + prd-workflow ✓ DONE

**Delivered** (May 2026):

- `.claude/agents/grill-master.md` — grilling subagent with doctrine three sections, Cohn user-story format, transient research-queue output
- `.claude/skills/prd-workflow/SKILL.md` — 4-phase orchestration (Pre-flight / Grill / Post-grill checkpoint / Research dispatch / Synth)
- `.claude/skills/prd-workflow/scripts/prd_lint.py` — PASS/FAIL structural lint (L01 H1, L02 R sections, L03 sub-sections, L04 Cohn stories, L05 AC checkboxes, L06 forbidden top-level)
- `.claude/commands/prd.md` — thin command

**Decisions made during T7 implementation** (locked, do not re-litigate):

- Format reference (`CONTEXT-FORMAT`) inlined into `grill-master.md` under § Output format. SKILL.md stayed under 200 lines so split was not needed.
- No `prd.schema.json` — prd.md is markdown; `prd_lint.py` enforces structure.
- Transient files: `specs/_batch/_research-queue.md` (grill-master output → fact-finder input → deleted at synth) and `specs/_batch/_research-findings/Q-NN.md` (fact-finder output → compiled into research.md → directory deleted at synth).
- Pre-flight rule: if `specs/_batch/` contains `prd.md` or `feature-list.json`, abort (prior batch must be /finalize-archived first). If only `_research-queue.md` is stale, delete and proceed.
- Post-grill checkpoint is the SINGLE human checkpoint per ARCHITECTURE.md invariant. Grill itself uses many AskUserQuestion turns but those are conversation, not gates. Three options: Approve / Revise / Abort.
- Research is non-interactive after Phase 2 checkpoint. Fact-finder failures surface in research.md as `Unanswerable` / `Unverified` entries; user reviews at /plan time, not at /prd.
- prd_lint.py runs at end of Phase 4 synth. Failure blocks /prd from declaring done.

---

## T8 — Step 4: generator + evaluator + harness-loop

**Goal**: Stage 3 of the pipeline. Walk features in `depends_on` DAG order; per feature, generator writes code → evaluator verifies → loop up to 3 rounds; emit DONE/BLOCKED.

**Deliverables**:
- `.claude/agents/generator.md` — stack-aware via active stack skill delegation; reads feature spec + AC + active stack skill recipes; writes code + tests. Embed doctrine three sections (generator rationalization table).
- `.claude/agents/evaluator.md` — read-only verifier; runs L1 (compile/lint) + L2 (unit) + L5 (smoke) from `test_contract`; greps `eval_anchors`; asserts `must_not`; emits PASS/FAIL with violation list. Embed doctrine three sections (evaluator rationalization table).
- `.claude/skills/harness-loop/SKILL.md` — round orchestration (max 3), feedback channel from evaluator → generator. Embed doctrine three sections.
- `.claude/commands/execution-loop.md` — thin command.

**Open question for T8 implementation**: TDD-style (evaluator writes failing test FIRST, generator makes it pass) vs post-hoc (generator writes both code and test, evaluator verifies). Pocock's `tdd` skill is the closest analogue to TDD-style. Defer decision to T8 implementation; document the trade-off in the eventual generator/evaluator agent prompts.

---

## T9 — Step 5: `/finalize` update

**Goal**: Replace the legacy `commands/finalize.md` + `skills/batch-gc/` (heavily out-of-date — references gen-dreamer/eval-dreamer, `docs/feature-list.json` at root which doesn't exist, `docs/tech-debt-tracker.md` which is removed, and the singular `docs/glossary.md` which has been replaced by `CONTEXT.md`).

**Deliverables**:
- Rewrite `.claude/commands/finalize.md` thin command.
- Rewrite `.claude/skills/batch-gc/SKILL.md` (or rename `finalize-workflow`) — drives:
  1. ADR proposed→accepted via `scripts/finalize_adr.py` (already written, language-free)
  2. Domain terms merge: scan `specs/_batch/prd.md` H2 sections, extract Domain terms draft per R, dedupe across R, merge into `CONTEXT.md` Language section. **If `CONTEXT.md` does not exist (first batch in target project), lazy-create with H1 stub before merging.**
  3. `app_docs/codemap.md` regen via `scripts/regen_codemap.py` (already written). **Lazy-create if missing.**
  4. Archive `specs/_batch/` → `specs/completed/<slug>/`.
- Single human checkpoint at "approve archive" (per ARCHITECTURE.md invariant § Single human checkpoint per stage).
- Embed doctrine three sections (finalize-workflow rationalization table from catalogue).

**Already in place**:
- `scripts/finalize_adr.py` — proposed→accepted + retroactive supersedes backfill + index.md regen.
- `scripts/regen_codemap.py` — barrel-file docstring extraction.
- `docs/adr/index.md` stub.
- `app_docs/codemap.md` stub.

---

## T12 — setup-gan-harness-skills (init scaffolder)

**Goal**: Init skill that scaffolds the per-repo substrate gan-harness expects when dropped into a fresh project.

**Inspired by Pocock's `setup-matt-pocock-skills`** (read: `https://github.com/mattpocock/skills/blob/main/skills/engineering/setup-matt-pocock-skills/SKILL.md`).

**Decision points to walk user through one-at-a-time**:

| Section | Question | Default | What gets written |
|---|---|---|---|
| **A. Project identity** | name + one-line description | (ask) | `README.md` template |
| **B. Stack(s)** | which language/framework(s)? | (ask; invoke `stack-skill-creator` per stack) | `.claude/skills/<stack>/` × N |
| **C. Domain layout** | single CONTEXT.md vs multi-context with CONTEXT-MAP.md | single | (write nothing — lazy) |
| **D. ADR location** | `docs/adr/` (Pocock + MADR convention) | `docs/adr/` | (write nothing — lazy) |

**Always-emitted scaffolding**:
- `ARCHITECTURE.md` template (matklad form; invariant placeholders for user to fill per project)
- `README.md` template
- `.claude/` tree (copy from harness)
- `specs/_batch/.gitkeep`, `specs/completed/.gitkeep`
- `docs/agent-prompt-doctrine.md` (copy verbatim — universal constraint layer)

**Lazy** (DO NOT pre-create):
- `CONTEXT.md`
- `docs/adr/` + `index.md`
- `app_docs/codemap.md`

**Pocock's interaction protocol** (must adopt):
1. Explore first (`git remote -v`, look for existing `CLAUDE.md` / `AGENTS.md` / `CONTEXT.md` / `docs/adr/`). Don't assume.
2. Present findings + ask one section at a time. Each section starts with explainer (what / why / what-changes-if-different) before showing choices.
3. Show drafts before writing. Let user edit before commit.
4. Idempotent / non-destructive. If a section already exists, update in-place, don't append duplicates. Never overwrite user edits to surrounding sections.
5. Pick CLAUDE.md OR AGENTS.md, never both. If neither exists, ask which to create — don't pick.
6. `disable-model-invocation: true` in frontmatter — setup is user-invoked only, not auto-loaded.

**Distribution model open question**:
- (a) Copy `.claude/` tree on setup — target project owns frozen copy
- (b) Symlink `.claude/` to harness clone — target follows harness HEAD
- (c) Plugin package via `npx skills@latest add ...` — target installs gan-harness via npm
- Recommendation: (a) for MVP. Revisit (c) when harness is mature.

**Doctrine**: embed three sections; rationalization table from catalogue (setup-gan-harness-skills row).

---

## Pocock skills as design reference

`mattpocock/skills` (`https://github.com/mattpocock/skills`) is the strongest external reference. Key files to read before T7/T8/T9/T12:

| Pocock skill | Why relevant | URL |
|---|---|---|
| `to-prd` | Direct PRD template | `skills/engineering/to-prd/SKILL.md` |
| `grill-with-docs` | Grill + CONTEXT.md update inline + ADR lazy creation | `skills/engineering/grill-with-docs/SKILL.md` |
| `grill-with-docs/CONTEXT-FORMAT.md` | The format spec for CONTEXT.md producers | `skills/engineering/grill-with-docs/CONTEXT-FORMAT.md` |
| `grill-with-docs/ADR-FORMAT.md` | ADR template + three-test gate | `skills/engineering/grill-with-docs/ADR-FORMAT.md` |
| `tdd` | Generator/evaluator alternative model | `skills/engineering/tdd/SKILL.md` |
| `diagnose` | Bug-fix loop discipline | `skills/engineering/diagnose/SKILL.md` |
| `improve-codebase-architecture` | Deep-module refactor doctrine | `skills/engineering/improve-codebase-architecture/SKILL.md` |
| `setup-matt-pocock-skills` | T12 template | `skills/engineering/setup-matt-pocock-skills/SKILL.md` |
| `setup-matt-pocock-skills/domain.md` | Substrate-consumer protocol | same dir |

Raw URL pattern: `https://raw.githubusercontent.com/mattpocock/skills/main/<path>`

---

## Files to consult before resuming

- `ARCHITECTURE.md` — 7 invariants the system must not violate
- `CONTEXT.md` — domain ubiquitous language (Pocock-style, slim)
- `docs/agent-prompt-doctrine.md` — universal constraint layer every worker prompt embeds
- `README.md` — pipeline diagram + project layout
- `.claude/agents/planner.md` — example agent definition with full doctrine three sections
- `.claude/skills/plan-workflow/SKILL.md` — example workflow skill with doctrine
- `.claude/skills/planner-handbook/SKILL.md` — example agent doctrine skill
- `.claude/skills/stack-skill-creator/SKILL.md` — example process skill (template for T12)
- `.claude/commands/plan.md` — example thin command (template for T7/T8 commands)
- `.claude/schemas/feature-list.schema.json` — schema-as-contract pattern (template for T7's PRD schema if any)

## Things NOT to do

- Don't reintroduce `deferred` resolution_kind — it's structurally banned. ARCHITECTURE.md invariant § Zero debt enforces.
- Don't reintroduce `risks` / `tech_debt` / `cross_r_risks` fields — schema's `additionalProperties: false` rejects them; planner must resolve to ADR / open_question / feature.
- Don't add WARN severity to lint scripts — PASS/FAIL only.
- Don't move `ARCHITECTURE.md` content into `CLAUDE.md` — different concerns; subagents don't auto-inherit `CLAUDE.md` anyway. Per-agent `Inputs` lists are the right mechanism.
- Don't add a `docs/agents/` layer (Pocock has it; we don't need it because doctrine lives in `docs/agent-prompt-doctrine.md` + per-agent prompts).
- Don't introduce a new top-level master file without a sink target.
- Don't lint-enforce deep-module heuristics — design-time doctrine only.
- Don't pre-create empty `CONTEXT.md` / `docs/adr/index.md` / `app_docs/codemap.md` stubs at setup — they are lazy.
- Don't merge `prd.md` and `research.md` — different rot lifecycles (intent stable, codebase snapshot may stale). Two files per batch.
- Don't shard prd/research per-R into subdirs — single batch-level file each, H2 sections per R. The 1M context makes sharding's token argument moot; planner needs cross-R coherence anyway.
- Don't write any worker prompt without embedding the doctrine three sections (Mandatory before starting + Common Rationalizations + reference to `docs/agent-prompt-doctrine.md`). Agent rationalization tables are catalogued there for reuse.
