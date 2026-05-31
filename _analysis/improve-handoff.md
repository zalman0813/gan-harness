# Improve handoff — thin-agent + focused-skill refactor

> Status: **design converged, partially landed.** One live change committed
> (stack-skill-creator); the rest are reviewed drafts in `_analysis/` awaiting
> landing into `.claude/`. This doc carries the background + the rationale + the
> remaining work so the next session can continue without re-deriving anything.

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
