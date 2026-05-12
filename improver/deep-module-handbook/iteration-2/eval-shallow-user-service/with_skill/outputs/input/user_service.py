"""user_service.py — a deliberately shallow / leaky / temporally-coupled module.

This file is the INPUT for a deep-module-handbook evaluator eval. The agent
under test is asked to produce a design_review for this file using the
handbook's vocabulary. Multiple deep-module anti-patterns are intentionally
present (each one tagged with a comment for the eval's own auditability,
NOT for the agent — the agent should discover them on its own).
"""
from __future__ import annotations

import sqlalchemy.exc
import bcrypt  # noqa: F401  (kept to dramatise leaky dep on hashing scheme)


class UserService:
    """User account service."""

    def __init__(self):
        # ANTIPATTERN-temporal-coupling: load_config() MUST be called
        # before any other method, but the docstring above is silent
        # about this required ordering.
        self._config_loaded = False
        self._repo = None

    def load_config(self, db_url: str, smtp_url: str, jwt_secret: str):
        """Load config. Must be called first."""
        self._config_loaded = True
        from db import UserRepository
        self._repo = UserRepository(db_url)

    # ANTIPATTERN-pass-through: this is a 1-line forward to repo. Removing
    # it would only require renaming get_user_by_id → repo.find_by_id at
    # every callsite (no other change needed).
    def get_user_by_id(self, user_id: int):
        return self._repo.find_by_id(user_id)

    # ANTIPATTERN-pass-through (variant): same shape, different verb.
    def get_user_by_email(self, email: str):
        return self._repo.find_by_email(email)

    # ANTIPATTERN-pass-through (variant): same shape again.
    def list_all_users(self):
        return self._repo.all()

    # ANTIPATTERN-wrapper-around-stdlib: trivial wrapper with no added
    # semantics. Callers could just write `not email or email == ""`.
    def is_empty_email(self, email: str) -> bool:
        return email == ""

    # ANTIPATTERN-leaky-abstraction: returns the raw SQLAlchemy Row /
    # ORM object across the public surface. Callers must know about
    # SQLAlchemy column names and connection state to use the result.
    def find_users_by_status_raw(self, status: str):
        """Returns raw sqlalchemy.Row objects so callers can access
        any column they want."""
        return self._repo.session.execute(
            f"SELECT * FROM users WHERE status = '{status}'"
        ).fetchall()

    # ANTIPATTERN-exception-leak: re-raises lower-layer exception types
    # (sqlalchemy.exc.OperationalError) as part of the public contract
    # of a domain method, forcing callers to depend on the DB driver.
    def delete_user(self, user_id: int):
        """Delete a user.

        Raises:
            sqlalchemy.exc.OperationalError: if the DB is unreachable.
            ValueError: if user_id is negative.
            KeyError: if user_id not found.
            RuntimeError: if config not loaded.
            ConnectionError: if SMTP for the goodbye email is down.
            PermissionError: if the calling thread has no audit token.
        """
        if not self._config_loaded:
            raise RuntimeError("call load_config() first")
        if user_id < 0:
            raise ValueError("user_id must be non-negative")
        try:
            self._repo.delete(user_id)
        except sqlalchemy.exc.OperationalError:
            raise  # bare re-raise; caller now must know about SQLAlchemy

    # ANTIPATTERN-config-leak: a single public method accepting an options
    # bag where the options ARE the interface — the function name conveys
    # almost nothing.
    def update_user(self, user_id: int, opts: dict):
        """Apply changes.

        opts may contain: email, password, name, role, status, locale,
        timezone, marketing_opt_in, mfa_enabled, recovery_email, phone,
        date_of_birth.
        """
        for key, value in opts.items():
            self._repo.set_field(user_id, key, value)

    # ANTIPATTERN-pass-through (4th): forward to repo.
    def count_users(self):
        return self._repo.count()

    # ANTIPATTERN-pass-through (5th): forward to repo with a rename.
    def user_exists(self, user_id: int) -> bool:
        return self._repo.find_by_id(user_id) is not None

    # ANTIPATTERN-pass-through (6th): forward to repo.
    def get_user_count_by_status(self, status: str) -> int:
        return self._repo.count_by_status(status)

    # ANTIPATTERN-entry-point-bloat: by this point the class has 12+
    # public methods. C4 (≤ 1-3 entry points) fails decisively. This is
    # a bag-of-getters, not a deep module.

    def reset_password(self, user_id: int, new_password: str):
        return self._repo.set_field(
            user_id, "password_hash", new_password  # ANTIPATTERN: caller passes raw
        )

    def lock_account(self, user_id: int):
        return self._repo.set_field(user_id, "status", "locked")

    def unlock_account(self, user_id: int):
        return self._repo.set_field(user_id, "status", "active")
