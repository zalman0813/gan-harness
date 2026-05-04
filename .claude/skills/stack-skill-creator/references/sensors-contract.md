# sensors.ini — stack sensor command contract

Every stack skill under `.claude/skills/<stack>/` MUST provide a
`sensors.ini` at its top level (sibling of `SKILL.md`, alongside
`references/`). It declares the lint/typecheck/test/ACL commands the
harness gates invoke for this stack.

The harness gates that consume `sensors.ini`:

- `.claude/skills/generator-handbook/scripts/gate_gen_precommit.py` —
  generator's pre-commit gate (Stripe-style two stages: <1s autofix →
  <5s read-only check). Internal stages cover lint.fix → lint.check →
  typecheck → test.unit → AC literal coverage → module ACL.
- `.claude/skills/evaluator-handbook/scripts/gate_eval_postcommit.py` —
  evaluator's L1+L2 wrapper (full `module_path` scope + optional L5
  smoke). The evaluator's grading process verifies AC literal coverage
  independently as the GAN-pattern adversarial check (per
  `evaluator.md` Principle #4); this gate handles only L1/L2/L5.
- Mutation testing reads `[mutation]` sensors.ini keys; wire a
  stack-specific adapter when a stack needs it.

## Required sections and keys

| Section | Required keys | Optional keys |
|---|---|---|
| `[lint]` | `fix`, `check` | — |
| `[typecheck]` | `command` | — |
| `[test]` | `unit` | `smoke` |
| `[acl]` | `tool` | `config_format`, `invoke` (mandatory when `tool` ≠ `none`) |
| `[anchors]` | — | `language`, `extra_absence_markers` |
| `[mutation]` | `tool` | `run`, `summary` (mandatory when `tool` ≠ `none`) |

`configparser` (Python stdlib) is the parser. Comments use `#` or `;`
at line start.

## Placeholders

The harness substitutes these in any command string before execution:

| Placeholder | Substituted by | Value |
|---|---|---|
| `{scope}` | `gate_gen_precommit.py` / `gate_eval_postcommit.py` | gen: changed files (`git diff --name-only`); eval: `feature.module_path` |
| `{config_path}` | `gate_gen_precommit.py` (module-ACL stage) | path to a temp config file rendered from `feature.acl_pairs[]` |

ALWAYS quote `{scope}` in the command string if your tool is
whitespace-sensitive (most modern lints handle multiple paths).

## ACL tools the harness understands today

| `tool =` | `config_format` | Notes |
|---|---|---|
| `import-linter` | `ini` | Python. `pip install import-linter`. The pre-commit gate's inlined module-ACL stage renders forbidden-contracts. |
| `dependency-cruiser` | `cjs` | TS/JS. `npm i -D dependency-cruiser`. The pre-commit gate renders forbidden rules array. |
| `none` | — | Stack has no ACL enforcement (the module-ACL stage is skipped). |

For other stacks, set `tool = none` until a per-stack adapter ships.

## Mutation-testing tools the harness understands today

| `tool =` | Notes |
|---|---|
| `mutmut` | Python. `pip install mutmut`. The future mutation adapter would parse `mutmut results` text output ("Killed X/Y", "Survived A/B"). |
| `stryker` | TS/JS. Stub — adapter not implemented. |
| `pit` | Java. Stub — adapter not implemented. |
| `none` | Stack has no mutation enforcement. |

Mutation testing is **not currently wired** into either harness gate.
The `[mutation]` sensors.ini keys exist as a forward-compatibility slot
— a future stack adapter or T15 e2e-bundle work can call them directly
from a per-stack script. `feature.mutation_threshold` (integer 0–100,
default 70) is the FAIL threshold convention if a stack wires this up.

For tools where mutation testing is too slow per-round (some Java/PIT
configurations), consider running mutation as a `/finalize`-time gate
rather than per-round. The `run` and `summary` commands are pluggable;
this contract does not constrain when they fire.

## Empty values = skip

If a key value is empty (e.g., `smoke =`), the harness skips that step
silently. `quality-gate` will not error on an empty `smoke` even when
`feature.test_contract.l5_smoke_path` is set; it logs a SKIPPED note.

## Self-validation

After emit, stack-skill-creator runs these checks:

1. File exists at `.claude/skills/<stack>/sensors.ini`
2. All required sections + keys present
3. `acl.tool` ∈ {`import-linter`, `dependency-cruiser`, `none`}
4. If `acl.tool ≠ none`, `acl.config_format` and `acl.invoke` are
   non-empty
5. Every command string parses as a non-empty token list

A failed check aborts skill creation — fix sensors.ini before retry.

## Template

See `templates/sensors.ini.template` for a fully-annotated Python
(Ruff + mypy + pytest + import-linter) example. New stacks copy it,
substitute commands, and validate.

## Why a separate file (vs putting commands in SKILL.md)

`sensors.ini` is **machine-readable**: hooks parse it directly. Putting
commands in SKILL.md prose would force every gate to re-implement
fragile markdown extraction. Separating "human prose" (SKILL.md +
references/) from "harness contract" (sensors.ini) keeps each stable.
