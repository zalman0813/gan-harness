# Vertical Slice — Theory + Lint Signals

The planner reads this when deciding feature decomposition. The active stack skill provides language-specific layer scaffolding; this file is the language-free rule.

## Horthy's vertical vs horizontal

A **horizontal plan** sequences work by layer:

```
F01: all DB migrations
F02: all API endpoints
F03: all services
F04: all UI
```

After F04 you have ~2000 lines of code that has never run end-to-end. If something is broken, you don't know which phase introduced it. Worse, the model wrote four phases without ever testing one against the other.

A **vertical plan** sequences work by user-observable outcome:

```
F01: place order — UI form + API endpoint + service stub + DB migration
F02: cancel order — same layers, new flow
F03: list orders — same layers, read-side
```

Each feature is end-to-end runnable on its own. Bugs surface within one feature, not across four.

> The rate of feedback is your speed limit.

## Layer-spanning rule

Each feature's `module_path` must touch every layer the feature description implies. The active stack skill defines what "layer" means in its idioms (UI / API / service / DB for full-stack apps; single-process for libraries; etc.).

Concrete signal: a feature whose description involves user interaction but whose `module_path` only touches a backend directory is suspect — either the description is wrong or the feature is a horizontal slice.

## Build order within a slice

Inside one feature, build top-down with mocks at each cut:

```
1. Mock the API endpoint, returning canned data (no service, no DB)
2. Wire the frontend to the mock; get UI rendering with real shape
3. Replace mock with real service backed by in-memory data (no DB yet)
4. Add DB migration; switch service to persistent backing
5. Run L5 smoke end-to-end
```

Each step has a checkpoint where the harness can run a partial test. The active stack skill's vertical-slice references describe this scaffold concretely.

## Anti-horizontal lint signals (`plan_lint.py L10`)

L10 flags any of these patterns:

- **Phase-named features** — `phase-1-database`, `migration-only`, `api-skeleton`, `db-setup`, `ui-only`. Reject.
- **Single-layer touches** — feature has a UI-implying user_story but `module_path` only matches a backend pattern (or vice versa)
- **Sequential horizontal chain** — `depends_on` describes a chain like `F01 (db) → F02 (api) → F03 (ui)` where each F covers exactly one layer
- **Missing l5_smoke_path on UI features** — if `module_path` matches a UI pattern (per stack skill), `l5_smoke_path` MUST be non-null

The stack skill provides the regex/glob patterns for "UI", "API", "service", "DB" in its idioms; harness core does the matching.

## When horizontal IS OK

There is one legitimate case: pure infrastructure or schema migrations that have no user-observable behaviour and exist only to enable later vertical features. These should:

- Be tagged `priority: P3` (nice-to-have on their own; not shippable alone)
- Have `kind: error` or descriptive AC explaining why they exist
- Be referenced via `depends_on` from at least one vertical feature in the same batch (so they don't ship orphaned)

If none of these apply, it's not infrastructure — it's an accidental horizontal slice.

## How the planner applies this

In Phase 2, for each candidate feature:

1. Read the user_story
2. Determine which layers it implies (per stack skill conventions)
3. Verify `module_path` covers all implied layers
4. Verify the build order in the feature's spec describes a vertical sequence (mock → wire → real)
5. Set `l5_smoke_path` if UI is implied
6. Reject any phase-named features; rewrite as vertical decomposition

## Sources

- Dexter Horthy, *Everything We Got Wrong About Research-Plan-Implement* (MLOps.community, 2026-03)
- Pragmatic Programmer, ch. on small deliberate steps and feedback loops
