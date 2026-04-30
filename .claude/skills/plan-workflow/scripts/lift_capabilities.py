#!/usr/bin/env python3
"""Semantic well-formedness for feature-list.json.

Checks that go beyond JSON Schema (which is plan_validator.py's job):
  - no duplicate feature ids batch-wide
  - no duplicate AC ids within a feature
  - no duplicate open_question ids within a feature
  - decision_refs[] resolve to existing files on disk (HARD)
  - eval_anchors and must_not lists have no duplicates (already in schema, but
    re-validated here for early diagnosis)

Note: open_question.resolution being non-empty is enforced by the schema
(required + minLength 1). No deferred kind exists. lift_capabilities.py does
not need to re-check; if planner left a question unresolved, plan_validator
catches it earlier.

Pure stdlib.

Usage: lift_capabilities.py <path-to-feature-list.json>

Exit codes:
  0  PASS
  1  FAIL — semantic violations
  2  parse error or file not found
"""
from __future__ import annotations
import sys
import json
import argparse
from pathlib import Path


def find_repo_root(fl_path: Path) -> Path:
    """specs/_batch/feature-list.json → repo root.

    If the path doesn't fit that layout, walk up until we find a .git or
    .claude directory; otherwise return the file's grandparent.
    """
    p = fl_path.resolve()
    for ancestor in [p.parent] + list(p.parents):
        if (ancestor / ".claude").is_dir() or (ancestor / ".git").exists():
            return ancestor
    return p.parents[2] if len(p.parents) >= 2 else p.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("feature_list", help="path to specs/_batch/feature-list.json")
    args = ap.parse_args()

    fl_path = Path(args.feature_list)
    if not fl_path.is_file():
        print(json.dumps({"status": "ERROR", "error": f"file not found: {fl_path}"}))
        sys.exit(2)

    try:
        data = json.loads(fl_path.read_text())
    except Exception as e:
        print(json.dumps({"status": "ERROR", "error": f"json parse: {e}"}))
        sys.exit(2)

    repo_root = find_repo_root(fl_path)
    violations: list[dict] = []

    feature_ids: list[str] = []
    for f in data.get("features", []):
        fid = f.get("id", "?")
        feature_ids.append(fid)

        # duplicate AC ids
        ac_ids = [ac.get("id") for ac in f.get("spec", {}).get("ac", [])]
        if len(ac_ids) != len(set(ac_ids)):
            dupes = sorted({x for x in ac_ids if ac_ids.count(x) > 1})
            violations.append({"feature": fid, "kind": "duplicate_ac_ids", "dupes": dupes})

        # duplicate Q ids
        q_ids = [q.get("id") for q in f.get("spec", {}).get("open_questions", [])]
        if len(q_ids) != len(set(q_ids)):
            dupes = sorted({x for x in q_ids if q_ids.count(x) > 1})
            violations.append({"feature": fid, "kind": "duplicate_question_ids", "dupes": dupes})

        # decision_refs resolve
        for ref in f.get("decision_refs", []):
            ref_path = repo_root / ref
            if not ref_path.is_file():
                violations.append({
                    "feature": fid,
                    "kind": "decision_ref_missing",
                    "ref": ref,
                    "resolved_to": str(ref_path),
                })

        # eval_anchors + must_not unique within each AC
        for ac in f.get("spec", {}).get("ac", []):
            for fld in ("eval_anchors", "must_not"):
                arr = ac.get(fld) or []
                if len(arr) != len(set(arr)):
                    dupes = sorted({x for x in arr if arr.count(x) > 1})
                    violations.append({
                        "feature": fid,
                        "ac": ac.get("id", "?"),
                        "kind": f"duplicate_{fld}",
                        "dupes": dupes,
                    })

    if len(feature_ids) != len(set(feature_ids)):
        dupes = sorted({x for x in feature_ids if feature_ids.count(x) > 1})
        violations.append({"kind": "duplicate_feature_ids", "dupes": dupes})

    report = {
        "status": "PASS" if not violations else "FAIL",
        "feature_count": len(feature_ids),
        "violations": violations,
    }
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
