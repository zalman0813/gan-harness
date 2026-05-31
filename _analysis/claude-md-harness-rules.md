# CLAUDE.md block — "Harness operating rules" (replaces the harness-conventions skill)

> This block goes into the **CLAUDE.md the harness agents run against** (the target
> project's CLAUDE.md — gan-harness's own CLAUDE.md is maintainer-only and not copied).
> It is auto-injected into every subagent, so the rules can't be skipped — which is why
> anti-drift content belongs HERE, not in a skill you must remember to load.
>
> Behavioral foundation is likely already present (gan-harness CLAUDE.md has it at the top);
> add the harness-mechanic subsections. Stack discovery is NOT here — it's inlined in
> generator + evaluator (only they run it).

---

## Harness operating rules (all agents)

These apply to every subagent the harness spawns (planner, generator, evaluator,
fact-finder). They live here, not in a skill, because a rule you must never skip
should not sit behind a "load it first" step — CLAUDE.md auto-injects into every subagent.

### Behavioral foundation
1. **Don't assume.** Surface assumptions and ask on ambiguity — you were trained on completion; override it.
2. **Minimum that solves it.** No speculative abstraction.
3. **Touch only what you must.** Every changed line traces to the task; clean up only your own mess.
4. **Define success as checks; loop until verified.** "Done" = you re-ran the check and it passed.

### Skill-loading rule
`skills:` frontmatter **registers** a skill; it is **NOT auto-injected**. Load a skill's
body with the Skill tool only when its `Use when` trigger matches. Never `Read` a skill's
`references/` files directly — the Skill tool is the only valid path.

### Write-boundaries (block_pretool enforces; denial is not negotiable)
- `spec.md` is immutable — only planner writes it. Surface a gap via your escalate path.
- `contracts.jsonl` is append-only by MAIN — agents read, never `Edit`.
- `docs/adr/*` — only generator authors. Planner/evaluator are write-denied.
- Never read a sibling agent's `.claude/agents/*.md`; `.git/hooks/` denied; `_traces/*` belong to the hook.

### Output contract
Return **exactly one line** to the parent; lead with a status token (`done` / `blocked` /
`escalate`), name the artifact, don't echo the mode. The parent parses that line.

### Anti-cheat stance
| Rationalization | Reality |
|---|---|
| "Unspecified → I'll pick a default" | Don't pick. Surface the assumption and ask. |
| "Standard → I'll do the mainstream thing" | Verify the project's actual convention first (CONTEXT.md, stack skill). |
| "Unsure → a reasonable skeleton is fine" | Stop and surface; don't ship confident-wrong output. |
| "Close enough → done" | Re-run the check. Done is verified, not believed. |

---

## What changed vs the skill design

- **No `harness-conventions` skill.** Deleted.
- **No `## Load First` in any agent.** The rules are always in context via CLAUDE.md.
- **Stack discovery inlines** into generator + evaluator (≈3 lines each) — it's their own
  procedure, not cross-cutting, and inlining keeps it un-skippable without a load step.
- Each agent still owns its **own one-line output formats** (the status tokens above are
  the shared shape; the exact `key=value` strings stay per-agent).

## Open wiring question (maintainer/target boundary)

gan-harness's own `CLAUDE.md` is **not** copied to target projects; the target gets its
own. So this block must be injected into the **target's** CLAUDE.md by the setup step
(the skills-block injector / template). Decide where that injection lives before shipping —
otherwise target agents run without these rules.
