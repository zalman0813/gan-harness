# Design Review — `user_service.py`

## Summary

- **Module under review**: `improver/deep-module-handbook/iteration-1/eval-shallow-user-service/with_skill/outputs/input/user_service.py`
- **Declared purpose** (per class docstring): "User account service" — a single `UserService` class exposing 13 public methods over a `UserRepository`.
- **Applicability classification** (foundation §3): business-logic / workflow orchestration → deep-module principles fully apply; this is not a DTO, framework-shaped object, hot path, or one-shot script, so the §3.5 PASS checklist and §5 red flags are in scope.
- **Overall verdict**: **FAIL.** The module is the textbook *shallow* shape — a thin bag-of-getters whose public surface is comparable in complexity to its implementation, with multiple red flags firing simultaneously (`fake-deep-pass-through`, `temporal-coupling`, `config-leak`, `exception-leak`, `wrapper-around-stdlib`, plus a leaky abstraction returning raw `sqlalchemy.Row`s). The PASS checklist fails on C1, C2, C3, C4, C6, C7 with C8 in the lower band but not redemptive on its own.

## `design_review` (narrative)

This module fails the depth principle on first read. The qualitative depth check from foundation §1 — "could a maintainer reconstruct the implementation correctly from the public signatures alone?" — is trivially answered **yes**: `get_user_by_id`, `get_user_by_email`, `list_all_users`, `count_users`, `user_exists`, `get_user_count_by_status`, `lock_account`, `unlock_account`, and `reset_password` are 1–2 line forwards to `self._repo`, and a maintainer needs no information beyond the signatures to write equivalent bodies. Per Ousterhout (APOSD ch.4) this is the canonical shallow shape. **C1 (name the hidden decision)** fails because no single design decision likely to change is owned here — the class is a transport for repository methods, not an information-hiding boundary in the Parnas (1972) sense; "User account service" is ceremony, not a falsifiable design claim, and would be falsified within seconds. **C2 (3-question self-test)** fails on (a) "what unique value does this module provide?" — the honest answer is "renames repository methods," which is not value. **C3 (deletion test, foundation §5.5)** fails for at least nine of the thirteen methods: deleting `get_user_by_id` would only require callers to write `repo.find_by_id(id)` at one extra character cost; complexity does not reappear in ≥ 2 callers. **C4 (1–3 entry-point budget, Pocock INTERFACE-DESIGN.md)** fails decisively — the class exposes 13 public methods, far above the Pocock budget, and unlike Unix file I/O (which earns its 5) these methods do not represent independent primitives over hidden state. **C6 (broad interface — signatures + invariants + ordering + error modes)** fails because the interface silently encodes a temporal-coupling rule (`load_config()` must precede every other call) that is not declared in signatures, and `delete_user`'s docstring lists six heterogeneous exception types drawn from three abstraction layers — callers learning to use the module must memorise both the ordering rule and the exception zoo. **C7 (interface = test surface)** would fail in practice: tests written against `find_users_by_status_raw` would couple to SQLAlchemy `Row` semantics and would not survive a swap of the repository's session backend.

Beyond the PASS-checklist failures, multiple §5 red flags fire concurrently, which is itself a depth signal:

1. `🚩 fake-deep-pass-through` (Ousterhout APOSD ch.5) — fires on ≥ 6 methods (`get_user_by_id`, `get_user_by_email`, `list_all_users`, `count_users`, `user_exists`, `get_user_count_by_status`, plus `lock_account` / `unlock_account` which forward to `set_field`). None of these qualify as ACL (foundation §4 row 4): no foreign-vocabulary translation happens; removing them concentrates no complexity in callers.
2. `🚩 temporal-coupling` (Seemann, ploeh.dk) — `load_config()` MUST be called before any other method; `delete_user` is the only method that even checks `self._config_loaded`, so callers of the other twelve methods will get `AttributeError` on `None._repo` rather than a domain error. The recommended fix is straightforward (constructor-takes-config / born-valid), and the cost of NOT fixing it is that the ordering becomes part of the interface every caller must memorise (C6).
3. `🚩 config-leak` (Ousterhout APOSD ch.5) — `update_user(user_id, opts: dict)` is the canonical case: a dozen optional fields hide behind an untyped `dict`, the function name conveys nothing, and the `set_field` loop blindly forwards every key to the repository (no validation, no per-field invariants).
4. `🚩 exception-leak` (Bloch *Effective Java* Item 73; Ousterhout APOSD ch.10) — `delete_user` documents six exception types from at least three layers (SQLAlchemy operational, Python builtin, network, OS). `sqlalchemy.exc.OperationalError` is bare-re-raised, forcing callers to import the SQLAlchemy exception namespace. Bloch's exception translation pattern is the prescribed cure.
5. `🚩 wrapper-around-stdlib` (Ousterhout APOSD ch.5) — `is_empty_email` is `email == ""` with no added validation, normalisation, or i18n consideration. The wrapper does not earn its existence.
6. **Leaky abstraction** (Spolsky 2002; foundation §1) — `find_users_by_status_raw` returns raw `sqlalchemy.Row` objects across the public surface, in a method whose docstring openly invites callers to "access any column they want." This is leakage by design; foreign vocabulary (SQLAlchemy column names, session lifecycle) is welded into the domain caller. The same method additionally builds SQL by f-string interpolation of `status`, which is an SQL-injection class issue — orthogonal to depth but worth surfacing under foundation evaluator-slice §4 (security): user input flows into a SQL literal with no parameter binding.
7. **Security — secret/secret-adjacent leakage** — `reset_password(user_id, new_password)` forwards `new_password` directly to `set_field(..., "password_hash", new_password)`. The argument named "new_password" is stored as `password_hash` without hashing; `bcrypt` is imported but never invoked. This is both a contract lie (parameter name vs storage column) and a hard FAIL under evaluator-slice §4 "Sanitization at the wrong layer" — the hashing responsibility is silently pushed onto whichever caller knows to pre-hash. The presence of `import bcrypt` makes the omission auditable.

The module's class-size sanity proxy (C8) sits at ~120 LOC, below the Ousterhout CS190 band of 200–2000. C8 is "look here first," not a verdict, and here it correlates with the qualitative finding: the module is genuinely too thin because the boundary is in the wrong place. The remedy is not to grow this class but to delete most of it and let callers call `UserRepository` directly, OR to redraw the boundary around an information-hiding decision the planner can name in one sentence (e.g., "this module hides how a password is stored and rotated"), at which point the surface area collapses to 2–3 entry points (`authenticate`, `reset_password`, `change_email`) over a private repository.

## `drift_from_spec[]`-style findings

- C1 fails — no `hides_decision` sentence is articulable; class docstring "User account service" is ceremony, falsifiable in under one minute by reading the body.
- C2 fails — the 3-question self-test (Ousterhout CS190) cannot be answered for unique value or for "least knowledge exposed at the interface."
- C3 fails — deletion test (foundation §5.5) does not fire for ≥ 9 of 13 public methods; complexity would not reappear in ≥ 2 callers because the methods are renames of `UserRepository` calls.
- C4 fails — 13 public methods, far above the Pocock 1–3 entry-point budget (INTERFACE-DESIGN.md); not a Unix-file-API style multi-primitive justification.
- C6 fails — temporal-coupling rule (`load_config()` first) and exception zoo on `delete_user` are part of the interface but undeclared in signatures.
- C7 would fail — `find_users_by_status_raw` returns ORM rows, so interface tests would bind to SQLAlchemy internals and not survive a repository refactor.
- C8 is below the 200–2000 LOC band; correlates with the qualitative depth failure but is not by itself the verdict.
- 🚩 `fake-deep-pass-through` fires on `get_user_by_id`, `get_user_by_email`, `list_all_users`, `count_users`, `user_exists`, `get_user_count_by_status`, `lock_account`, `unlock_account`.
- 🚩 `temporal-coupling` fires on the `load_config()` → every-other-method ordering rule.
- 🚩 `config-leak` fires on `update_user(user_id, opts: dict)`.
- 🚩 `exception-leak` fires on `delete_user`'s 6-type exception list and bare re-raise of `sqlalchemy.exc.OperationalError`.
- 🚩 `wrapper-around-stdlib` fires on `is_empty_email`.
- Leaky abstraction (Spolsky 2002): `find_users_by_status_raw` returns raw `sqlalchemy.Row`; callers must know SQLAlchemy column / session semantics.
- ACL bypassed (Evans DDD; foundation §1): `sqlalchemy.exc.OperationalError` crosses the module boundary into the caller's namespace.
- Security — sanitization at the wrong layer (evaluator-slice §4): `reset_password` stores the raw argument as `password_hash`; `bcrypt` is imported but never invoked.
- Security — SQL injection risk (orthogonal but auditable): `find_users_by_status_raw` interpolates `status` into a SQL literal with f-string.

## `module_design_verification` block

```json
{
  "module_design_verification": [
    {
      "module_name": "user_service.py::UserService",
      "hides_decision_falsifiable_within_one_minute": true,
      "applicability_honest": false,
      "boundary_type_honest": false,
      "design_review": "Shallow module per Ousterhout APOSD ch.4: public surface (13 methods) is comparable in complexity to the implementation (mostly 1-line forwards to UserRepository). C1 fails — no hides_decision sentence is articulable beyond ceremony, falsifiable in under one minute. C2 fails on 'unique value' and 'least knowledge'. C3 fails — deletion test (foundation §5.5) does not fire for ≥ 9 of 13 methods. C4 fails decisively at 13 public methods vs Pocock's 1-3 budget. C6 fails because the broad interface (signatures + invariants + ordering + error modes) encodes a temporal-coupling rule (load_config first) and a 6-type exception list on delete_user, neither declared in signatures. Red flags fired: fake-deep-pass-through (≥ 6 instances), temporal-coupling (load_config ordering), config-leak (update_user opts dict), exception-leak (delete_user re-raises sqlalchemy.exc.OperationalError bare), wrapper-around-stdlib (is_empty_email). Leaky abstraction: find_users_by_status_raw returns raw sqlalchemy.Row across the public surface and uses f-string SQL interpolation (security finding orthogonal to depth). Security: reset_password stores raw new_password into password_hash though bcrypt is imported — sanitisation at the wrong layer per evaluator-slice §4. Boundary type cannot be 'internal' as written: SQLAlchemy vocabulary and exceptions cross the module boundary, so an ACL is needed but absent. Recommendation: redraw the boundary around a nameable hidden decision (e.g., 'how passwords are stored / rotated'), collapse the entry-point surface to 2-3, wrap or translate SQLAlchemy exceptions at the boundary, and either delete the pass-throughs or merge UserService into UserRepository.",
      "drift_from_spec": [
        "C1: no falsifiable hides_decision; class docstring is ceremony",
        "C2: 3-question self-test fails on unique-value and least-knowledge axes",
        "C3: deletion test fails for ≥ 9 of 13 public methods (pass-through smell)",
        "C4: 13 public methods vs Pocock 1-3 entry-point budget",
        "C6: temporal-coupling rule and exception zoo undeclared in signatures",
        "C7 (projected): interface tests would couple to SQLAlchemy Row internals",
        "red_flag fake-deep-pass-through fires across ≥ 6 methods",
        "red_flag temporal-coupling fires on load_config ordering",
        "red_flag config-leak fires on update_user(opts: dict)",
        "red_flag exception-leak fires on delete_user (6 exception types; bare re-raise of sqlalchemy.exc.OperationalError)",
        "red_flag wrapper-around-stdlib fires on is_empty_email",
        "leaky-abstraction: find_users_by_status_raw returns raw sqlalchemy.Row",
        "ACL bypassed: sqlalchemy.exc.OperationalError leaks across module boundary",
        "security: reset_password stores raw new_password as password_hash (bcrypt imported but unused)",
        "security: find_users_by_status_raw f-string SQL interpolation (injection risk)"
      ]
    }
  ]
}
```
