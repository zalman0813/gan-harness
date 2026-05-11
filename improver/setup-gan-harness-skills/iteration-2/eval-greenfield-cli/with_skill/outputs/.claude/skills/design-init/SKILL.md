---
name: design-init
description: Bootstrap a Google-spec DESIGN.md from an Anthropic design share URL, local markup, brand brief, or blank skeleton; suggests which stack skill should reference it. Use when the user wants to create DESIGN.md for the first time or turn a Claude design share into design tokens. Skip when an existing DESIGN.md needs updating (goes through /finalize) or the user wants UI implemented (generator's job).
---

# design-init

One-shot bootstrap. Take a design source (Anthropic design share / local
markup / brief / blank) → produce a root `DESIGN.md` matching the Google
open-source spec → suggest which existing stack skill should reference it.

This skill is **distillation-only**. It writes exactly one file
(`DESIGN.md` at target root) and prints suggestions. It never edits any
other skill, never implements UI, never generates component code.

## Mandatory before starting

ASSUMPTIONS I'M MAKING:
1. cwd is the target project root (where `DESIGN.md` should land).
2. The target was already bootstrapped by `setup-gan-harness-skills`
   (so `.claude/skills/` exists with stack skills to scan in Phase 5).
3. `npx` is available for the lint gate. If not, I will warn and
   continue, marking the file `lint_status: skipped`.
4. The user owns the brand identity. I extract / suggest; I never
   invent design choices the user did not authorize.
→ Correct me now or I'll proceed with these.

If a `DESIGN.md` already exists at target root, ABORT immediately and
tell the user to either (a) rename / move the existing file before
re-running, (b) update tokens through their normal feature flow
(generator surfaces missing tokens as `open_question` → /finalize merge),
or (c) confirm replacement explicitly. I will not silently overwrite.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "User pasted a URL — I'll just fetch it and start writing tokens" | No. Confirm input mode first (Section A). The URL might be reference-only ("look at this for inspiration") rather than the source of truth. Ask. |
| "Linting is optional, the user is in a hurry" | Run `npx @google/design.md lint` every time. If it fails, surface the failure with three options. If npx itself is unavailable, warn and stamp `lint_status: skipped` in frontmatter — never silently skip. |
| "I'll grep the stack SKILL.md and append my own substrate line" | NO. design-init is suggest-only. Print the file path + insertion location + suggested text; the user decides whether to paste. Touching another skill's file violates the boundary. |
| "Detection found nothing, I'll guess by filename" | If heuristic match is empty, fall back to listing ALL skills with a note that I could not confidently classify any as frontend — let the user pick. Inventing a match silently misroutes the suggestion. |
| "User said 'extract tokens from this Anthropic share' so they obviously want me to also implement the page" | NO. The skill description forbids implementation. If the user wants the design realised in code, they exit this skill and run their normal feature flow (`/prd → /plan → /execution-loop`); generator implements against `DESIGN.md`. |
| "The Anthropic share URL won't fetch (auth wall) — I'll just guess from the filename in the URL" | No. Ask the user to either (a) paste the readme + key HTML content directly into chat, or (b) save the share locally and give me the path. Guessing tokens from a filename is fabrication. |
| "WCAG fails on a contrast pair the user clearly wanted — I'll silently round the colour to make it pass" | NO. Surface the failure and the offending pair. Let the user choose to fix or to override (`lint_status: failed`). Mutating the user's brand to satisfy a linter is out of scope. |

## When to use

- A target project has no `DESIGN.md` and the user wants to bootstrap one
- The user has a Claude-generated design share (Anthropic URL) and wants
  it turned into Google-spec design tokens
- The user has existing markup (HTML / CSS / Tailwind config / screenshot)
  and wants tokens extracted into a single canonical file
- The user has only a brand brief in natural language and wants a starter
  DESIGN.md scaffold

## When NOT to use

- `DESIGN.md` already exists — token additions go through the normal
  feature flow (generator surfaces missing tokens as `open_question`,
  /finalize merges into root DESIGN.md)
- Mid-batch (`specs/_batch/` non-empty) — finish or abort the batch
  first; design system bootstrap during a live batch confuses the lint
  gate that runs at /finalize
- The user wants UI implemented — that is generator's job, not init's
- The target is not bootstrapped (no `.claude/skills/`) — run
  `setup-gan-harness-skills` first

## Inputs

- **Input mode** (asked in Section A) — one of:
  - `anthropic-share` — URL like `https://api.anthropic.com/v1/design/h/<hash>?open_file=<file>.html`
  - `local-markup` — absolute path(s) to HTML / CSS / screenshot files
  - `brand-brief` — natural-language description in chat
  - `blank-skeleton` — start from Google spec scaffold, user fills later
- **Input source** (asked in Section B, varies by mode) — the URL,
  paths, brief text, or empty for skeleton
- **Brand identity** (asked in Section C when needed) — name + one-line
  tone (only required for `brand-brief` and `blank-skeleton`; extracted
  from source for the other two)

## Outputs (target side)

After successful run:

- `target/DESIGN.md` — single file, Google-spec format, with frontmatter
  recording `lint_status` (one of `passed` / `failed` / `skipped`)
- Console output — heuristic-matched stack skills with suggested
  insertion location and ready-to-paste text

NOT created / NOT modified:
- Any `.claude/skills/*/SKILL.md` — suggest-only
- Any frontend code — distillation-only
- `CONTEXT.md` / `CODEMAP.md` / `docs/adr/` — out of scope for design tokens

## Process

### Phase 1 — Explore (silent)

1. Verify cwd looks like a bootstrapped target:
   - `.claude/skills/` exists → continue
   - Otherwise → ABORT with "Run `setup-gan-harness-skills` first."
2. Check for existing `DESIGN.md` at target root:
   - Exists → ABORT per the "Mandatory before starting" rule above
3. Check `specs/_batch/` for live batch artefacts (any file other than
   `.gitkeep`):
   - Non-empty → ABORT: "Live batch detected. Finish /finalize or
     remove the batch before bootstrapping DESIGN.md — the design lint
     gate also runs at /finalize and bootstrapping mid-batch is racy."
4. Check `npx` availability (`command -v npx`). Record
   `NPX_AVAILABLE=true|false` for Phase 3 lint branching.

### Phase 2 — Ask one section at a time

Walk these in order. Each section starts with a one-sentence explainer
the user can act on without reading docs.

#### Section A — Input mode

> DESIGN.md can be bootstrapped from four kinds of input. Which fits
> what you have right now?

`AskUserQuestion` with the four options above. The user picks one.

#### Section B — Input source

Branch on Section A:

- **`anthropic-share`** → AskUserQuestion: "Paste the share URL."
  - WebFetch the URL. Two possible outcomes:
    - Success → continue to Section C with fetched content
    - Auth wall / fetch error → AskUserQuestion: "Fetch failed. Either
      (1) paste the readme + main HTML inline here, or (2) save the
      share files locally and give me a directory path." Loop until
      one path produces readable content.
- **`local-markup`** → AskUserQuestion: "Absolute path(s) to HTML / CSS
  / screenshot. Comma-separated for multiple."
  - Read each path. Reject silently-empty files.
- **`brand-brief`** → AskUserQuestion: "Describe the design language —
  brand tone, target feel, any reference brands or sites."
  - Free-text answer.
- **`blank-skeleton`** → no source needed. Skip directly to Section C.

#### Section C — Brand identity

Only for `brand-brief` and `blank-skeleton` (the other two extract from
source).

> The DESIGN.md frontmatter needs a `name` and `description`. These
> appear at the top of the file and in agent-readable export formats.

Two AskUserQuestion calls (one per field): brand `name` + one-line
`description`.

### Phase 3 — Confirm

#### 3a. Distil

Synthesise the DESIGN.md from inputs:

- **Frontmatter (YAML)** — `version: alpha`, `name`, `description`,
  `colors`, `typography`, `rounded`, `spacing`, `components`. Use token
  references (`{path.to.token}`) inside `components` rather than
  hard-coding hex values.
- **Body (markdown)** — H2 sections in canonical order: Overview /
  Colors / Typography / Layout / Elevation & Depth / Shapes /
  Components / Do's and Don'ts. Each section's prose explains the *why*
  behind the tokens, not just restating them.

For `anthropic-share` and `local-markup`, ground every extracted token
in observed source (e.g., a hex from CSS, a font-family from inline
style). For `brand-brief` and `blank-skeleton`, mark synthesised tokens
explicitly in the Overview prose ("These values are starter defaults;
edit before shipping.").

#### 3b. Lint gate

If `NPX_AVAILABLE=true`:

```
npx -y @google/design.md lint <draft-path>
```

(Write the draft to a temp path first — do not write to target root
until Phase 4.)

Branch on result:

- **`passed`** → continue to 3c
- **`failed`** → show the user the lint output, then AskUserQuestion
  with three options:
  1. **Fix** — I revise the draft to address the failure and re-lint
  2. **Manual fix** — user takes the draft, edits in their editor,
     hands back; we re-lint
  3. **Force write** — write as-is with frontmatter `lint_status: failed`
     (this is auditable; a future /finalize regen can flag it)

If `NPX_AVAILABLE=false`:

- Warn: "`npx` unavailable. Skipping lint. The DESIGN.md will be marked
  `lint_status: skipped`; run `npx @google/design.md lint DESIGN.md`
  manually when you can install Node."
- Set frontmatter `lint_status: skipped`

#### 3c. User confirmation

Show a single confirmation block:

```
Ready to write DESIGN.md to <target>:

  Source mode      : <anthropic-share | local-markup | brand-brief | blank-skeleton>
  Token counts     : colors=N, typography=N, spacing=N, components=N
  Lint status      : <passed | failed (forced) | skipped>
  File size        : ~N lines

After write, I'll scan your existing skills for likely frontend
matches and print suggestions for which SKILL.md to attach DESIGN.md
to. I will NOT modify any skill file.

Approve / Edit / Abort
```

`AskUserQuestion`. On Edit, surface a sub-question (which item to tweak)
and loop. On Abort, exit cleanly with no writes.

### Phase 4 — Write

Single file write:

```
target/DESIGN.md
```

Idempotent guard: re-check the file does not exist (Phase 1 already
checked, but defend against races). If it exists at this point, ABORT.

### Phase 5 — Done (scan + suggest)

#### 5a. Scan

List every skill at `target/.claude/skills/*/SKILL.md`. For each, read
its frontmatter `name` + `description` (no body — frontmatter is
sufficient signal).

#### 5b. Heuristic match

Mark a skill as a candidate if its `name` or `description` contains any
of (case-insensitive, word boundaries):

```
react, next, nextjs, vue, svelte, angular, solid, qwik,
flutter, swiftui, ios, android, jetpack-compose, react-native,
tailwind, css, scss, sass, postcss, html, dom, jsx, tsx,
frontend, front-end, ui, web, browser, component, design-system
```

For each candidate, record which keyword(s) matched (this is the
evidence shown to the user).

If zero candidates after scan, fall back: list ALL skills with the note
"No skill confidently classified as frontend; pick whichever owns your
visual layer (or none)."

#### 5c. Per-candidate insertion suggestion

For each candidate `target/.claude/skills/<stack>/SKILL.md`:

1. Grep the file for an existing substrate-like H2 / H3 section. Match
   pattern (case-insensitive):
   ```
   ^(##|###)\s+(Substrate|Substrate files|Substrate refs|References|Loads|Reads|Inputs)\b
   ```
2. If a matching section exists → suggest insertion at the end of that
   section. Show the heading text verbatim so the user can find it.
3. If no matching section exists → suggest inserting a new section
   after the frontmatter (and any leading H1) and before the first
   existing H2. Suggest the header `## Substrate`.

#### 5d. Print suggestion block

For each candidate, emit:

```
─────────────────────────────────────────────────────────────
Candidate: .claude/skills/<stack>/SKILL.md
Match    : <keywords that matched>
Suggested insertion: <"end of '## Substrate'" or "new '## Substrate' section after frontmatter">

Paste this block:

  - `DESIGN.md` — visual design tokens (Google-spec format).
    Generator reads when implementing UI; evaluator reads when
    grading visual ACs.

─────────────────────────────────────────────────────────────
```

After all candidates, print the closing report:

```
═══════════════════════════════════════════════════════════════
design-init complete
═══════════════════════════════════════════════════════════════

Wrote                : DESIGN.md (lint_status: <passed | failed | skipped>)
Candidate skills     : <N matched | 0 matched (full skill list shown)>
Stack skills modified: 0  (suggestions only — paste manually)

If the user wants the design realised in code, that's a normal
feature flow: /prd → /plan → /execution-loop. Generator will read
DESIGN.md (once it's referenced in a frontend stack skill).
═══════════════════════════════════════════════════════════════
```

## Anti-patterns

- **Modifying any `.claude/skills/*/SKILL.md`.** Phase 5 is suggest-only.
  The user owns whether DESIGN.md is referenced from a stack skill.
  Editing another skill's file silently violates the boundary.
- **Writing component code, JSX/TSX, CSS classes, or any UI markup.**
  This skill is distillation. Implementation belongs to generator under
  the normal feature flow.
- **Silently skipping lint.** If `npx` works, lint runs. If lint fails,
  the user sees the failure and chooses. If `npx` is unavailable,
  frontmatter records `lint_status: skipped` so audit is preserved.
- **Auto-fixing WCAG violations by mutating the user's brand colours.**
  Surface the violation; let the user decide. Brand identity is not
  agent-owned.
- **Inventing tokens for `anthropic-share` / `local-markup` modes.**
  Every token must trace to observed source. If a token cannot be
  grounded, omit it and note in the Overview prose.
- **Guessing from a URL filename when the URL won't fetch.** Ask the
  user to paste content or supply a local path. Filename inference is
  fabrication.
- **Bulk-asking input mode + source + identity in one prompt.** One
  AskUserQuestion per section, with explainer first. The walk IS the
  contract.
- **Writing a stub `DESIGN.md` "to be filled later".** If the user
  picks `blank-skeleton`, the file is the Google-spec scaffold with
  starter defaults — explicitly marked in Overview as starter, not as
  decided values.
- **Pre-creating files outside `DESIGN.md`.** This skill writes one
  file. No README, no glossary, no doc/adr entries.
- **Re-running mid-batch.** Phase 1 aborts if `specs/_batch/` is live.
  The /finalize lint gate races with bootstrap if both touch DESIGN.md.

## Done when

- [ ] Phase 1 preflight clean (no existing DESIGN.md, no live batch,
      target is bootstrapped)
- [ ] Sections A–C walked; input collected per mode
- [ ] Phase 3 distillation produced; lint result recorded
- [ ] User Approve received
- [ ] `target/DESIGN.md` written exactly once with correct
      `lint_status` frontmatter
- [ ] Phase 5 scan run; candidates printed with insertion suggestion
      and ready-to-paste text
- [ ] Closing report printed; no other files modified
