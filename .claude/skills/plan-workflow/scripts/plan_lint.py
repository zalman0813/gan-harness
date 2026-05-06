#!/usr/bin/env python3
"""Design-discipline lint for feature-list.json.

Enforces only rules that are (a) mechanically unambiguous AND
(b) either consumer-blocking or design-discipline:

  L10a — phase-named features rejected (vertical-slice rule)
  L10b — UI-touching features must set test_contract.l5_smoke_path
         (consumer-blocking: evaluator cannot run the smoke stage without it)

Out of scope here:
  * Structural shape  → plan_validator.py (JSON Schema + DAG)
  * Semantic checks   → lift_capabilities.py (refs resolve, no dupes,
                        open_question resolution required)
  * Deep-module depth → doctrine in planner-handbook/references/deep-module.md;
                        the planner applies it during design
  * Docstring promise → generator + active stack skill responsibility
  * Forbidden fields  → JSON Schema's `additionalProperties: false` at
                        validator level

Pure stdlib. PASS/FAIL only.

Usage: plan_lint.py <path-to-feature-list.json>

Exit:
  0  PASS
  1  FAIL
  2  file not found / parse error
"""
from __future__ import annotations
import sys
import re
import json
import argparse
from pathlib import Path


PHASE_NAME_PATTERNS = [
    re.compile(r"^phase-\d+", re.IGNORECASE),
    re.compile(r"-only$", re.IGNORECASE),
    re.compile(r"^migration(-only)?$", re.IGNORECASE),
    re.compile(r"^db-setup$", re.IGNORECASE),
    re.compile(r"^api-skeleton$", re.IGNORECASE),
    re.compile(r"^ui-only$", re.IGNORECASE),
    re.compile(r"^backend-only$", re.IGNORECASE),
    re.compile(r"^frontend-only$", re.IGNORECASE),
]

UI_PATH_PATTERNS = [
    re.compile(r"apps?/[^/]+/(lib|src)/(features|widgets|pages|screens|views)", re.IGNORECASE),
    re.compile(r"src/(features|app|pages|components|screens)/", re.IGNORECASE),
    re.compile(r"^(client|frontend|webui)/", re.IGNORECASE),
    re.compile(r"\.dart$"),
    re.compile(r"\.tsx?$"),
]


def lint_l10a_phase_name(features: list[dict]) -> list[dict]:
    out = []
    for f in features:
        name = f.get("name", "")
        for pat in PHASE_NAME_PATTERNS:
            if pat.search(name):
                out.append({
                    "feature": f.get("id", "?"),
                    "rule": "L10a",
                    "msg": f"phase-named feature '{name}' — rewrite as vertical slice",
                })
                break
    return out


def lint_l10b_ui_smoke(features: list[dict]) -> list[dict]:
    out = []
    for f in features:
        # singleton feature.module_path is gone (deep-module hybrid refactor);
        # check every spec.module_design[*].module_path instead
        module_paths = [
            entry.get("module_path", "")
            for entry in f.get("spec", {}).get("module_design", [])
        ]
        is_ui = any(
            any(pat.search(mp) for pat in UI_PATH_PATTERNS)
            for mp in module_paths
        )
        if is_ui:
            l5 = f.get("test_contract", {}).get("l5_smoke_path")
            if not l5:
                ui_hits = [mp for mp in module_paths if any(pat.search(mp) for pat in UI_PATH_PATTERNS)]
                out.append({
                    "feature": f.get("id", "?"),
                    "rule": "L10b",
                    "msg": f"UI-touching feature (module_design paths matching UI: {ui_hits}) must set test_contract.l5_smoke_path",
                })
    return out


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

    features = data.get("features", []) if isinstance(data, dict) else []
    violations = []
    violations.extend(lint_l10a_phase_name(features))
    violations.extend(lint_l10b_ui_smoke(features))

    report = {
        "status": "PASS" if not violations else "FAIL",
        "violation_count": len(violations),
        "violations": violations,
    }
    print(json.dumps(report, indent=2))
    sys.exit(0 if not violations else 1)


if __name__ == "__main__":
    main()
