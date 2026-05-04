# Deep Module Handbook — Foundation

Shared by all consuming agents (planner, generator, evaluator). Always
read this first before reading your role's slice.

## §1 Definitions

All terms below are qualitative. The previous repo file
(`planner-handbook/references/deep-module.md` before migration) used a
quantitative `depth_score = impl_LOC / public_surface ≥ 5` heuristic
"anchored to Unix I/O has ~5 calls". This anchor was reviewed and found
to conflate the count of public functions with a depth ratio; Ousterhout
gives no numeric threshold in *A Philosophy of Software Design*. The
quantitative gate is dropped; all checks below are qualitative.

| Term | Definition | Qualitative check |
|---|---|---|
| **Deep module** | Hides substantially more complexity than its interface exposes (Ousterhout APOSD ch.4) | Could a maintainer reconstruct the implementation correctly from the public signatures alone? Yes → shallow. No → deep. |
| **Shallow module** | Interface is comparable in complexity to implementation | Public surface item count ≈ private item count; or all behavior is implied by signatures |
| **Information hiding (Parnas)** | A module hides one design decision likely to change (Parnas 1972) | Write down in one sentence: "this module hides X". If you cannot, the module's boundary is wrong. |
| **Pass-through method** | Public method that does little except invoke another with similar signature (Ousterhout APOSD ch.5) | Removing this method would only require renaming one callsite (no other change at the callsite) |
| **Leaky abstraction** | Caller must know implementation details to use the interface correctly (Spolsky 2002) | List all implementation facts a caller must memorize. Each item is a leak. |
| **Anti-corruption layer (ACL)** | Boundary translation layer between two bounded contexts; foreign types do not cross into the domain (Evans DDD) | Any third-party SDK class name appearing in domain-layer imports = ACL bypassed |
| **Bounded context** | Linguistic boundary inside which a domain term has a single, consistent meaning (Evans DDD) | The same word ("Order", "User") may mean different things across contexts; one BC = one meaning |
| **Ubiquitous language** | Vocabulary shared by domain experts, code, and (in this harness) AI agents (Evans DDD) | Terms appear verbatim in code identifiers, in CONTEXT.md, in agent conversations, in PRDs |

## §2 Pocock-calibrated DDD

This methodology adopts a deliberately partial slice of DDD. Pocock's
own clarification on adopting DDD for AI-coding contexts (X post,
paraphrased per Fowler-network research):

> "GOOD: Ubiquitous Language / Bounded Contexts / ADR's. BAD: Entities /
> Value Objects / Aggregates / Domain Events. Use DDD to document the
> app but don't prescribe the shape of the app."

This handbook follows that calibration:

| DDD concept | Status | Why |
|---|---|---|
| Ubiquitous Language | **Required** | Without it, agents and humans use different words for the same thing; design intent leaks into translation cost |
| Bounded Context | **Required** | Without explicit BC, deep modules grow until they absorb unrelated logic = god module |
| ADR | **Required** | Boundary decisions must be auditable |
| Anti-Corruption Layer | **Conditional** (any time you cross to an external system) | Prevents foreign vocabulary from polluting domain |
| Entities | **Not adopted** | Tactical layer; over-prescribes module internal shape |
| Value Objects | **Not adopted** | Same |
| Aggregates | **Not adopted** | Same |
| Domain Events | **Not adopted** | Same |

Three required + one conditional + four not-adopted = "minimum
effective dose" of DDD that prevents god module while keeping the
methodology lightweight.

Sources: Pocock X post (2026, paraphrased via Fowler-network research);
Eric Evans on InfoQ ("a trained language model is a bounded context");
Fowler+Joshi on UbiquitousLanguage
(https://martinfowler.com/articles/convo-llm-abstractions.html).

## §3 Applicability scope — when NOT to apply

Deep-module is a structural design principle, not a universal law.
For each module the planner is about to design, classify it first.

| Module type | Apply deep module? | Reason |
|---|---|---|
| Business logic / workflow orchestration | **Yes** | Primary territory |
| Cross-system integration layer | **Yes — and require ACL** | Primary territory; ACL is the boundary |
| Pure data container (DTO, schema, config dataclass) | **No — keep shallow** | Its essence is "carry data"; hiding makes it harder to read |
| Framework-mandated shape (React hook, ORM model, CLI command) | **No — conform to framework** | "Conform to framework convention" outranks "apply architectural pattern" |
| Performance hot path (parser inner loop, real-time compute) | **No or partial** | Interface call cost is non-negligible |
| One-shot script / migration | **No** | No second caller; depth has no payoff |

The grey zone (something doesn't clearly fit any row above) is the
planner's `open_question` candidate, not a silent decision.

## §4 Cross-cutting tensions

Every consuming agent must know these so they don't accidentally
work against another tradition.

1. **Ousterhout vs Uncle Bob.** Clean Code's "extract till you drop"
   produces many small functions = shallow modules — exactly what
   Ousterhout warns against. **This methodology follows Ousterhout.**
   Generator does not extract helpers reflexively.

2. **Mockist vs Classicist.** London-school (Mockist) testing mocks
   all collaborators and verifies interactions; this freezes the
   internal collaboration graph and defeats deep modules' value.
   **This methodology follows Detroit/Chicago (Classicist):** test
   the public interface, use real internal collaborators, mock only
   process boundaries. (See `generator-slice.md` for implementation.)

3. **Strategy/DI seam vs pass-through smell.** Every injection seam
   is a candidate pass-through. **Discipline:** introduce a Strategy
   only when a real second implementation exists or is imminent
   (planner records the second implementation in the ADR or
   open_question). YAGNI before "predictable variation".

4. **ACL purity vs pass-through smell.** ACL methods may *look like*
   pass-throughs (forward to external). **Diagnostic:** if removing
   the layer would let foreign vocabulary leak into the domain →
   it's an ACL, keep it. If removing the layer only saves one
   indirection → it's a pass-through, delete it.

## §5 Red flags

Format. Each red flag follows this exact schema. Folklore flags rot;
source-cited flags age gracefully.

> **Lint vs evaluator split.** Red flags below are evaluator/planner
> triggers, NOT lint rules. Quantitative proxies (mock count,
> import-edge presence) MAY be linted by stack-skill sensors.
> Qualitative red flags (depth, pass-through, leaky abstraction, etc.)
> stay with the LLM evaluator because they need ownership/semantic
> context lint cannot supply.

```
### 🚩 <flag-id>
- **Source**: <primary source — Ousterhout chapter, Parnas section,
              Fowler bliki URL, etc. Becomes the rot detector: if
              source becomes 404 or contradicts, review the flag.>
- **Pattern**: <abstract description; no instance-specific class names
                or paths>
- **Trigger to investigate**: <yes/no question the agent self-asks>
- **If fires, recommend to user**: <2-4 directions. Never auto-FAIL —
                                     red flags are open_question triggers,
                                     not verdicts>
- **Retirement criteria**: <what conditions would justify removing this
                            flag from doctrine>
```

The flag list is intentionally short (target: 5-8 flags). Adding a
9th flag forces audit of the existing list — if a flag is rarely
fired, retire it before adding new.

### 🚩 fake-deep-pass-through
- **Source**: Ousterhout APOSD ch.5
- **Pattern**: A public method whose body just invokes another method
  with similar signature, often emitted to "name" a step.
- **Trigger to investigate**: For each public method, ask: "If I
  removed this method, would callers only need to rename their call
  to the inner method (no other change)?"
- **If fires, recommend to user**:
  (a) Inline — caller calls the inner method directly
  (b) Merge into adjacent module if both are thin
  (c) Confirm as ACL — if this method translates a foreign type to a
      domain type (foreign-vocabulary diagnostic per §4 row 4)
- **Retirement criteria**: This pattern doesn't fire across 5+
  consecutive batches AND no new variants emerge.

### 🚩 fake-deep-decorator-stack
- **Source**: Ousterhout APOSD ch.4 (Java I/O example)
- **Pattern**: Each layer has a small interface, but the caller must
  know N composition layers and the order. Total surface to learn
  exceeds the sum of individual layers.
- **Trigger to investigate**: How many classes/wrappers must the
  caller chain to perform one conceptual operation?
- **If fires, recommend to user**:
  (a) Single facade hides composition
  (b) Builder if real configuration exists
  (c) Default constructor if defaults work for >80% of cases
- **Retirement criteria**: Stack uses no decorator-pattern libraries
  AND no new variants for 5+ batches.

### 🚩 config-leak
- **Source**: Ousterhout APOSD ch.5 (interface-shape considerations)
- **Pattern**: A single public function accepts an options object
  with many fields; the options *are* the interface, not the function
  name.
- **Trigger to investigate**: Does the public signature contain an
  options/config parameter with more fields than the rest of the
  signature combined?
- **If fires, recommend to user**:
  (a) Split into 2-3 functions, each taking only what it needs
  (b) Make options a documented value type with sensible defaults
      reducing required fields to ≤ 3
- **Retirement criteria**: No options-object pattern in stack idioms
  AND no fires for 5+ batches.

### 🚩 exception-leak
- **Source**: Effective Java Item 73 (Bloch); Ousterhout APOSD ch.10
- **Pattern**: Function looks simple but raises 6+ distinct exception
  types the caller must handle, each from a different abstraction
  level.
- **Trigger to investigate**: Count distinct exception types the
  public method can raise. Are they all expressed in the module's
  abstraction, or does the count include lower-layer types
  (database, HTTP, parser)?
- **If fires, recommend to user**:
  (a) Collapse into 2-3 semantic categories at the boundary
  (b) Wrap lower-layer exceptions; preserve cause via chain
  (c) If one layer is genuinely unforeseeable, keep it but document
- **Retirement criteria**: Stack has automatic exception unification
  AND no fires for 5+ batches.

### 🚩 temporal-coupling
- **Source**: Seemann ploeh.dk "TemporalCoupling"
  (https://blog.ploeh.dk/2011/05/24/DesignSmellTemporalCoupling/)
- **Pattern**: Public methods must be called in a specific order
  (e.g., init() then start() then configure()). Ordering is part of
  the interface even if signatures are small.
- **Trigger to investigate**: Does the README or docstring need a
  sentence beginning "first call X, then call Y"?
- **If fires, recommend to user**:
  (a) Move required setup into constructor — object born valid
  (b) Use immutability — no before/after state
  (c) Single method that absorbs phases (e.g., start(config))
- **Retirement criteria**: Stack convention enforces immutable
  construction AND no fires for 5+ batches.

### 🚩 wrapper-around-stdlib
- **Source**: Ousterhout APOSD ch.5 (cost of unnecessary abstraction)
- **Pattern**: A wrapper that calls a stdlib/well-known function with
  no added semantics (e.g., `MyStringUtils.isEmpty(s)` over
  `s.length() == 0`).
- **Trigger to investigate**: Does the wrapper add any of: input
  validation, logging, retry, alternative dispatch, type translation?
- **If fires, recommend to user**:
  (a) Delete the wrapper; use stdlib directly
  (b) If a real concern is hidden (e.g., "use this for our i18n
      strings"), document it explicitly so the wrapper earns its
      existence
- **Retirement criteria**: Stack convention enforces direct stdlib
  use AND no fires for 5+ batches.

## §5.5 The deletion test (diagnostic, not a flag)

Used by `fake-deep-pass-through` and by planner-slice §2 Q6.

For any module the planner is about to add, ask:

> If I removed this module, would the complexity concentrate in
> ≥ 2 distinct callers?

- **Yes** → the module earns its existence; complexity is genuinely
  centralized. Keep.
- **No** (single caller, or trivial inline replacement) → it's a
  pass-through. Merge into the caller, or merge with an adjacent
  module.

Source: Pocock 2026 "It Ain't Broke" talk; mattpocock/skills
`improve-codebase-architecture` skill ("deletion test", "interface =
test surface").

## §6 Sources (canonical references)

Primary — the doctrine is anchored to these:
- John Ousterhout, *A Philosophy of Software Design* (2018), ch. 4
  (Modules Should Be Deep), ch. 5 (Information Hiding and Leakage),
  ch. 9 (Better Together or Better Apart), ch. 10 (Define Errors
  Out of Existence)
- David Parnas, "On the Criteria To Be Used in Decomposing Systems
  into Modules" (1972) —
  http://sunnyday.mit.edu/16.355/parnas-criteria.html
- Eric Evans, *Domain-Driven Design* (2003) — Bounded Context,
  Ubiquitous Language, Anti-Corruption Layer
- Joshua Bloch, *Effective Java* Item 73 — exception translation
- Joel Spolsky, "The Law of Leaky Abstractions" (2002) —
  https://www.joelonsoftware.com/2002/11/11/the-law-of-leaky-abstractions/

Secondary — informs application:
- Matt Pocock, "It Ain't Broke: Why Software Fundamentals Matter
  More Than Ever" (AI Engineer, 2026) —
  https://www.youtube.com/watch?v=v4F1gFy-hqg
- Mark Seemann, "Design Smell: Temporal Coupling" (2011) —
  https://blog.ploeh.dk/2011/05/24/DesignSmellTemporalCoupling/
- Martin Fowler, "Anti-Corruption Layer" via Legacy Mimic article —
  https://martinfowler.com/articles/patterns-legacy-displacement/legacy-mimic.html
- mattpocock/skills `improve-codebase-architecture` — deletion test
  framing

Critical conversation pieces (Fowler network on AI coding × DDD):
- Birgitta Böckeler, "Harness Engineering — first thoughts" (Feb 2026)
  — https://martinfowler.com/articles/exploring-gen-ai/harness-engineering-memo.html
- Erik Doernenburg, "Assessing internal quality while coding with an
  agent" (Jan 2026) —
  https://martinfowler.com/articles/exploring-gen-ai/ccmenu-quality.html
- Martin Fowler + Unmesh Joshi, "LLMs and Building Abstractions" —
  https://martinfowler.com/articles/convo-llm-abstractions.html
