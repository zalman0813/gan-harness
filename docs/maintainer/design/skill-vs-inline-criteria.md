# Skill vs Inline — When to write a new skill (and when not to)

> Maintainer-facing design memo. **Not loaded at runtime by any agent, skill, or hook.** This file captures the criteria future maintainers should apply when deciding whether a new piece of doctrine becomes a new `.claude/skills/<name>/` directory or gets inlined into an agent prompt. It is not referenced from any worker file by design — the actual prompts are self-contained.

## The criteria

A piece of doctrine becomes a `.claude/skills/<name>/` skill if-and-only-if it satisfies **at least one** of:

1. **Shared** — consumed by **two or more** agents (e.g. `deep-module-handbook` is loaded by planner + generator + evaluator; `escalation` is loaded by generator + evaluator).
2. **Progressive** — only relevant when a **specific decision point** arises during a run. The agent should NOT need to read it as part of every spawn (e.g. `playwright-cli` only when the active stack uses Playwright; `escalation` only when env blocks).
3. **Stack-related** — the content is language-/framework-specific and should swap when the active stack swaps (e.g. `rust-tauri-v2`, `python-fastapi`, `nextjs-supabase`).
4. **Approach-related** — the content captures a methodology that downstream agents bind into via frontmatter (e.g. `deep-module-handbook` for the Ousterhout depth methodology; `windows-mcp` as an e2e approach handbook for Windows desktop apps).

If **none** of those four hold, the content is **not a skill**. It belongs:

- Inline in the agent prompt (`.claude/agents/<agent>.md`), if the agent always needs it.
- In a workflow skill (`.claude/skills/<workflow>-workflow/`), if it's orchestration logic.
- In a hook (`.claude/hooks/`), if it's a runtime enforcement.
- Deleted, if it's training-data-dressed-as-doctrine (worked examples that don't change agent behaviour).

## The litmus question

Before creating a new skill, answer this in one breath:

> "Is this content (a) consumed by two-plus agents, OR (b) only consulted at a specific decision point, OR (c) stack-bound, OR (d) approach-bound?"

If you cannot answer "yes" to one of those, do not create the skill. Inlining is the correct move.

## Why this filter matters

Skills have hidden costs:

- Every skill adds to the available-skills list the agent sees at startup, competing for attention.
- Reference paths embedded in skills can rot; dead refs are easy to miss across multiple files.
- A "handbook" with one consumer creates the illusion of reusability that never materialises.
- Splitting always-required content into a skill *forces* the agent to do an extra read-step, when the prompt could have just contained the content.

When in doubt, **inline first**. Refactor to a skill *after* a second consumer or a decision-point boundary genuinely emerges. Premature skill extraction is a real cost and a hard one to roll back (every consumer adds a frontmatter `skills:` reference that has to be removed in lockstep).

## Worked examples (correct applications)

### `deep-module-handbook` — shared + approach

Loaded by planner / generator / evaluator. All three need information-hiding doctrine and the red-flag taxonomy. Single source of truth, one update propagates to all three. Satisfies criterion 1 + 4.

### `escalation` — shared + progressive

Loaded by generator + evaluator. Both need the same `specs/_batch/_escalations/F{NN}-{gen|eval}-R{N}.json` schema, but neither agent escalates on every run — only when env blocks. Satisfies criterion 1 + 2.

`block_pretool.py` blocks generator from reading evaluator's prompt and vice versa, so inlining the same schema in both prompts would mean two copies that drift over time. The shared skill resolves the constraint cleanly.

### `playwright-cli` — approach

A specific e2e tool's commands and idioms. Only loaded when the project's active e2e approach is Playwright. Swappable with `windows-mcp` / `flutter-driver` / etc. Satisfies criterion 4.

### `rust-tauri-v2` — stack

Vendored Tauri v2 conventions. Loaded only when the active stack is Rust + Tauri v2. Different stack → different skill. Satisfies criterion 3.

## Worked examples (incorrect applications, retroactive corrections)

### Past mistake: `evaluator-handbook` (now dissolved)

Originally housed evaluator's behavioural principles, adversarial probe taxonomy, calibration examples, L5 workflow, escalation schema, and verdict discipline. Failed every criterion:

- **Shared?** No — only evaluator loaded it.
- **Progressive?** No — every evaluator spawn read it at startup.
- **Stack-related?** No.
- **Approach-related?** No.

The handbook was loaded as part of every evaluation. That's not progressive; that's "I forgot to put this in the prompt and made a skill out of habit". The correct distribution was:

- Behavioural principles → inline `evaluator.md` (always-required).
- Probe cheat row → inline `evaluator.md` (always-required).
- Drift-detection self-checks → inline `evaluator.md` (always-required pre-submit).
- L5 methodology → inline `evaluator.md` § L5 (always-required when L5 path exists; ~15 lines).
- Escalation schema → new shared skill `escalation` (criterion 1 + 2, since generator also needs it).
- Calibration worked examples → deleted (training data, not doctrine).
- Verdict definitions → already inline `evaluator.md` (the handbook copy was a duplicate).
- Round-3 endpoint table → no action (already encoded in `harness-loop` SKILL's branch logic).

Outcome: 767 lines of handbook → 0. evaluator.md grew by ~30 lines net. New `escalation` skill is ~50 lines. Net reduction ~700 lines, no behavioural loss.

### Past mistake: `playwright test` literal in `evaluator.md` Principle #5

The principle was correctly inline (always-required: every verdict needs tool-call evidence). But the literal Bash invocation was hard-coded to Playwright — that's stack/approach-bound content that leaked into a framework-agnostic principle. Resolution: the principle stays inline, the literal is replaced with "the L5 invocation prescribed by the active e2e approach handbook". The invocation lives in the approach handbook (`playwright-cli`, `windows-mcp`), satisfying criterion 4.

## Anti-patterns when designing new skills

- **"Loading order" tables in a skill's `SKILL.md`.** If your `SKILL.md` is mostly a pointer to which sub-reference to load when, the agent's prompt should contain those pointers directly. The SKILL.md mid-layer adds a read-step without informing the decision.
- **Single-consumer "handbook" skills.** If only one agent loads it, ask: is it progressive? If no, inline. A shared name doesn't make a single-consumer skill shared.
- **Worked examples / calibration cases as doctrine.** Few-shot examples are training data. They influence the agent's first-shot behaviour but don't carry decision-time rules. They should be in test fixtures or design memos, not in skills the agent reads every spawn.
- **Wrapping a CLI's man page as a skill.** Stack-skill-creator's job is to vendor stack idioms; it doesn't need a skill that explains `pytest --help`. Stack idioms = how this stack draws boundaries / what the test runner expects in its assertions, not the runner's flag list.
- **"Future-proofing" skills.** "I'm splitting this into a skill in case we add another consumer" is a YAGNI violation. Add the second consumer first, then refactor.

## When to revisit the filter

Skills can be promoted from inline → skill (and demoted skill → inline) over time. Triggers:

- **Inline → skill**: a second agent legitimately needs the same content (criterion 1 emerges); or a decision-point boundary becomes real and the content's only relevance is at that point (criterion 2 emerges).
- **Skill → inline**: a skill's only consumer is one agent and every spawn loads it anyway. The skill's existence is buying nothing; collapse.

Both directions are cheap when the content is genuinely small. The cost is in the cross-reference cleanup (frontmatter `skills:` lists, prose references in adjacent prompts).

## Sources of friction worth flagging in PRs

- Adding a new file under `.claude/skills/<X>/references/` without saying which decision point reads it.
- Frontmatter `skills:` extension to a new agent without specifying which paragraph in that agent's prompt triggers the load.
- Skill's `SKILL.md` description that doesn't pass the litmus question above.
- Skill mentioned by name in the project's CLAUDE.md / CONTEXT.md (those files are infrastructure, not skill registries).
