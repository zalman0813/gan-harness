---
name: stack-skill-creator
description: Create a new stack skill for gan-harness — a capsule that vendors language/framework conventions (Python, FastAPI, Next.js, AWS CDK, Flutter, etc.) so harness agents can read code in that stack. Use when the user says "add a stack", "support <language>", "init project for <framework>", or asks how to make gan-harness work with a stack that doesn't yet have a skill. Make sure to use this skill whenever the user mentions adding language or framework support, even if they don't say "skill" explicitly.
---

# Stack Skill Creator

A process skill that produces a new stack skill at `.claude/skills/<stack-name>/`. The output is a minimal capsule: just enough metadata for the harness to load it, plus a `references/` library of stack-specific docs that downstream agents (planner / generator / evaluator / finalize) can selectively consult.

This skill **does not pre-bake role-specific reference files**. Stack skills are vendored libraries of stack idioms; how each harness agent consumes them is defined by the agent itself in later stages, not by the creator.

## Mandatory before starting

Before creating any directory or fetching any doc, surface your assumptions about scope:

ASSUMPTIONS I'M MAKING:
1. <e.g., "stack name is python-fastapi (not python-django)">
2. <e.g., "vendoring source is user-provided files at /path/X">
3. <e.g., "scope is Starter (3-5 seed topics), not Comprehensive">
→ Correct me now or I'll proceed with these.

Do not silently pick a stack variant on the user's behalf. If they say "Python", ask which web framework / which test runner / which version. See `docs/agent-prompt-doctrine.md` § Universal rules.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "User didn't specify exact stack variant, I'll pick a common one" | Don't pick. Grill until stack boundary, version, test runner are explicit. Wrong defaults disguised as right ones is the worst output. |
| "Barrel pattern is standard, I'll copy mainstream" | Each stack has its own idiom (Python `__init__.py`, Rust `mod.rs`, Dart `library;`). Verify the target stack's actual convention before writing. |
| "I'm not familiar with this stack, I'll write a reasonable skeleton" | Unfamiliar = stop. Writing a "reasonable skeleton" hands the user wrong defaults. Either source from user docs / official docs, or refuse. |

## When the user invokes this skill

Capture intent up front via `AskUserQuestion`:

1. **Stack name** — kebab-case identifier. Examples: `python-fastapi`, `nextjs-supabase`, `cdk-typescript`, `flutter-serverpod`.
2. **Source of material** — one of:
   - User-provided files (paths to local docs, README excerpts, internal style guides)
   - Web search of official docs (creator does WebSearch + WebFetch on framework's canonical doc site)
   - Mixed (user docs + web fill-in)
3. **Scope**:
   - Starter — identification + 3-5 seed reference topics (quick start, ~30 min)
   - Comprehensive — deep vendor pass on official docs (~hours; covers routing, auth, persistence, testing, deployment, error handling)

Confirm before proceeding.

## Process

### Step 1 — Capture intent

Run the three questions above. Wait for user's full answer set.

### Step 2 — Vendor the source material

Create the skill directory: `.claude/skills/<stack-name>/references/`.

**If user-provided**: read each file, split by topic (one topic = one `references/<topic>.md`). If a single file covers multiple topics, split it. Preserve original prose; do not paraphrase.

**If web search**: WebSearch for `<stack> official documentation`, then WebFetch the top-result canonical doc pages. Strip nav, ads, version-switcher noise. Save each page or section as `references/<topic>.md`. **Always** record provenance in `references/upstream.md` (table: file | source URL | revision/SHA | license | fetched_at).

**Vendoring rules**:
- One topic per file. Don't merge "routing + middleware + auth" into one big file.
- Cap each reference file at ~500 lines. If larger, split by table-of-contents into sub-topics.
- Strip framework-version-specific notes if user pinned a version; otherwise keep version markers.
- Include code examples verbatim — those are the most useful part for downstream agents.

### Step 3 — Write SKILL.md for the new stack skill

Use this template (substitute `<stack-name>` and the references list):

```markdown
---
name: <stack-name>
description: <Stack Name> stack reference library for gan-harness. Vendors official docs and conventions for <key topics: routing, modules, testing, etc.>. Make sure to use this skill whenever harness agents work on <Stack Name> code or need <Stack Name>-specific idioms.
---

# <Stack Name> Stack Skill

Reference library of <Stack Name> conventions, vendored from <source>. Downstream harness agents (planner, generator, evaluator, /finalize) consult specific references as needed; this SKILL.md is the index.

## When to use

- Generator writes or edits code in <Stack Name>
- Planner needs <Stack Name>-specific test-runner / module / barrel conventions
- /finalize regenerates docs from <Stack Name> code

## References

- [routing.md](references/routing.md) — <one-line summary>
- [testing.md](references/testing.md) — <one-line summary>
- (etc., generated from references/ directory)

## Provenance

See [references/upstream.md](references/upstream.md) for source URL, revision, license, and fetched-at per vendored file.

## Stack-specific anti-patterns (optional)

If you've encountered specific gotchas in <Stack Name>, log them here so downstream agents avoid them.
```

### Step 4 — Self-validate

Run minimal checks (inline, not a separate script):

- `SKILL.md` frontmatter has `name` + `description`
- `references/` exists with ≥1 file
- `references/upstream.md` exists if any web-vendored content (otherwise N/A)
- No file in `references/` exceeds 500 lines (warn if so, suggest splitting)

Print summary: skill path, references file count, total LOC, vendored URLs.

### Step 5 — Hand off

Tell the user:

> The stack skill is at `.claude/skills/<stack-name>/`. Downstream harness agents will pull from `references/` as they mature. You can edit `references/` at any time to add idioms you want enforced. To re-vendor an upstream file, fetch the new revision and update `references/upstream.md`.

## Anti-patterns

- **Pre-baking role-specific content** — do NOT create files like `references/sink-module-doc.md` or `references/test-contract.md` predicting what planner or generator will want. Those agents define their own consumption contract; the creator's job is to vendor raw idioms, not to predict roles.
- **One mega-reference file** — splitting a 3000-line dump into a single file makes Claude skim and miss specifics. One topic per file.
- **Skipping provenance** — without `references/upstream.md`, vendored content becomes mystery code. Always log source.
- **Editing vendored files in place** — re-vendor with new revision and update the log instead.
- **Paraphrasing official docs** — vendoring means copying the canonical text, not summarizing. Summaries lose the literal idioms downstream agents grep for.

## Examples

### Example 1 — Add Python/FastAPI from web search

```
User: "I want to add Python FastAPI as a stack."
Creator: AskUserQuestion:
  - Q1: name → python-fastapi (or other?)
  - Q2: source → web search of official docs?
  - Q3: scope → starter or comprehensive?
User: python-fastapi / web / comprehensive
Creator:
  WebSearch "FastAPI official documentation"
  WebFetch fastapi.tiangolo.com/tutorial/{first-steps,path-params,query-params,
                                          dependencies,security,testing,deployment}
  Saves each as references/<section>.md
  Records provenance in references/upstream.md
  Writes SKILL.md indexing all references
  Validates
  Reports: 8 references, 2400 LOC vendored from fastapi.tiangolo.com @ commit abc123
```

### Example 2 — Add internal stack from user docs

```
User: "Add our internal stack. I have docs locally."
Creator: AskUserQuestion:
  - Q1: name → acme-internal
  - Q2: source → user-provided
  - Q3: paths → /docs/style.md, /docs/arch.md
  - Q4: scope → comprehensive
Creator:
  Reads both files
  Splits style.md by section (naming, formatting, error-handling)
  Splits arch.md by section (modules, layering, testing)
  Saves as references/{naming,formatting,error-handling,modules,layering,testing}.md
  Writes SKILL.md
  No upstream.md (all user-provided, no web fetches)
  Validates
  Reports: 6 references, 850 LOC
```

## What's intentionally NOT in this skill

- **A required reference file list** (sink-module-doc / deep-module / etc.) — those are downstream agent contracts, defined when planner/generator/evaluator/finalize mature
- **A stack-skill linter** — provenance + non-empty + size checks are the only gates here; deeper structural validation happens when an agent actually consumes the skill
- **Versioning policy** — bump the new stack skill's `version` field if you add one; this creator doesn't enforce a scheme
