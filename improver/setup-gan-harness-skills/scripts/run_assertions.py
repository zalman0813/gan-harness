#!/usr/bin/env python3
"""run_assertions.py — deterministic assertion runner for setup-gan-harness-skills evals.

Per skill-creator guidance:
> "For assertions that can be checked programmatically, write and run a script
>  rather than eyeballing it — scripts are faster, more reliable, and can be
>  reused across iterations."

Reads eval_metadata.json, runs each assertion against a target directory,
emits grading.json in the format the eval-viewer expects (text/passed/evidence).

Usage:
    python run_assertions.py \\
        --eval-metadata path/to/eval_metadata.json \\
        --target path/to/with_skill/outputs/ \\
        --out path/to/grading.json

Pure stdlib.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def assert_file_exists(target: Path, paths: list[str]) -> tuple[bool, str]:
    missing = [p for p in paths if not (target / p).exists()]
    if not missing:
        return (True, f"All {len(paths)} paths present: {paths}")
    return (False, f"Missing: {missing}")


def assert_file_absent(target: Path, paths: list[str]) -> tuple[bool, str]:
    present = [p for p in paths if (target / p).exists()]
    if not present:
        return (True, f"All {len(paths)} paths correctly absent")
    return (False, f"Should be absent but present: {present}")


def assert_file_set(
    target: Path, must_present: list[str], must_absent: list[str]
) -> tuple[bool, str]:
    missing = [p for p in must_present if not (target / p).exists()]
    leaked = [p for p in must_absent if (target / p).exists()]
    if not missing and not leaked:
        return (True, f"present={must_present} absent={must_absent} all OK")
    parts = []
    if missing:
        parts.append(f"missing required: {missing}")
    if leaked:
        parts.append(f"should be absent but present: {leaked}")
    return (False, "; ".join(parts))


def assert_regex_match(
    target: Path, paths: list[str], regex: str, either: bool = False
) -> tuple[bool, str]:
    pat = re.compile(regex)
    matched_in: list[str] = []
    for p in paths:
        full = target / p
        if not full.exists():
            continue
        if pat.search(full.read_text(encoding="utf-8")):
            matched_in.append(p)
    if either:
        if matched_in:
            return (True, f"regex matched in: {matched_in}")
        return (False, f"regex {regex!r} did not match any of {paths}")
    # all paths must match
    failed = [p for p in paths if (target / p).exists() and p not in matched_in]
    missing = [p for p in paths if not (target / p).exists()]
    if failed or missing:
        return (False, f"failed_match={failed} missing={missing}")
    return (True, f"regex {regex!r} matched all paths")


def assert_regex_no_match(
    target: Path, paths: list[str], regex: str
) -> tuple[bool, str]:
    pat = re.compile(regex)
    matched_in: list[str] = []
    for p in paths:
        full = target / p
        if full.exists() and pat.search(full.read_text(encoding="utf-8")):
            matched_in.append(p)
    if not matched_in:
        return (True, f"regex {regex!r} correctly absent from all paths")
    return (False, f"regex {regex!r} unexpectedly matched in: {matched_in}")


def assert_any_file_exists(
    target: Path, paths_glob: list[str]
) -> tuple[bool, str]:
    found: list[str] = []
    for pattern in paths_glob:
        for match in target.glob(pattern):
            found.append(str(match.relative_to(target)))
    if found:
        return (True, f"matched: {found}")
    return (False, f"no files matched globs: {paths_glob}")


def assert_yaml_frontmatter_contains(
    target: Path, paths: list[str], yaml_path: str, value_regex: str
) -> tuple[bool, str]:
    """Lightweight: split frontmatter on `---` lines, search the requested key
    for a regex match in its value (the value is read as a string blob — we
    don't full-YAML parse to keep deps zero)."""
    pat = re.compile(value_regex)
    failed: list[str] = []
    for p in paths:
        full = target / p
        if not full.exists():
            failed.append(f"{p}: missing")
            continue
        text = full.read_text(encoding="utf-8")
        # Crude frontmatter extraction
        if not text.startswith("---"):
            failed.append(f"{p}: no frontmatter")
            continue
        try:
            _, fm, _rest = text.split("---", 2)
        except ValueError:
            failed.append(f"{p}: malformed frontmatter")
            continue
        # Find a line matching `^<yaml_path>:` and capture the rest
        key_line_re = re.compile(rf"^{re.escape(yaml_path)}\s*:\s*(.+)$", re.MULTILINE)
        m = key_line_re.search(fm)
        if not m:
            failed.append(f"{p}: yaml_path '{yaml_path}' not in frontmatter")
            continue
        value_blob = m.group(1)
        if not pat.search(value_blob):
            failed.append(f"{p}: value '{value_blob}' does not match {value_regex!r}")
    if not failed:
        return (True, f"frontmatter[{yaml_path}] contains {value_regex!r} in all of {paths}")
    return (False, "; ".join(failed))


KIND_DISPATCH = {
    "file_exists": lambda target, a: assert_file_exists(target, a["paths"]),
    "file_absent": lambda target, a: assert_file_absent(target, a["paths"]),
    "file_set": lambda target, a: assert_file_set(
        target, a.get("must_present", []), a.get("must_absent", [])
    ),
    "regex_match": lambda target, a: assert_regex_match(
        target, a["paths"], a["regex"], either=a.get("either", False)
    ),
    "regex_no_match": lambda target, a: assert_regex_no_match(
        target, a["paths"], a["regex"]
    ),
    "any_file_exists": lambda target, a: assert_any_file_exists(
        target, a["paths_glob"]
    ),
    "yaml_frontmatter_contains": lambda target, a: assert_yaml_frontmatter_contains(
        target, a["paths"], a["yaml_path"], a["value_regex"]
    ),
}


def run(eval_metadata: dict, target: Path) -> dict:
    expectations: list[dict[str, Any]] = []
    for assertion in eval_metadata["assertions"]:
        kind = assertion.get("kind")
        if kind not in KIND_DISPATCH:
            expectations.append(
                {
                    "text": assertion["text"],
                    "passed": False,
                    "evidence": f"unknown assertion kind: {kind}",
                }
            )
            continue
        try:
            passed, evidence = KIND_DISPATCH[kind](target, assertion)
        except Exception as e:  # noqa: BLE001 — surface unexpected failures
            passed = False
            evidence = f"assertion runner threw {type(e).__name__}: {e}"
        expectations.append(
            {
                "text": assertion["text"],
                "passed": passed,
                "evidence": evidence,
                "id": assertion.get("id"),
                "blocking": assertion.get("blocking", True),
            }
        )

    passed_count = sum(1 for e in expectations if e["passed"])
    blocking_failed = [
        e for e in expectations if not e["passed"] and e.get("blocking", True)
    ]
    total = len(expectations)
    return {
        "expectations": expectations,
        "summary": {
            "passed": passed_count,
            "failed": total - passed_count,
            "total": total,
            "pass_rate": passed_count / total if total else 0.0,
            "blocking_failed": len(blocking_failed),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-metadata", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    eval_meta = json.loads(Path(args.eval_metadata).read_text())
    target = Path(args.target)
    if not target.exists():
        print(f"target dir missing: {target}", file=sys.stderr)
        return 2

    grading = run(eval_meta, target)
    Path(args.out).write_text(json.dumps(grading, indent=2))

    s = grading["summary"]
    print(
        f"PASS {s['passed']}/{s['total']} "
        f"(blocking_failed={s['blocking_failed']}, pass_rate={s['pass_rate']:.0%})"
    )
    if s["blocking_failed"] > 0:
        for e in grading["expectations"]:
            if not e["passed"] and e.get("blocking", True):
                print(f"  FAIL [{e.get('id', '?')}] {e['text']}", file=sys.stderr)
                print(f"        evidence: {e['evidence']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
