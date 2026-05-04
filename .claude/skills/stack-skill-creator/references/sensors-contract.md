# sensors.ini — stack sensor command contract

Every stack skill under `.claude/skills/<stack>/` MUST provide a
`sensors.ini` at its top level (sibling of `SKILL.md`, alongside
`references/`). It declares the lint/typecheck/test commands the
harness gates invoke for this stack.

The harness gates that consume `sensors.ini`:

- `.claude/skills/generator-handbook/scripts/gate_gen_precommit.py` —
  generator's pre-commit gate (Stripe-style two stages: <1s autofix →
  <5s read-only check). Internal stages cover lint.fix → lint.check →
  typecheck → test.unit → AC literal coverage. AC literal coverage is
  inlined; there is no separate sensor script.
- `.claude/skills/evaluator-handbook/scripts/gate_eval_postcommit.py` —
  evaluator's L1+L2 wrapper (full `module_path` scope + optional L5
  smoke). The evaluator's grading process verifies AC literal coverage
  independently as the GAN-pattern adversarial check (per
  `evaluator.md` Principle #4); this gate handles only L1/L2/L5.

## Required sections and keys

| Section | Required keys | Optional keys |
|---|---|---|
| `[lint]` | `fix`, `check` | — |
| `[typecheck]` | `command` | — |
| `[test]` | `unit` | `smoke` |

`configparser` (Python stdlib) is the parser. Comments use `#` or `;`
at line start.

## Placeholder

The harness substitutes this in any command string before execution:

| Placeholder | Substituted by | Value |
|---|---|---|
| `{scope}` | `gate_gen_precommit.py` / `gate_eval_postcommit.py` | gen: changed files (`git diff --name-only`); eval: `feature.module_path` (L1), `feature.test_contract.l2_path` (L2), or `feature.test_contract.l5_smoke_path` (L5) |

ALWAYS quote `{scope}` in the command string if your tool is
whitespace-sensitive (most modern lints handle multiple paths).

## Empty values = skip

If a key value is empty (e.g., `smoke =`), the harness skips that step
silently. `gate_eval_postcommit.py` will not error on an empty `smoke`
even when `feature.test_contract.l5_smoke_path` is set; it logs a
SKIPPED note.

## Self-validation

After emit, stack-skill-creator runs these checks:

1. File exists at `.claude/skills/<stack>/sensors.ini`
2. All required sections + keys present (`[lint] fix`, `[lint] check`,
   `[typecheck] command`, `[test] unit`)
3. Every command string parses as a non-empty token list

A failed check aborts skill creation — fix sensors.ini before retry.

## Template

See `templates/sensors.ini.template` for an annotated Python (Ruff +
mypy + pytest) example. New stacks copy it, substitute commands, and
validate.

## Why a separate file (vs putting commands in SKILL.md)

`sensors.ini` is **machine-readable**: hooks parse it directly. Putting
commands in SKILL.md prose would force every gate to re-implement
fragile markdown extraction. Separating "human prose" (SKILL.md +
references/) from "harness contract" (sensors.ini) keeps each stable.
