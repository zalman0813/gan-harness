#!/usr/bin/env python3
"""/finalize pre-flight validation.

Validates that the active batch is ready for /finalize and prints
machine-readable env-style output the SKILL can source. Single mode —
no --print-slug variant; the slug is `feature-list.json.batch_slug`.

Checks:
  1. specs/_batch/feature-list.json exists + parses as JSON
  2. batch_slug + base_commit present (schema requirement; mirror it)
  3. base_commit resolves in git history
  4. specs/_batch/prd.md exists (Domain terms source for archive path)
  5. Every feature.status is terminal: passed | deferred | blocked-by-ancestor

Decides the branch:
  BRANCH=archive   when every feature.status == "passed"
  BRANCH=retro     when any feature.status in {deferred, blocked-by-ancestor}

Quarantine check:
  Any feature.quarantined_tests[] entry whose `expires_after_batch`
  equals the current batch slug is "expired and unresolved". On
  BRANCH=archive these REFUSE the run (resolve or extend expiry first).
  On BRANCH=retro they are reported but do NOT block — retro walk
  surfaces them to the user.

Output (stdout, key=value lines on success):
  SLUG=<batch_slug>
  BASE_COMMIT=<full sha>
  BRANCH=archive|retro
  TOTAL=<n>
  PASSED=<csv>
  DEFERRED=<csv>
  BLOCKED=<csv>
  EXPIRED_QUARANTINES=<csv of feature_id:test_id pairs>

Exit:
  0 OK
  1 validation failed (diagnostic on stderr)
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

FEATURE_LIST = Path("specs/_batch/feature-list.json")
PRD = Path("specs/_batch/prd.md")
TERMINAL = {"passed", "deferred", "blocked-by-ancestor"}


def fail(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 1


def main() -> int:
    if not FEATURE_LIST.exists():
        return fail(
            f"{FEATURE_LIST} not found. /plan must run first; if the batch "
            "was already archived, /finalize is a no-op."
        )

    try:
        data = json.loads(FEATURE_LIST.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return fail(f"{FEATURE_LIST} is not valid JSON: {exc}")

    slug = data.get("batch_slug")
    base_commit = data.get("base_commit")
    features = data.get("features") or []

    if not slug:
        return fail(f"{FEATURE_LIST}.batch_slug is missing or empty.")
    if not base_commit:
        return fail(f"{FEATURE_LIST}.base_commit is missing or empty.")
    if not features:
        return fail(f"{FEATURE_LIST}.features is empty — nothing to finalize.")

    try:
        result = subprocess.run(
            ["git", "cat-file", "-t", base_commit],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return fail(
                f"base_commit {base_commit} not found in git history. "
                "Branch may have been rewritten; investigate before archiving."
            )
    except (subprocess.SubprocessError, OSError) as exc:
        return fail(f"git verification of base_commit failed: {exc}")

    if not PRD.exists():
        return fail(
            f"{PRD} not found. Archive path needs the PRD for Domain terms "
            "merge. Did /prd run before /plan?"
        )

    non_terminal = [
        f.get("id", "?") for f in features
        if f.get("status") not in TERMINAL
    ]
    if non_terminal:
        return fail(
            f"Features {non_terminal} are not in a terminal status. "
            f"Run /execution-loop until every feature.status is one of "
            f"{sorted(TERMINAL)}."
        )

    passed = [f["id"] for f in features if f["status"] == "passed"]
    deferred = [f["id"] for f in features if f["status"] == "deferred"]
    blocked = [f["id"] for f in features if f["status"] == "blocked-by-ancestor"]

    branch = "archive" if not deferred and not blocked else "retro"

    # Quarantine: any feature.quarantined_tests[] whose
    # expires_after_batch == current batch slug is overdue. Archive
    # path refuses; retro path surfaces but does not block.
    expired = []
    for feat in features:
        for q in (feat.get("quarantined_tests") or []):
            if q.get("expires_after_batch") == slug:
                expired.append(f"{feat['id']}:{q.get('test_id', '?')}")

    if branch == "archive" and expired:
        return fail(
            "Quarantine entries expire in this batch but are not resolved: "
            f"{expired}. Either remove the entry (the underlying test is "
            "fixed) or extend its expires_after_batch to a future slug. "
            "/finalize archive refuses to proceed until every entry "
            "expiring in this batch is gone."
        )

    print(f"SLUG={slug}")
    print(f"BASE_COMMIT={base_commit}")
    print(f"BRANCH={branch}")
    print(f"TOTAL={len(features)}")
    print(f"PASSED={','.join(passed)}")
    print(f"DEFERRED={','.join(deferred)}")
    print(f"BLOCKED={','.join(blocked)}")
    print(f"EXPIRED_QUARANTINES={','.join(expired)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
