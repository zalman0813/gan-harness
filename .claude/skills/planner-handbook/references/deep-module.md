# Deep Module — Theory + Heuristic

The planner reads this when deciding module boundaries. Stack-specific examples live in the active stack skill's `references/`; this file is language-free theory.

## Ousterhout's framing

> A **deep module** hides substantially more complexity than its interface exposes. A **shallow module** has an interface nearly as complex as its implementation.

Module **cost** = what every caller must learn:
- Public functions / types / methods
- Required configuration keys / constructor params
- Distinct error or exception types raised
- Temporal-ordering constraints (e.g. must call `init()` before `start()`)
- Invariants the caller must maintain

Module **benefit** = how much functionality is hidden behind that surface (proxied by implementation LOC).

Best modules maximize `benefit / cost`.

**Canonical deep example** — Unix file I/O: 5 calls (`open`, `read`, `write`, `lseek`, `close`) hide files, directories, permissions, concurrency, and devices.

**Canonical shallow example** — `java.io`: `new ObjectInputStream(new BufferedInputStream(new FileInputStream(name)))` forces 3 classes for a single conceptual operation.

## Pocock's adaptation for AI coding

LLMs trained on "small file = readable" extract every helper into its own file, producing sprawl: many tiny single-purpose modules with thin interfaces that pass arguments through. This:

1. **Inflates token cost** when the model later reads its own code (pushing past the ~100K "smart zone")
2. **Destroys locality** — bugs hide in the call-graph between modules, not inside any one
3. **Breaks the deletion test** — if removing a module would not concentrate complexity in ≥2 callers, it's a pass-through

**Counter-rule**: design the interface, delegate the implementation. Treat each module as a "gray box" — the planner locks the interface; the generator implements the body.

## Heuristic — `depth_score` (planner doctrine, not lint-enforced)

For each feature you design, internally estimate:

```
depth_score = impl_LOC / max(public_surface, 1)

public_surface =
    count(public functions/methods exported from barrel)
  + count(public types/classes exported)
  + count(required config keys / constructor params)
  + count(distinct error / exception types raised through public API)
  + count(temporal-ordering constraints)
```

Target: `depth_score ≥ 5`. Below 3 is clearly shallow — refactor the design before committing it to `feature-list.json`. The threshold 5 is anchored to Unix I/O (~5 calls hides thousands of LOC).

`impl_LOC` is your *estimated* implementation size; the active stack skill provides the public-surface counting rule for its language.

**This is planner doctrine, not a lint check.** The harness does not measure depth at self-verify time because both inputs (impl estimate, stack-specific counting) have edge cases that defeat mechanical scoring. Apply the heuristic during design; lint catches phase-named features and missing `l5_smoke_path`, not module depth.

## Pocock deletion test (companion check)

For any module the planner is about to add:

> If I removed this module, would the complexity concentrate in ≥2 distinct callers?

- **Yes** → the module earns its existence. Keep.
- **No** (single caller, or trivial inline replacement) → it's a pass-through. Merge into the caller, or merge with an adjacent module.

Lint records this as a separate signal: any module with exactly one caller fails the deletion test regardless of `depth_score`.

## Six fake-deep anti-patterns

LLMs are prone to all of these. The planner must flag and refactor.

1. **Pass-through wrapper** — body just calls another method with the same signature. Often emitted to "name" a step.
   ```
   void addNullValueForAttribute(String attr) { data.put(attr, null); }
   ```
   *Fix*: caller uses `data.put(attr, null)` directly.

2. **Decorator stack** — small interface per layer, but caller must know N layers + composition order. Total surface > sum of layer surfaces.
   ```
   new ObjectInputStream(new BufferedInputStream(new FileInputStream(name)))
   ```
   *Fix*: a single facade hides composition.

3. **Config-leak** — single public function but accepts a 20-field options object. The options *are* the interface.
   *Fix*: split into 2-3 functions each taking only what it needs, or make the options a documented value type with sensible defaults reducing required fields to ≤3.

4. **Exception-leak** — function looks simple but raises 6 distinct exception types the caller must handle.
   *Fix*: collapse into 2-3 semantic categories at the boundary; map internal errors to public categories.

5. **Temporal coupling** — `init()` then `start()` then `configure()`. Ordering is part of the interface even if signatures are small.
   *Fix*: builder pattern, or a single `start(config)` that absorbs phases.

6. **Wrapper-around-stdlib** — `MyStringUtils.isEmpty(s)` over `s.length() == 0`. Deletion test fails (callers gain nothing).
   *Fix*: delete the wrapper.

## How the planner applies this

In Phase 2, for each feature the planner:

1. Lists the proposed module's `public_surface` items (functions, types, config, errors, ordering)
2. Estimates `impl_LOC` from the AC complexity
3. Computes `depth_score`
4. Checks the deletion test
5. Scans for the 6 fake-deep patterns

If any signal trips, refactor the design before writing it into `feature-list.json`. The lint will catch it later regardless; iterating in design is cheaper than iterating after lint FAIL.

## Sources

- John Ousterhout, *A Philosophy of Software Design* (2018), ch. 4-5, ch. 7, ch. 9
- Matt Pocock, *It Ain't Broke: Why Software Fundamentals Matter More Than Ever* (AI Engineer, 2026)
- mattpocock/skills `improve-codebase-architecture` (deletion test, "interface = test surface")
