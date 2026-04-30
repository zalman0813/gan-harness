# Grill Protocol

The discipline `prd-workflow` follows during Phase 1 (Grill). Loaded by MAIN session when entering grill phase. Detailed rules + output formats live here so SKILL.md stays at orchestration level.

## Core rules

1. **One question at a time.** Each `AskUserQuestion` covers exactly one branch of the design tree. Wait for the answer before asking the next.

2. **Surface assumptions before any question.** Initial assumptions list precedes the first grill question. New assumptions surfaced mid-grill go into the same explicit format and get user confirmation.

3. **Recommend before asking.** Every question carries your recommended answer + 1-line rationale. The user approves / edits / overrides — they don't decide blind.

4. **Reframe vague targets as success criteria.** When the user gives an immeasurable target ("make it fast", "make it secure"), translate into concrete testable conditions and rebound:

   ```
   USER: "Make password reset secure"

   REFRAMED SUCCESS CRITERIA:
   - Reset tokens have ≥128-bit entropy
   - Tokens expire after 15 minutes (configurable)
   - Tokens are single-use (consumed after first verification)
   - Failed attempts logged with rate-limit trigger after 5/hour per IP
   → Are these the right targets?
   ```

   Each reframed bullet becomes a candidate AC checkbox. The user can approve / edit / drop any bullet. Vague targets that don't get reframed become assumption debt — don't let them through.

5. **Surface contradictions, don't auto-resolve.** If the user said A in R1 and not-A in R2, ask: "You said A on line 3 and not-A on line 7 — which?". No silent reconciliation.

6. **Cross-check against `CONTEXT.md`.** Every domain term mentioned by the user — see if it's already defined. If yes, use the canonical definition. If no, draft and add to that R's `### Domain terms (draft)` section. If conflicting, surface the conflict.

7. **Cross-check against `docs/adr/index.md`.** If the user wants something that contradicts an accepted ADR, surface it: "ADR-NNNN says X; you're asking for not-X. Want to revisit the ADR, or rescope?". Don't propose new ADRs (that's planner's job).

## What grill covers per R

For each R, walk the design tree until all six sub-sections of `prd.md` (per § Output format below) are concrete. Coverage checklist:

- **Problem** — what's wrong now, user-perspective, 1-2 sentences
- **Solution** — what the user gets, user-perspective, 1-2 sentences
- **User Stories** — at least one Cohn-form ("As a `<role>`, I want a `<feature>`, so that `<benefit>`"), happy path AND discoverable error paths
- **Acceptance Criteria** — binary, testable claims as bullets, ≤10 per R (over 10 → split the R)
- **Constraints** — limits, performance bounds, compliance, integration constraints (apply Reframe pattern when vague)
- **Domain terms (draft)** — any new domain concept; bold name + 1-sentence definition + `_Avoid_` aliases

## Codebase questions are separate

When the user asserts something about the existing codebase ("use the existing session model"), DO NOT verify in the grill — write the question to the research queue and let Phase 3 fact-finders verify. The grill stays user-facing; codebase verification is a separate concern.

Example user statement: "Use the existing email service for sending the reset link."
→ Do NOT search the codebase for the email service in Phase 1.
→ DO write `Q-NN — Where is the existing email-sending service defined and what's its interface?` to `_research-queue.md`.

## Cross-R coherence

After all R individually pass coverage, ask:

- "Are R1 and R2 actually independent, or does one depend on the other?" (surface dependencies → planner uses these for `depends_on` DAG)
- "R1 references **Customer**, R2 references **User**. Are these the same?" (surface term-overlap conflicts)
- "R3's AC contradicts R1's Constraint. Resolve?" (surface logical contradictions)

Cross-R is the last grill round before declaring grill done.

## Output format — `specs/_batch/prd.md`

```markdown
# Batch PRD — <batch-slug>

<one-line batch summary capturing the overarching goal>

## R1 — <r-slug>

### Problem
<1-2 sentences, user perspective>

### Solution
<1-2 sentences, user perspective>

### User Stories
1. As a <role>, I want a <feature>, so that <benefit>.
2. As a <role>, I want a <feature>, so that <benefit>.

### Acceptance Criteria
- [ ] <binary, testable claim>
- [ ] <binary, testable claim>

### Constraints
- <constraint>
- <constraint>

### Domain terms (draft)
**TermName**:
<one-sentence definition: what it IS, not what it does>
_Avoid_: <synonym1>, <synonym2>

## R2 — <r-slug>

(same six sub-sections)
```

Required sub-sections per R: `### Problem`, `### Solution`, `### User Stories`, `### Acceptance Criteria`, `### Constraints`, `### Domain terms (draft)`. If a section has no content, write the literal text `_(none)_` so `prd_lint.py` can verify the structure.

**Forbidden sub-sections** (industry convention: PRD = what/why, plan = how; enforced by `prd_lint.py` L06):

- `### Implementation Decisions`
- `### Tech Stack`
- `### Architecture`
- `### Risks` / `### Tech Debt`
- `### Timeline`

If something feels architectural, it's a candidate ADR — but ADR proposals come from the planner at /plan, not from grill.

## Output format — `specs/_batch/_research-queue.md`

Transient file. Exists between grill and Phase 3 dispatch, deleted at Phase 4 synth. Contains ONLY questions, no requirement context (blindfold preserved at file level).

```markdown
# Research Queue — <batch-slug>

base_for_dispatch: <ISO timestamp grill completed>

## Q-01 — <one-line question>

<optional: 1-2 sentences clarifying scope>

## Q-02 — <one-line question>

(...)
```

Each Q-NN is self-contained — a fact-finder can answer it without reading `prd.md`.

**Good** (specific + verifiable):
- "Where is the user session model defined and what's its full type signature?"
- "What email-sending library does the codebase use and what's its public API?"
- "Does the codebase have rate-limit middleware? If yes, what's its interface?"

**Bad** (vague or interpretive — don't write these):
- "Does our app handle 2FA?" — what does "handle" mean?
- "Is the codebase ready for password reset?" — subjective, fact-finder can only report facts
- "Do we use good security practices?" — opinion, not fact

## Done-with-grill checklist

Before writing files and returning control, verify:

- [ ] Every R has all six required sub-sections (or `_(none)_` if deliberately empty)
- [ ] Every Cohn-form story has `<role>`, `<feature>`, `<benefit>` filled
- [ ] Every AC bullet is binary and testable (not aspirational)
- [ ] Every vague target was reframed into measurable conditions and confirmed
- [ ] Cross-R coherence pass complete (dependencies surfaced, term conflicts resolved)
- [ ] All assumptions surfaced and confirmed by user (none silent)
- [ ] All codebase claims by user routed to `_research-queue.md`, not verified inline
