---
name: pattern-skill-creator
description: Use when capturing a POC'd implementation pattern as a focused skill — turn a working approach (and the wrong approaches it beats) into one concern-scoped pattern skill in the GodotPrompter shape: a "Use when … — … NOT …" trigger, an approach-comparison table, the verbatim working code, and the gotchas. Trigger on "capture this pattern", "make a skill from this POC", "turn this working approach into a skill".
---

# Pattern Skill Creator

Turn a POC into a **focused pattern skill** at `.claude/skills/<pattern-name>/`. One skill = one concern.

The highest-value content is the **non-obvious decision**: what to do AND what NOT to do — the wrong/obvious approaches you already burned time on. That NOT-clause is what stops an agent reinventing the wheel or defaulting to the pattern that doesn't work. Model: Apollo's `agentcore-browser-live-view` (raw `dcvjs-umd` — NOT the SDK wrapper which is viewer-only).

A pattern skill is **not**: a stack skill (version + gate commands → `stack-skill-creator`), a methodology handbook (cross-cutting approach → `approach-handbook-creator`), or a docs mirror.

## What a pattern skill records — and nothing else

1. **Use-when trigger with the NOT clause** — the exact task it fires on + the wrong/obvious approach it replaces.
2. **Approach comparison** — the options tried, why each loses, which wins.
3. **The pattern** — the **verbatim** working code from the POC (never paraphrased).
4. **Gotchas** — what cost time; the failure modes.

NOT here: `## Related skills` (relationships are wired in the agent's `## Your Skills`), a version pin (that's the stack skill's job), or tutorial padding.

## Mandatory before starting

Never invent the pattern — it must come from a real POC / working reference the user points at.

```
ASSUMPTIONS I'M MAKING:
1. <pattern name + the one concern it owns>
2. <source: the working file(s) / POC the verbatim code comes from>
3. <the wrong approach(es) it beats — the NOT clause>
→ Correct me now or I proceed.
```

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "I'll write a reasonable pattern from memory" | No. The value is verbatim-verified code + the NOT clause. No POC = no skill — point me at the working reference. |
| "I'll list every related skill so the agent finds them" | No. Relationships are wired in the agent's `## Your Skills`. The skill stays self-contained and portable. |
| "More approaches listed = more thorough" | No. One winner + the few real losers. A pattern skill is a decision, not a survey. |
| "This pattern does two related things" | Two concerns = two skills. Split it. |

## Process

### Step 1 — Capture intent (AskUserQuestion)
- **name** — kebab-case, scoped to ONE concern (`agentcore-browser-live-view`, not `browser`).
- **source** — the working file(s) / POC the verbatim code comes from.
- **the NOT** — the wrong/obvious approach(es) this beats (the most valuable input).

### Step 2 — Extract the decision
Read the real source files (do not paraphrase). Pull: the winning approach, the losers + why each loses, the verbatim code, the gotchas. If a small reference table earns it (IAM actions, env matrix), put it in `references/<topic>.md` — one level deep, linked from SKILL.md.

### Step 3 — Write SKILL.md
Use the template below.

### Step 4 — Self-validate (inline)
- frontmatter `name` (one concern) + `description` in `Use when … — … NOT …` form.
- approach-comparison table present, with ≥1 loser and its reason.
- the code block is **verbatim from a cited source**, not synthesized.
- no `## Related skills`; no version pin.

### Step 5 — Hand off
> Pattern skill is at `.claude/skills/<name>/SKILL.md`. Wire which agents use it (and alongside what) in those agents' `## Your Skills` index — don't cross-link skills. One concern per skill; a second concern is a second skill. Re-run the POC and update the code block if the upstream API changes.

## The pattern skill template

```markdown
---
name: <pattern-name>
description: Use when <specific task> — <the technique + the gotcha it solves; name the libs/APIs a sprint would mention>. NOT <the wrong/obvious approach it replaces>.
---

# <Pattern Name>

<One sentence: what you get + the non-obvious win.>

## Approach comparison

| Approach | <trade-off axis> | When to pick |
|---|---|---|
| <obvious / SDK-default one> | <why it loses> | Never |
| **<your POC approach>** | <why it wins> | <when> |

## The pattern

```<lang>
<verbatim working code from the cited source — the part that's hard to get right>
```

## Gotchas

- <the thing that cost hours / the failure mode / the silent footgun>
```

## Anti-patterns

- **Synthesizing the pattern from memory** — no POC, no skill. The code must be verbatim from a working reference.
- **Omitting the NOT clause / the loser approaches** — that's the drift-prevention payload; without it the agent re-walks the dead end you already cleared.
- **`## Related skills` inside the skill** — wire relationships in the agent's `## Your Skills` index instead, where they're centralized and visible.
- **Two concerns in one skill** — split into two; the `Use when` trigger should name one task.
- **Pinning a version or carrying gate `## Commands`** — that's the stack skill's job; a pattern skill assumes the stack skill exists.
- **Paraphrasing the code** — paraphrase loses the exact idiom the agent needs to copy; keep it verbatim.
