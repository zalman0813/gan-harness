# Design Review — `user_service.py`

**Module under review:** `improver/.../input/user_service.py`
**Reviewer stance:** general SWE judgement (Ousterhout *A Philosophy of Software Design*, Parnas information hiding, Fowler refactoring catalogue, standard layered-architecture / DDD vocabulary). No project-specific handbook consulted.

---

## TL;DR

`UserService` is a **thin façade** — almost every method is a one-line forward to `UserRepository`. It claims to be a domain service but provides no abstraction over the data layer: it leaks ORM types, raw SQL, driver exceptions, and storage column names through its public interface. Its constructor is a half-built object (temporal coupling), its public surface is a bag-of-getters, and at least one method is a textbook SQL-injection vector. The right move is **delete most of it**: either let callers depend on the repository directly, or rewrite this as a genuinely deep module with a narrow, intention-revealing interface (verbs the *domain* cares about) and hide SQLAlchemy entirely.

---

## Findings (severity-ordered)

### 1. SQL injection in `find_users_by_status_raw` — **critical, security**

```python
self._repo.session.execute(
    f"SELECT * FROM users WHERE status = '{status}'"
).fetchall()
```

`status` is interpolated directly into a raw SQL string. Any caller passing user-controlled input creates a classic SQLi. This is not a "design smell" — it's a live vulnerability. Fix: parameterised query (`text("... :status")` + bindparams) or use the repository's typed query API. Independently, the method also returns raw `sqlalchemy.Row` objects (see Finding 3), so even after fixing the injection, this method should not exist on a domain service.

### 2. Half-built object / temporal coupling — **high**

```python
def __init__(self): ...        # _config_loaded = False, _repo = None
def load_config(self, ...): ... # must be called before anything else
```

Every other method assumes `self._repo` is not `None`, but only `delete_user` checks `self._config_loaded`. Calling `get_user_by_id` on a fresh instance is an `AttributeError`, not a useful error. This is a [Fowler] *Temporal Coupling* / [Ousterhout] *requiring callers to know hidden ordering* smell.

**Fix:** pass `db_url`, `smtp_url`, `jwt_secret` to `__init__` (or accept an already-constructed `UserRepository` — proper dependency injection). Construct-or-fail; never construct a half-broken instance. If config truly must come from a side channel, expose a `UserService.create(config)` classmethod that returns a fully-initialised service and make `__init__` private-by-convention.

### 3. Leaky abstraction — ORM types on the public surface — **high**

- `find_users_by_status_raw` returns SQLAlchemy `Row` objects ("so callers can access any column they want").
- `get_user_by_id` / `get_user_by_email` / `list_all_users` return whatever the repo returns — almost certainly ORM-mapped entities that are bound to a session.
- The docstring of `find_users_by_status_raw` *advertises* the leak as a feature.

This is the [Evans] anti-corruption-layer in reverse: instead of insulating the domain from the persistence model, the "domain service" hands the persistence model out. Callers now depend on SQLAlchemy: they must know column names, session lifecycle, lazy-load behaviour, detachment rules. Swapping the persistence engine is now a cross-cutting refactor instead of a one-file change.

**Fix:** define a plain `User` dataclass (or Pydantic model) at the domain boundary. Every public method returns `User` / `list[User]` / `Optional[User]`. The repository's ORM types stay strictly internal.

### 4. Exception leakage — `sqlalchemy.exc.OperationalError` in the public contract — **high**

```python
Raises:
    sqlalchemy.exc.OperationalError: if the DB is unreachable.
```

Documenting a driver-specific exception type on a domain method makes the driver part of the contract. Callers must `import sqlalchemy.exc`; replacing SQLAlchemy is now a breaking change for everyone who handled this exception. The docstring also lists six unrelated exception types (`ValueError`, `KeyError`, `RuntimeError`, `ConnectionError`, `PermissionError`) — that's a code smell about cohesion: the method is doing too many things.

**Fix:** define module-level domain exceptions (`UserNotFound`, `UserServiceUnavailable`, `InvalidUserId`). Wrap-and-translate `OperationalError` at the repo→service boundary. The public contract should mention only domain exceptions.

### 5. Bag-of-getters / pass-through methods — **high (Ousterhout "shallow module")**

Roughly 8 of the ~14 methods are one-line forwards:

| Method                       | Body                                       |
| ---------------------------- | ------------------------------------------ |
| `get_user_by_id`             | `self._repo.find_by_id(user_id)`           |
| `get_user_by_email`          | `self._repo.find_by_email(email)`          |
| `list_all_users`             | `self._repo.all()`                         |
| `count_users`                | `self._repo.count()`                       |
| `user_exists`                | `self._repo.find_by_id(...) is not None`   |
| `get_user_count_by_status`   | `self._repo.count_by_status(status)`       |
| `lock_account` / `unlock`    | `set_field(user_id, "status", ...)`        |
| `reset_password`             | `set_field(user_id, "password_hash", raw)` |

Per Ousterhout, *interface complexity should be small relative to implementation complexity*. These methods add interface surface with zero hidden complexity — the *cost* of the abstraction exceeds its *benefit*. Delete them and let callers use the repository, **or** consolidate them behind one or two intention-revealing operations. Right now the service is a "fat wrapper over a thin wrapper".

### 6. `update_user(user_id, opts: dict)` — opaque options-bag interface — **medium-high**

```python
def update_user(self, user_id: int, opts: dict):
    for key, value in opts.items():
        self._repo.set_field(user_id, key, value)
```

Problems compound here:

- The function name says nothing; the `opts` keys *are* the interface, but they're undocumented except in a free-text docstring, untyped, and unvalidated.
- No invariants are enforced. A caller can pass `{"password_hash": "literally anything"}`, `{"role": "superadmin"}`, or `{"status": "deleted_but_not_really"}`. Sensitive fields (`password`, `role`, `mfa_enabled`, `recovery_email`) need *different* code paths with *different* authorisation, validation, and side effects (audit log, email confirmation, MFA re-enrol). Funnelling them through one untyped setter is how privilege-escalation bugs get written.
- It's also a thin wrapper around `set_field`, which itself looks like it just writes any column — i.e. the repository is also too generic.

**Fix:** explicit verbs — `change_email(user_id, new_email)`, `change_role(user_id, new_role, actor)`, `enable_mfa(user_id, factor)`. Each method validates its own inputs, enforces its own invariants, and emits its own audit event. The "options bag" is an anti-pattern when the options have different security properties.

### 7. Password handling — **critical, security**

```python
def reset_password(self, user_id, new_password):
    return self._repo.set_field(user_id, "password_hash", new_password)
```

The parameter is `new_password` (cleartext) but it's stored under column `password_hash`. Either the column is being populated with cleartext (catastrophic) or the caller is expected to pre-hash (interface lie). The unused `import bcrypt` at the top is a tell. There's also no audit, no session invalidation, no "old password required" check, no rate limiting.

**Fix:** `reset_password` accepts cleartext, computes the bcrypt hash *inside* the service, calls a typed repo method (`update_password_hash`), invalidates existing sessions/JWTs, and emits an audit event. The hashing scheme is an implementation detail and should never appear in a column-name string at the call site.

### 8. `is_empty_email` — wrapper around stdlib — **low**

`email == ""` is shorter and clearer than `service.is_empty_email(email)`. Delete. If email validation is actually needed, it should be a real validator (`is_valid_email`) returning structured failure info, not a redundant predicate.

### 9. No tests are possible without a real DB — **medium (testability)**

Because the repository is constructed *inside* `load_config` from a URL string, there's no seam to inject a fake. To unit-test `UserService` you either spin up Postgres or monkey-patch `db.UserRepository` at import time. Standard fix: accept a `UserRepository` (or a `UserRepositoryProtocol`) via the constructor. This also makes Finding 2 disappear.

### 10. Missing concerns the docstring hints at but the code ignores — **medium**

The `delete_user` docstring mentions SMTP-down errors and an audit token, but the body does neither — no goodbye email, no audit. Either the docstring is aspirational (delete it) or the implementation is missing (add it). Lying docstrings are worse than missing ones.

---

## Recommended target shape

```python
# domain types (no ORM imports)
@dataclass(frozen=True)
class User:
    id: int
    email: str
    name: str
    role: Role
    status: UserStatus

class UserNotFound(Exception): ...
class UserServiceUnavailable(Exception): ...

class UserRepository(Protocol):
    def find_by_id(self, user_id: int) -> User | None: ...
    def find_by_email(self, email: str) -> User | None: ...
    def update_password_hash(self, user_id: int, bcrypt_hash: bytes) -> None: ...
    def update_status(self, user_id: int, status: UserStatus) -> None: ...
    def delete(self, user_id: int) -> None: ...
    # ...

class UserService:
    def __init__(self, repo: UserRepository, mailer: Mailer, clock: Clock):
        self._repo = repo
        self._mailer = mailer
        self._clock = clock

    # narrow, intention-revealing verbs only
    def reset_password(self, user_id: int, new_password: str) -> None: ...
    def change_email(self, user_id: int, new_email: str, actor: ActorId) -> None: ...
    def lock_account(self, user_id: int, reason: str) -> None: ...
    def unlock_account(self, user_id: int) -> None: ...
    def delete_account(self, user_id: int, actor: ActorId) -> None: ...
```

Notes on the rewrite:

- No `load_config`; construct-or-fail.
- No pass-throughs to the repo — if a caller just needs a lookup, it depends on the repository directly. The service exists only when *behaviour* (validation + side effects + invariants) needs to be enforced.
- Public types are domain types; SQLAlchemy stays behind the `UserRepository` protocol.
- Exceptions are domain-typed; driver errors are translated at the boundary.
- Each mutating method is a verb with a specific contract — no opaque `opts` dict.

---

## Summary of severities

| #  | Finding                                 | Severity |
| -- | --------------------------------------- | -------- |
| 1  | SQL injection in `find_users_by_status_raw` | critical |
| 7  | Cleartext password stored as hash       | critical |
| 2  | Half-built object / temporal coupling   | high     |
| 3  | ORM types on public surface             | high     |
| 4  | Driver exception in public contract     | high     |
| 5  | Pass-through bag-of-getters             | high     |
| 6  | Opaque `opts` dict on `update_user`     | medium-high |
| 9  | Untestable without a real DB            | medium   |
| 10 | Docstring promises behaviour code lacks | medium   |
| 8  | `is_empty_email` wrapper                | low      |
