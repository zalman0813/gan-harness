# Improve handoff — thin-agent + focused-skill refactor

> Status: **LANDED in gan-harness + propagated to Apollo.**
> - gan-harness: all six follow-ups landed, committed `e52411c`
>   (`refactor(agents): land thin agents + fold handbooks into CLAUDE.md rules`).
> - Apollo-Agent-Harness: thin agents + CLAUDE.md block + handbook deletion +
>   two stack skills rebuilt + pattern-skill-creator + reference reconciliation,
>   on branch `thin-agent-skill-refactor`.
> The original design rationale is kept below; the live state is in §3, the
> Apollo propagation in §7. Remaining work is optional (§4 / §7 tails).

---

## 1. Why this work exists (the problem)

The harness agents were **bloated and drifting**. Symptoms the user reported:

- During /loop's **negotiate** phase, agents go off-script and **reinvent the wheel**
  instead of using existing skills / subagents.
- Subagents don't use the intended designs (e.g. AWS Strands subagents in the Apollo
  sibling repo) — they hand-roll instead.
- The user had to **repeat "use the skill" in the system prompt** and it still didn't stick.

Root cause (diagnosed, grounded in Anthropic's own guidance):

1. **Physical bloat.** gan-harness agents were 337 / 454 / 495 lines (generator /
   planner / evaluator); Apollo's were up to 588. The reference template
   (GodotPrompter `godot-csharp-engineer.md`) is **73 lines**. High-signal instructions
   were buried → Anthropic "attention budget / context rot": recall decays as tokens grow.
2. **Missing reuse input.** The negotiate phase never received "what already exists",
   so reuse-vs-build was an *undefined* decision → the model defaults to **build**
   (completion bias).
3. **Anti-drift rules behind a load step.** Putting "don't drift" rules in a skill the
   agent must *remember to load* is self-defeating — loading is itself the skipped step.

Reference + sources studied: GodotPrompter (jame581/GodotPrompter) `agents/` + `skills/`;
Anthropic engineering posts (context engineering, long-running harnesses, Agent Skills,
writing tools for agents, multi-agent research); Claude Skills authoring best practices;
Agent SDK subagents; MCP. Full analysis: `_analysis/agent-refactor-report.html`.

---

## 2. The design that converged (SSoT)

Authoritative design doc: **`_analysis/agent-template-spec.md`**. The core is three
**placement rules** — they decide where any piece of content lives:

1. **A skill exists only if conditional OR shared.** (conditional = not every round →
   real JIT; shared = ≥2 agents → real DRY.) Neither → not a skill.
2. **Every-round behavioral guardrails → CLAUDE.md** (auto-injected into every subagent,
   unskippable — the only correct home for anti-drift rules).
3. **Every-round single-agent procedure → inline in that agent** (dense bullets; a second
   file is pure overhead + a rot surface).

Consequences:
- **Thin agent** = identity + (stack discovery if it runs the gate) + Your Skills
  (conditional/shared only) + Two Modes (each self-contained: Read → Produce → Rules →
  Return) + Principles (agent-specific behavior, no foreign-package names, no thresholds)
  + Boundaries. **No `## Load First`.**
- **Output contract** = one line `<status> <key=value…>`; status token (`done`/`blocked`/
  `escalate`) for the parent to branch on; keys name the **artifact**, never the mode
  (the parent already knows the mode it spawned).
- **Domain knowledge** (thresholds, schemas, gate stages, module design) lives in skills
  *only when conditional/shared*; otherwise inline. Skill descriptions are
  `Use when <trigger> — <scope>`.
- **Skill relationships are wired in the agent's `## Your Skills`**, never cross-linked
  inside skills (no `## Related skills`). Keeps skills self-contained + portable; one less
  rot surface.

### Skill taxonomy (three creators, clean set)
| creator | produces | shape |
|---|---|---|
| `stack-skill-creator` | one stack's **version anchor + gate `## Commands`** | lightweight single file |
| `pattern-skill-creator` | one **POC'd concrete pattern** | GodotPrompter: `Use when … — … NOT …` + approach table + verbatim code + gotchas |
| `approach-handbook-creator` | cross-cutting **methodology** | conceptual handbook |

### Handbook verdict
- **Deleted (fold into agent):** `generator-handbook`, `planner-handbook`,
  `evaluator-handbook` — single-agent + every-round, fail Rule 1.
- **Deleted (→ CLAUDE.md):** `harness-conventions` (was never built).
- **Kept as skills:** `deep-module-handbook` (shared gen+eval + conditional),
  `adr-lifecycle` (conditional), stack skills, pattern skills, the three `*-creator`s.

---

## 3. What's in this repo now (state)

### Landed (live, in this commit)
- `.claude/skills/stack-skill-creator/SKILL.md` — rewritten 304 → 126 lines.
  Now **version-anchored + lightweight**: drops web-doc vendoring; emits a stack skill
  with `## Version` + `## Version highlights` (the deltas the model writes wrong by
  default — React 19 ref-as-prop, Next 15 async cookies, PEP 695 generics) + `## Commands`
  + `## Conventions`. No `## Related skills`. New core step: **version research**
  (WebFetch the upgrade guide). Removed `references/pbt-patterns.md` (PBT is a test-case
  concern, not stack-creator content).

### Drafts in `_analysis/` (reviewed, NOT yet landed into `.claude/`)
- `agent-template-spec.md` — **the SSoT** (three placement rules + everything above).
- `generator.thin.md` — 337 → 77. Modes self-contained; reuse-before-build gate anchored
  on `_research/S{NN}/*.md`; VP ≥ 20; obey next_action verbatim; no Strands wording.
- `planner.thin.md` — 454 → 71. Two modes; spec.md 9-section shape (rest via spec_lint
  "fix until PASS"); archetype→4-criteria templates inline.
- `evaluator.thin.md` — 495 → 83. REVIEW 8-checks; VERIFY dual-axis + matrix sensor +
  module verify + missing-ADR + next_action determination; output JSON/YAML schemas.
- `claude-md-harness-rules.md` — the "Harness operating rules" block for CLAUDE.md
  (behavioral foundation + skill-loading rule + write-boundaries + output contract +
  anti-cheat table) — replaces the harness-conventions skill.
- `pattern-skill-creator.SKILL.md` — new creator draft (GodotPrompter shape).
- `stack-skill-creator.redesign.md` — the rationale doc behind the landed change.
- `agent-refactor-report.html` — the original analysis report (open in a browser).

---

## 4. Follow-up work (ordered)

> **All six landed in gan-harness (commit `e52411c`).** Items 1-6 below are done:
> pattern-skill-creator shipped; thin agents replaced live; handbooks deleted +
> refs cleaned; CLAUDE.md "Harness operating rules" block added to the setup
> template (`claude-md-skills-block.template.md`) + §4d injector + this repo's own
> CLAUDE.md; harness-loop / init / finalize / adr-lifecycle / deep-module slices
> reconciled (incl. the 3 broken `agents/*.md > ##` section cross-refs). The
> README.md + `docs/maintainer/design/*` pre-existing v3.8 staleness was left
> untouched (flagged, not in scope). The original ordered list is kept below for
> provenance.

1. **Land `pattern-skill-creator`** → `.claude/skills/pattern-skill-creator/SKILL.md`
   (move the draft; low risk, new non-destructive file).
2. **Land the three thin agents** → replace `.claude/agents/{generator,planner,evaluator}.md`.
   This is the big one — it changes live agent behavior. Before landing, verify each thin
   agent still names every flow-critical token the harness-loop skill + hooks expect
   (paths like `_pending/S{NN}-draft-v{R}.yaml`, `_evals/S{NN}-R{IR}.json`; thresholds
   like VP ≥ 20; the `next_action` vocabularies for negotiate vs verify).
3. **Delete the folded handbooks** — `generator-handbook`, `planner-handbook`,
   `evaluator-handbook` — and remove them from agent `skills:` frontmatter + any
   `harness-loop` references. Grep first: `grep -rn "generator-handbook\|planner-handbook\|evaluator-handbook" .claude/`.
4. **Wire the CLAUDE.md "Harness operating rules" block into the *target's* CLAUDE.md.**
   ⚠ Maintainer/target boundary: gan-harness's own CLAUDE.md is **not** copied to targets;
   the target gets its own via the setup injector. Find where the target CLAUDE.md is
   assembled (setup-gan-harness-skills + `templates/` — currently empty) and inject the
   block there. Without this, target agents run without the guardrails.
5. **Reconcile downstream consumers** of the changed surface:
   - `harness-loop` SKILL.md spawn prompts mention "auto-load deep-module-handbook via
     frontmatter" — align with the skill-loading rule (registered, load on trigger).
   - The hook `log_subagent_stop.py` / `block_pretool.py` audit stack discovery — confirm
     the inlined stack-discovery wording still satisfies the audit.
6. **Pattern-skill consistency** — decide whether existing pattern skills (Apollo's
   `agentcore-browser-live-view`) keep their `> Related skills:` line or move it to the
   agent. The SSoT says move it; not yet enforced.

---

## 5. Decisions log (so they're not re-litigated)

- **Principles are agent-specific behavior, not universal-across-harnesses.** The earlier
  over-correction (generic principles) was wrong. Remove only *foreign-package* leaks
  (e.g. "Strands"); keep gan-harness-specific behavior.
- **Output lines don't echo the mode.** Parent knows the mode; the line carries
  status + artifact.
- **Stack `## Commands` stays** (every stack has a test framework; it's the gate contract,
  shared by hook + generator + evaluator). Only the doc-vendoring was wrong.
- **Version is the stack skill's core job** — the model defaults to stale versions; pin +
  highlight the deltas. This is why `stack-skill-creator` gained a version-research step.
- **Single-agent every-round handbooks were the mistake** — they double the rot surface
  for zero JIT gain. Fold them in.

---

## 6. How to verify a thin agent didn't lose flow-critical behavior

For each landed thin agent, check it still carries (grep the agent + diff vs old):
- the exact output **paths** and **round vocab** (`v{R}` negotiate vs `R{IR}` implement);
- the **thresholds** the loop/hooks enforce (VP ≥ 20; matrix `must_pass: all`);
- the **next_action** values per phase (negotiate: proceed_to_implement/refine_contract/
  restart_contract; verify: proceed/refine/restart_sprint/escalate_to_user);
- the **locked reading order** (anti-worldview-leak for evaluator);
- the **write-deny** surfaces (now in CLAUDE.md, but block_pretool still enforces).

"Done" = the harness-loop skill can drive the thin agent end-to-end with no missing token.

---

## 7. Apollo-Agent-Harness propagation (done; branch `thin-agent-skill-refactor`)

Apollo is a live product repo that received the gan-harness substrate earlier, then
diverged with richer mechanism. The same design was applied there — but Apollo's
agents are NOT a copy of gan-harness's; they were distilled from Apollo's own bloated
agents so the divergent machinery survives.

**Thin agents** (`.claude/agents/`): planner 454→77, generator 529→154, evaluator
588→122. Apollo-specific mechanism preserved verbatim: the **two-gate contract**
(`inner_gate[]` generator-run + `outer_gate[]` evaluator-run, phase-ordered
env→integration→e2e→matrix with `depends_on`/`on_fail`), the **inner-gate artifact**
(`_pending/S{NN}-inner-gate-R{IR}.json`, trusted at VERIFY Phase 0, no unit re-run),
the **handoff note**, the **AWS env precondition gate** (env-blocker → escalate on
first occurrence), `criterion_mapping` over outer_gate ids, the **mcpServers**
frontmatter blocks (Strands / copilotkit / next-devtools / aws-iac), and the existing
prose output-line formats (Apollo's harness-loop reads files, not the line). Added the
**reuse-before-build** gate (the motivating fix: call existing Strands/AgentCore
subagents by their MCP tool, don't hand-roll). Removed the **"already preloaded"**
false premise and the **"stack_audit = audit FAIL"** fiction (Apollo's
`log_subagent_stop.py` is pure logging — `progress.tsv` has no stack_audit column).

**CLAUDE.md**: added the `## Harness operating rules` block (behavioral foundation +
skill-loading + write-boundaries + output contract + anti-cheat, incl. a "reuse first,
don't hand-roll Strands" row), sitting above Apollo's existing Domain docs / AWS env /
doc-authoring sections.

**Handbooks**: deleted `generator/planner/evaluator-handbook`; cleaned refs in the kept
skills (deep-module slices, aws-ephemeral-testinfra, harness-loop, init/finalize-workflow,
adr-lifecycle) incl. the 3 broken `agents/*.md > ##` cross-refs.

**Stack skills rebuilt** (lightweight, version-anchored, **matched to the codebase** —
verified live by a subagent, not the skill's prior prose):
- `nextjs-copilotkit-agui` 416→70 — Next 16.2.6 / React 19.2 / CopilotKit 1.57 (v1
  root import) / Tailwind v4; **AG-UI consumed as raw SSE, NOT `@ag-ui/client`** (the
  codebase has no `@ag-ui/*`); version-delta highlights + the field-observed `useCoAgent`
  setState HAZARD preserved; Commands verbatim. Its three `references/*.md` were
  reconciled to stop prescribing `@ag-ui/client`.
- `python-agentcore-strands` 252→63 — Python 3.11 / strands-agents 1.41 /
  bedrock-agentcore 1.1.5 / **FastAPI 0.115 hand-rolled** (not `BedrockAgentCoreApp`,
  matching the codebase) / uv; Strands→AG-UI dict-by-toolCallId gotcha + Memory-vs-DynamoDB
  boundary preserved; Commands verbatim.

**Also**: added `pattern-skill-creator`; fixed the `log_subagent_stop.py` render label
("Skills preloaded" → "Skills registered (frontmatter — load on trigger)").

**Apollo remaining (optional)**: wire `pattern-skill-creator`/skills into agent
`## Your Skills` indexes as needed; the `agentcore-browser-live-view` pattern skill's
`> Related skills:` line (move to agent per SSoT); the `_c`-suffix CopilotKit hook names
in references left as-is (unverified upstream; look-up-at-decision-time anyway).
