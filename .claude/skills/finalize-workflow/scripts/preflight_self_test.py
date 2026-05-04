#!/usr/bin/env python3
"""
preflight_self_test.py — fixture-based self-test for preflight.py.

Two layers:

  1. JSON-Schema validation of feature.quarantined_tests entries
     against feature-list.schema.json. Asserts well-formed entries
     pass and malformed entries (short reason, bad ac_id, bad slug)
     are rejected.

  2. End-to-end preflight invocation under tmp git repos that match
     the four meaningful scenarios:

     - archive_clean        : passed feature, no quarantine        → BRANCH=archive
     - archive_blocked      : passed feature, quarantine expires
                              this batch                            → exit 1 (refuse)
     - archive_future_quar  : passed feature, quarantine expires
                              a FUTURE batch                        → BRANCH=archive
     - retro_with_quar      : deferred feature, quarantine expires
                              this batch                            → BRANCH=retro
                                                                       (reported, not blocked)

Run:  python3 preflight_self_test.py
Exit 0 = ok; non-zero = failed.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PREFLIGHT = HERE / "preflight.py"
REPO_ROOT = HERE.parents[3]  # .claude/skills/finalize-workflow/scripts/ → repo root
SCHEMA = REPO_ROOT / ".claude" / "schemas" / "feature-list.schema.json"


# --- Schema validation tests ---


def run_schema_tests() -> list[str]:
    failures: list[str] = []
    try:
        import jsonschema
    except ImportError:
        return ["jsonschema not installed; skipping schema tests"]

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    base_feat = {
        "id": "F01", "name": "selftest", "status": "passed", "priority": "P1",
        "depends_on": [], "module_path": "src",
        "spec": {
            "user_story": "As a user I want to test so that quarantine works.",
            "ac": [{"id": "AC-01", "title": "happy path", "kind": "positive",
                    "priority": "P1", "given": "input here", "when": "submit it",
                    "then": "see Saved", "eval_anchors": ["Saved"], "must_not": []}]
        },
        "test_contract": {"l1_command": "echo lint",
                          "l2_path": "tests", "l5_smoke_path": None}
    }
    base = {"batch_slug": "test-slug", "base_commit": "abc1234",
            "features": [base_feat]}

    cases = [
        ("valid quarantine entry", [{
            "test_id": "test_AC_01_save",
            "ac_id": "AC-01",
            "quarantine_reason": "race condition between fixture and DB cleanup",
            "expires_after_batch": "next-batch",
        }], True),
        ("reason too short", [{
            "test_id": "t",
            "ac_id": "AC-01",
            "quarantine_reason": "flaky",  # 5 chars, <10
            "expires_after_batch": "next",
        }], False),
        ("bad ac_id format", [{
            "test_id": "t",
            "ac_id": "AC1",  # missing dash
            "quarantine_reason": "race condition; investigate",
            "expires_after_batch": "next",
        }], False),
        ("bad expires_after_batch (uppercase)", [{
            "test_id": "t",
            "ac_id": "AC-01",
            "quarantine_reason": "race condition; investigate",
            "expires_after_batch": "Next-Batch",  # uppercase rejected
        }], False),
        ("missing field", [{
            "test_id": "t",
            "ac_id": "AC-01",
            "quarantine_reason": "race condition; investigate",
            # missing expires_after_batch
        }], False),
    ]

    for name, qts, should_pass in cases:
        f = json.loads(json.dumps(base))
        f["features"][0]["quarantined_tests"] = qts
        try:
            jsonschema.validate(f, schema)
            ok = should_pass
            if not ok:
                failures.append(f"schema/{name}: expected REJECT, got PASS")
        except jsonschema.ValidationError as e:
            ok = not should_pass
            if not ok:
                failures.append(f"schema/{name}: expected PASS, got REJECT ({e.message[:50]})")
    return failures


# --- preflight end-to-end tests ---


PRD_STUB = "# PRD\n\n## R1 — stub for preflight self-test.\n"


def make_feature_list(slug: str, status: str, quarantine: list[dict]) -> dict:
    return {
        "batch_slug": slug,
        "base_commit": "PLACEHOLDER",
        "features": [{
            "id": "F01", "name": "selftest", "status": status, "priority": "P1",
            "depends_on": [], "module_path": "src",
            "spec": {
                "user_story": "As a user I want quarantine so that finalize is honest.",
                "ac": [{"id": "AC-01", "title": "happy path", "kind": "positive",
                        "priority": "P1", "given": "input here",
                        "when": "submit it", "then": "see Saved",
                        "eval_anchors": ["Saved"], "must_not": []}]
            },
            "test_contract": {"l1_command": "echo lint",
                              "l2_path": "tests", "l5_smoke_path": None},
            "quarantined_tests": quarantine,
        }]
    }


def run_preflight(project_dir: Path) -> tuple[int, dict, str, str]:
    """Run preflight in project_dir. Returns (exit_code, parsed_env,
    stdout, stderr). parsed_env maps KEY → value when stdout is in
    KEY=VAL format; otherwise empty dict."""
    res = subprocess.run(
        [sys.executable, str(PREFLIGHT)],
        cwd=str(project_dir), capture_output=True, text=True, check=False,
    )
    env: dict[str, str] = {}
    if res.returncode == 0:
        for line in res.stdout.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env[k] = v
    return res.returncode, env, res.stdout, res.stderr


def setup_repo(tmp: Path, fl: dict) -> Path:
    """Create a tmp git repo with feature-list.json + prd.md, commit
    them, then patch base_commit to the actual sha. Returns project
    dir."""
    (tmp / "specs" / "_batch").mkdir(parents=True)
    (tmp / "specs" / "_batch" / "feature-list.json").write_text(
        json.dumps(fl), encoding="utf-8"
    )
    (tmp / "specs" / "_batch" / "prd.md").write_text(PRD_STUB, encoding="utf-8")

    # git init + commit so base_commit resolves
    def git(*args):
        subprocess.run(["git", "-C", str(tmp), *args], check=True,
                       capture_output=True)
    git("init", "-q")
    git("config", "user.email", "test@example.com")
    git("config", "user.name", "Test")
    git("add", ".")
    git("commit", "-q", "-m", "initial")

    sha = subprocess.run(
        ["git", "-C", str(tmp), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True
    ).stdout.strip()

    # rewrite base_commit to actual sha
    fl["base_commit"] = sha
    (tmp / "specs" / "_batch" / "feature-list.json").write_text(
        json.dumps(fl), encoding="utf-8"
    )
    return tmp


def run_preflight_tests() -> list[str]:
    failures: list[str] = []

    # archive_clean: passed + no quarantine → archive
    with tempfile.TemporaryDirectory() as td:
        tmp = setup_repo(Path(td), make_feature_list("clean", "passed", []))
        code, env, out, err = run_preflight(tmp)
        if code != 0 or env.get("BRANCH") != "archive":
            failures.append(f"archive_clean: expected BRANCH=archive exit 0, "
                            f"got code={code} branch={env.get('BRANCH')} stderr={err[:200]}")
        if env.get("EXPIRED_QUARANTINES"):
            failures.append(f"archive_clean: EXPIRED_QUARANTINES should be empty, got '{env.get('EXPIRED_QUARANTINES')}'")

    # archive_blocked: passed + quarantine expires this batch → refuse
    with tempfile.TemporaryDirectory() as td:
        tmp = setup_repo(Path(td), make_feature_list(
            "blocked-batch", "passed",
            [{"test_id": "test_AC_01", "ac_id": "AC-01",
              "quarantine_reason": "race condition; investigate",
              "expires_after_batch": "blocked-batch"}]
        ))
        code, env, out, err = run_preflight(tmp)
        if code != 1:
            failures.append(f"archive_blocked: expected exit 1 (refuse), got "
                            f"code={code} out={out[:200]} stderr={err[:200]}")
        if "Quarantine entries expire" not in err:
            failures.append(f"archive_blocked: expected 'Quarantine entries expire' "
                            f"in stderr, got {err[:200]!r}")

    # archive_future_quar: quarantine expires a future batch → archive
    with tempfile.TemporaryDirectory() as td:
        tmp = setup_repo(Path(td), make_feature_list(
            "current-batch", "passed",
            [{"test_id": "test_AC_01", "ac_id": "AC-01",
              "quarantine_reason": "race condition; investigate later",
              "expires_after_batch": "future-batch"}]
        ))
        code, env, out, err = run_preflight(tmp)
        if code != 0 or env.get("BRANCH") != "archive":
            failures.append(f"archive_future_quar: expected archive exit 0, "
                            f"got code={code} branch={env.get('BRANCH')}")
        if env.get("EXPIRED_QUARANTINES"):
            failures.append(f"archive_future_quar: EXPIRED_QUARANTINES should be empty")

    # retro_with_quar: deferred + quarantine expires this batch → retro (no refuse)
    with tempfile.TemporaryDirectory() as td:
        tmp = setup_repo(Path(td), make_feature_list(
            "retro-batch", "deferred",
            [{"test_id": "test_AC_01", "ac_id": "AC-01",
              "quarantine_reason": "race condition; investigate",
              "expires_after_batch": "retro-batch"}]
        ))
        code, env, out, err = run_preflight(tmp)
        if code != 0 or env.get("BRANCH") != "retro":
            failures.append(f"retro_with_quar: expected retro exit 0, "
                            f"got code={code} branch={env.get('BRANCH')} stderr={err[:200]}")
        expired = env.get("EXPIRED_QUARANTINES", "")
        if "F01:test_AC_01" not in expired:
            failures.append(f"retro_with_quar: expected F01:test_AC_01 in "
                            f"EXPIRED_QUARANTINES, got '{expired}'")

    return failures


def main() -> int:
    failures = run_schema_tests() + run_preflight_tests()
    if failures:
        print("preflight_self_test: FAILED", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("preflight_self_test: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
