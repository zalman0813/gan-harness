# L5 E2E Workflow — methodology

The methodology evaluator follows for the L5 (smoke / end-to-end) stage.
**Stack-specific commands live in the stack skill** (e.g. `playwright-cli`
for Next.js, `flutter-driver` for Flutter); this document only defines
WHAT to verify and HOW to grade.

## When this applies

L5 is invoked **whenever** a feature has both:
- `feature.test_contract.l5_smoke_path` — non-null in feature-list.json
- The active stack's `sensors.ini` has a non-empty `[test] smoke` command

If both conditions are met, L5 is **mandatory** for that feature's verdict.
If either is empty, the feature is "L5 not applicable" — record this in
the eval JSON and move on. There is no third "deferred to a future skill"
state.

## Non-runnable rule

If L5 cannot be executed (server fails to start, browser tooling crashes,
selectors unresolvable, dependency missing), the result is **never** a
silent SKIP. Two paths:

- **Code-bug class** (selector mismatch, page crash on render, assertion
  failure) → record as FAIL on the relevant AC, generator's R2 fixes it.
- **Environment / human-fixable class** (auth expired, external service
  down, missing local config, port already in use) → write
  `specs/_batch/_escalations/F{NN}-eval-R{N}.json` describing what
  blocked you and what the operator must do, return without verdict.
  See `escalation.md`.

The classification heuristic: did the failure come from inside the app
under test (code) or from outside (env)? If the same code would pass on
a freshly-set-up machine, it's env. If it would still fail, it's code.

"Could not verify" is FAIL by default — the burden is on you to
classify, not on the operator to ask.

## Six-step workflow

How each step is performed (browser launch, screenshot capture, selector
syntax) is specified by the stack skill, not here.

| # | Step | Purpose |
|---|---|---|
| 1 | Pre-flight | Verify prerequisites — server can start, creds exist if the spec touches authenticated paths. Escalate now if blocked. |
| 2 | Launch | Start server (typically via the stack's webServer config); establish browser/inspection channel. |
| 3 | Structural | Walk the live DOM / element tree; assert expected structure exists (see "Property over Value" below). |
| 4 | Visual smoke | Capture rendered screen; check no layout/render disasters (see criteria below). |
| 5 | Adversarial | Inject one edge-case data scenario per AC where the AC has a boundary; restart cleanly if the test framework supports it. |
| 6 | Cleanup | Stop server cleanly. No orphan processes — they will collide with the next feature's L5. |

## Assertion discipline: Property over Value

E2E assertions verify **structural properties**, not specific copy:

| Property (do) | Value (don't) |
|---|---|
| `<article data-row>` exists for each item in the list | "first row text says 'crawler-X'" |
| A non-empty text node renders inside `<header>` after fetch | "the title reads 'Pending: 3'" |
| An error fallback element renders for bad input | "the error message reads 'Parse failed'" |
| After click, the URL pathname changes to `/.+/trace` | "URL equals `/monitor/trace?key=foo`" |

Property assertions survive copy / i18n / data changes. Value assertions
can be gamed by tailoring seed data to match exact strings.

## Assertion types

- **Existence** — a node of the expected role / type exists
- **Cardinality** — count of matching nodes equals expected N (or N≥1)
- **State** — `aria-pressed` / `disabled` / `data-X` reflects expected state
- **Absence** — no error / crash / unhandled-exception element visible
- **Transition** — after an interaction, new-screen elements appear

## Visual smoke — minimal criteria

A screenshot from step 4 must show none of:

- Overlapping elements (text bleeding into another component)
- Clipped text on visible-by-default content
- Unhandled error banner / red error screen / "Application Error" text
- Blank where data was expected and no empty-state design rendered

These are FAIL signals visible to a human reviewer. No pixel-perfect
parity check unless the feature spec explicitly references a design
artefact — admin / data-display features rarely do.

## Evidence — how to capture, where it goes, what to list

Per-feature, per-round evidence directory:

```
specs/_batch/_traces/F{NN}-eval-R{N}-screenshots/
```

Not `/tmp/`, not the runner's default cache (`node_modules/.playwright/test-results/`,
`.flutter_tool/screenshots/`, Cypress's `cypress/screenshots/`, etc.).
The per-feature dir means the next round's generator and a future
maintainer audit can find the artefacts without hunting the runner's
transient location.

### Capture: redirect the runner's output

The smoke command in `sensors.ini` is intentionally minimal — most
runners default their output to a project-relative cache dir, not
your evidence dir. **Wrap the smoke command** with the runner's
output-redirect flag so artefacts land where doctrine says.

For Playwright (the typical Next.js / web stack):

```
mkdir -p specs/_batch/_traces/F{NN}-eval-R{N}-screenshots
pnpm --filter <pkg> exec playwright test \
     --output=specs/_batch/_traces/F{NN}-eval-R{N}-screenshots \
     {scope}
```

Equivalent flags exist for most stacks (Cypress `--config screenshotsFolder=...`,
Flutter `--reporter=...` + integration_test config). If the runner
has no redirect flag, do the run, then `cp -r` / `rsync` the default
output dir into evidence-dir before listing.

### What ends up in evidence-dir

After a Playwright run with `--output`:
- `trace.zip` per failing test — DOM snapshot, console, network log
- `video.webm` per failing test (if `video: 'on-failure'` in playwright.config)
- `*.png` for assertion-failure auto-screenshots and any explicit
  `await page.screenshot({...})` calls in the spec
- Per-test subdirs named after the spec + AC

A clean PASS with **no explicit `page.screenshot()` in the spec**
produces an essentially empty evidence dir. That is itself a signal —
visual smoke grading happened via test-suite execution only, not
per-step screen capture. Note this explicitly in the eval JSON; do
not leave the field misleading.

### List in eval JSON

The eval JSON's top-level `evidence[]` field MUST be non-empty when L5
ran:

- If artefacts were captured → list every file by repo-relative path:
  `["specs/_batch/_traces/F03-eval-R1-screenshots/trace.zip",
    "specs/_batch/_traces/F03-eval-R1-screenshots/health-overview-AC-12-chromium/video.webm"]`
- If the run produced no artefacts (clean PASS, no explicit screenshots
  in spec) → emit a single-element note string:
  `["L5 PASS via test-suite execution; no per-step screenshots captured by spec"]`

**Empty `evidence[]` when L5 ran is a doctrine violation** — either
the artefacts went somewhere (find them, list them) or the run
produced none (note it). Silence is the failure mode that motivated
this section.

## Domain boundary

L5 is **evaluator-only**. Generator does not load this document, does
not invoke browser tooling, does not start the server. Generator's
build-time smoke equivalent is the pre-commit hook running the stack's
production-faithful typecheck (e.g. `next build` for Next.js); that
catches build / route / type contract failures before commit. Anything
that requires running the actual app belongs to the evaluator's L5.

`block_pretool.py` enforces the boundary at the tool level — generator
attempting to read this file or invoke the e2e tool skill will be denied.
