# Deep Module Handbook — Foundation

Shared by all consuming agents (planner, generator, evaluator). Always
read this first before reading your role's slice.

## §1 Definitions

The depth axis itself is qualitative — Ousterhout deliberately offers no
`depth_score` arithmetic gate. He DOES, however, endorse class size
**200–2000 LOC** as an acceptable range (CS190 modular-design lecture);
"classitis" (lots of tiny classes) is a positive shallow signal, not a
verdict. Use the LOC band as a sanity proxy, never as a pass/fail axis.

| Term | Definition | Qualitative check |
|---|---|---|
| **Deep module** | Hides substantially more complexity than its interface exposes; provides high leverage per unit of interface the caller must learn (Ousterhout APOSD ch.4; Pocock 2026 LANGUAGE.md). | Could a maintainer reconstruct the implementation correctly from the public signatures alone? Yes → shallow. No → deep. AND: can you name in one sentence the design decision this module owns (Parnas 1972)? Yes → depth has a target. |
| **Shallow module** | Interface is comparable in complexity to implementation | Public surface item count ≈ private item count; or all behavior is implied by signatures |
| **Interface** (broad, Pocock LANGUAGE.md) | Everything a caller must know to use the module correctly: signatures **plus** invariants, ordering constraints, and error modes — NOT just the type signatures | When listing what a new caller must learn before they can call this module, do you have to mention an invariant ("must be initialised first"), an ordering rule, or a non-obvious error mode? Each such item IS part of the interface — count it. |
| **Information hiding (Parnas)** | A module hides one **design decision likely to change** (Parnas 1972) | Write down in one sentence: "this module hides X". If you cannot, the module's boundary is wrong. Parnas's bar is sharper than generic "encapsulation" — X must be a decision likely to change, not "just implementation detail". |
| **Pass-through method** | Public method that does little except invoke another with similar signature (Ousterhout APOSD ch.5) | Removing this method would only require renaming one callsite (no other change at the callsite) |
| **Leaky abstraction** | Caller must know implementation details to use the interface correctly (Spolsky 2002) | List all implementation facts a caller must memorize. Each item is a leak. |
| **Anti-corruption layer (ACL)** | Boundary translation layer between two bounded contexts; foreign types do not cross into the domain (Evans DDD) | Any third-party SDK class name appearing in domain-layer imports = ACL bypassed |
| **Bounded context** | Linguistic boundary inside which a domain term has a single, consistent meaning (Evans DDD) | The same word ("Order", "User") may mean different things across contexts; one BC = one meaning |
| **Ubiquitous language** | Vocabulary shared by domain experts, code, and (in this harness) AI agents (Evans DDD) | Terms appear verbatim in code identifiers, in CONTEXT.md, in agent conversations, in PRDs |

> **Depth ≠ monolithic implementation** (Pocock LANGUAGE.md). Depth is a
> property of the *interface*, not the *implementation*. A deep module
> can be internally composed of small, mockable, swappable parts —
> what matters is that callers only learn the deepened interface, not
> the internal seams. Do not reject a well-decomposed module as
> "shallow" just because its implementation is split across helpers.

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

The grey zone (something doesn't clearly fit any row above) is a
contract-negotiation discussion item for generator+evaluator — surface
it in the sprint contract's `done_looks_like` narrative or as an
evaluator finding during NEGOTIATE, not a silent decision.

## §3.5 Success criteria — PASS checklist (positive, with sources)

The current §5 catalogue lists negative red flags ("what makes this
shallow / leaky / smelly"). This section is the **positive complement**:
the criteria a module must SATISFY to be called deep. Use it to write
PASS verdicts, not just FAIL ones.

Apply only when §3 puts the module in an "apply deep module" row (the
opt-out rows — DTO, framework-shaped, hot-path, one-shot — should NOT
be measured against this checklist).

| # | Criterion | Source | Concrete check |
|---|---|---|---|
| **C1** | **Name the hidden decision** | Parnas 1972 (criterion-based decomposition) | The module's `hides_decision` field is a ≥30-char sentence naming one design decision likely to change. Evaluator can falsify it within 1 minute? Then C1 fails — the sentence was ceremony. |
| **C2** | **3-question self-test** | Ousterhout CS190 modular-design lecture | (a) "What unique value does this module provide?" — answerable in one sentence. (b) "What key knowledge does it use to provide that value?" — nameable. (c) "What's the LEAST of that knowledge that must be exposed through the interface?" — driven below the obvious. If any answer is "I don't know" or "everything", C2 fails. |
| **C3** | **Deletion test** | Pocock LANGUAGE.md ("interface = test surface"); Ousterhout APOSD ch.5 implicitly | If you removed this module, would complexity reappear in ≥2 distinct callers? Yes → C3 passes (module earns its existence). No (single caller, or trivial inline replacement) → C3 fails (pass-through risk). |
| **C4** | **Entry-point budget** | Pocock INTERFACE-DESIGN.md ("minimise the interface — 1-3 entry points max") | Count public methods / exported functions / surface routes. ≤ 1-3 entry points → C4 passes. ≥ 4 → C4 needs justification (genuine multi-use module like Unix file API which has 5 calls IS valid; "I needed lots of getters" is not). |
| **C5** | **Two-adapter rule for ports** | Pocock LANGUAGE.md ("one adapter = hypothetical seam; two adapters = real seam") | If the module exposes a Strategy / DI / port interface, ≥2 actual implementations must exist (or one + one named imminent with a hard date). One implementation = the interface is a hypothetical seam = YAGNI; collapse to direct dependency. |
| **C6** | **Interface is everything callers must know** | Pocock LANGUAGE.md (broader interface definition; see §1) | The "interface" is signature + invariants + ordering constraints + error modes. C6 passes when each of those four is either declared in code (type, contract) OR documented at the call site (docstring, README), AND callers don't need to read the implementation to discover any of them. |
| **C7** | **Interface = test surface** | Pocock LANGUAGE.md (tests at deepened interface survive internal refactor); APOSD ch.6 indirectly | Tests for this module exercise the public interface only. They survive an internal refactor of the module's helpers without changes. If renaming an internal helper breaks a test → that test is testing implementation, not interface; C7 fails. |
| **C8** | **Class-size sanity proxy** | Ousterhout CS190 (200-2000 LOC band) | Module LOC is in the 200-2000 range (qualitative — files much smaller may be "classitis" instances; files much larger may be unrelated concerns bundled). NOT a verdict on its own; a 30-LOC genuinely-thin facade can be deep, a 3000-LOC genuinely-cohesive parser can be deep. Use as a "look here first" tap, then apply C1-C7. |

### How to use the checklist

- **Generator NEGOTIATE phase** (proposing a sprint contract): for each
  module the sprint touches, write C1 (hides_decision sentence), C2 (3-
  question answers), C5 (any Strategy seam needs ≥2 actual impls)
  into `done_looks_like[]` narrative items. C4 (entry-point budget) and
  C6 (broad interface) are committed to as future constraints.
- **Generator IMPLEMENT phase**: hold C6 (interface = invariants +
  ordering + error modes in docstring) and C7 (tests at interface only,
  no mocking internal collaborators) live throughout implementation.
- **Evaluator NEGOTIATE phase** (reviewing the proposed contract):
  spot-check each module-touching `done_looks_like` item against
  C1-C5. Surface concerns as contract-amendment proposals before
  agreeing.
- **Evaluator VERIFY phase**: cite the criterion # when emitting a
  PASS verdict's `design_review` paragraph — "C1 passes (hides_decision
  is non-trivially true)", "C3 passes (deletion test fires; three
  callers would regrow the cursor-signing logic)". Cite the criterion
  # when emitting a FAIL — "C5 fails (Strategy seam introduced for one
  named implementation; second impl is hypothetical)". C7 verification
  = renaming an internal helper must not break tests. C8 is an
  outcome observation.

The checklist is a vocabulary, NOT a mandatory walk. If a module is
obviously deep (Unix-file-API-shaped), citing C1+C2+C4 is enough; not
every module needs an 8-criterion narrative. If a module is borderline,
the criteria are how you write down WHY you accepted or rejected it.

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
   is a candidate pass-through. **Pocock's two-adapter rule** (the
   quantitative go/no-go from LANGUAGE.md): "One adapter = hypothetical
   seam. Two adapters = real seam." Introduce a Strategy / port only
   when ≥2 actual implementations exist, or one + one named imminent
   with a hard date. One implementation = collapse to direct
   dependency; the seam isn't earning its existence. (See §3.5 C5.)

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
                                     red flags surface as
                                     contract-amendment items
                                     (generator-side) or design_review
                                     findings (evaluator-side); the
                                     evaluator's threshold check
                                     decides verdict>
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

Used by `fake-deep-pass-through` and as part of §3.5 C3 (deletion test). Generator runs it at NEGOTIATE time when sizing a new module boundary; evaluator runs it at VERIFY time when auditing committed code.

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
- mattpocock/skills `improve-codebase-architecture` —
  https://github.com/mattpocock/skills/tree/main/skills/engineering/improve-codebase-architecture
  - SKILL.md — overall workflow
  - LANGUAGE.md — interface as everything callers must know;
    depth = leverage at the interface; two-adapter rule; deletion
    test; interface = test surface
  - INTERFACE-DESIGN.md — 1-3 entry-point budget; "design it twice"
    contrast on depth / locality / seam-placement
  - DEEPENING.md — process for turning shallow modules into deep
    ones (extract-then-deepen pattern)
- John Ousterhout, CS190 Modular Design lecture (Stanford) —
  https://web.stanford.edu/~ouster/cgi-bin/cs190-winter18/lecture.php?topic=modularDesign
  (3-question self-test; 200-2000 LOC class-size endorsement)

Critical conversation pieces (Fowler network on AI coding × DDD):
- Birgitta Böckeler, "Harness Engineering — first thoughts" (Feb 2026)
  — https://martinfowler.com/articles/exploring-gen-ai/harness-engineering-memo.html
- Erik Doernenburg, "Assessing internal quality while coding with an
  agent" (Jan 2026) —
  https://martinfowler.com/articles/exploring-gen-ai/ccmenu-quality.html
- Martin Fowler + Unmesh Joshi, "LLMs and Building Abstractions" —
  https://martinfowler.com/articles/convo-llm-abstractions.html
