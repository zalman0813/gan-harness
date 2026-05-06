#!/usr/bin/env python3
"""gate_eval_postcommit.py — evaluator's L1+L2 (+optional L5) wrapper.

Evaluator subagent reads its handbook, sees the doctrine to run this
script when forming a verdict, and subprocess-invokes it.

Differences from the project's git pre-commit hook:

    - NO autofix (no in-place mutation during evaluation)
    - L1 scope = space-joined union of feature.spec.module_design[*].module_path
                 (the previous singleton feature.module_path is gone)
    - L2 scope = feature.test_contract.l2_path (whole test dir)
    - L5 scope = feature.test_contract.l5_smoke_path (only if non-null)
    - Does NOT run ac_coverage — the evaluator process is itself the
      adversarial verifier of AC literal coverage (per evaluator.md
      Principle #4 and the "Coverage check (AC-NN literal in test body)
      + anchor check + must_not check" step in the verdict process).
      The pre-commit hook ran ac_coverage at commit time as a mechanical
      gate; the evaluator independently re-verifies via its own grading.

Stages:
    L1: lint.check + typecheck over union of spec.module_design[*].module_path
    L2: test.unit over l2_path
    L5: test.smoke over l5_smoke_path (only if l5_smoke_path is non-null
        AND sensors.ini test.smoke is non-empty)

Verdict semantics (per evaluator doctrine):
    - L1 fail → whole feature FAIL
    - L2 fail → individual AC fails (caller maps test failures to ACs)
    - L5 fail → feature FAIL on the smoke band

This script just reports per-stage status and exit code; the caller
(evaluator process) decides verdict.

Usage:
    gate_eval_postcommit.py <feature_id> [round]

Exit codes:
    0  all stages PASS
    1  any stage FAILED
    2  script error (bad args, sensors.ini missing, no stack skill,
       feature not found in feature-list.json)
"""
from __future__ import annotations

import configparser
import json
import os
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent

_BAR = "──────────────────────────────────────────────────────────────"


# --- inline sensors.ini reader (was sensor_io.py) ----------------------------

def read_sensor(stack: Path | str, section: str, key: str) -> str:
    """Return value or empty string. No exception on missing file/section/key."""
    parser = configparser.ConfigParser(interpolation=None, allow_no_value=True)
    if not parser.read(Path(stack) / "sensors.ini", encoding="utf-8"):
        return ""
    if not parser.has_section(section) or not parser.has_option(section, key):
        return ""
    return parser.get(section, key) or ""


def render_sensor(template: str, **subs: str) -> str:
    """Substitute {key} placeholders in template with kwarg values."""
    out = template
    for k, v in subs.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def find_stack(project_dir: Path) -> Path | None:
    skills_root = project_dir / ".claude" / "skills"
    if not skills_root.is_dir():
        return None
    for d in sorted(skills_root.iterdir()):
        if d.is_dir() and (d / "sensors.ini").is_file():
            return d
    return None


def feature_scope(feature_list: Path, fid: str) -> tuple[str, str, str] | None:
    """Return (module_paths_joined, l2_path, l5_smoke_path) or None if feature
    not found. module_paths_joined is the space-joined union of every
    spec.module_design[*].module_path — the previous singleton
    feature.module_path field is gone; vertical slices have multiple modules
    and the L1 lint scope is the union."""
    try:
        data = json.loads(feature_list.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    for feat in data.get("features", []):
        if feat.get("id") == fid:
            tc = feat.get("test_contract", {}) or {}
            md_entries = feat.get("spec", {}).get("module_design", []) or []
            paths = [
                e.get("module_path", "")
                for e in md_entries
                if e.get("module_path")
            ]
            return (
                " ".join(paths),
                tc.get("l2_path", "") or "",
                tc.get("l5_smoke_path") or "",
            )
    return None


def run_stage(label: str, cmd: str, project_dir: Path) -> int:
    print()
    print(f"▶ {label}")
    if not cmd or not cmd.strip():
        print("  (skipped: sensors.ini value empty)")
        return 0
    print(f"  $ {cmd}")
    try:
        rc = subprocess.run(cmd, shell=True, cwd=project_dir).returncode
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"  ✗ FAIL (subprocess error: {exc})")
        return 1
    if rc == 0:
        print("  ✓ pass")
        return 0
    print(f"  ✗ FAIL (exit {rc})")
    return rc


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: gate_eval_postcommit.py <feature_id> [round]", file=sys.stderr)
        return 2
    feature = sys.argv[1]
    round_ = sys.argv[2] if len(sys.argv) > 2 else "0"

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    feature_list = project_dir / "specs" / "_batch" / "feature-list.json"

    if not feature_list.is_file():
        print(f"ERROR: {feature_list} missing", file=sys.stderr)
        return 2

    scope = feature_scope(feature_list, feature)
    if scope is None:
        print(
            f"ERROR: feature {feature} not found in {feature_list}", file=sys.stderr
        )
        return 2
    module_path, l2_path, l5_path = scope

    stack = find_stack(project_dir)
    if stack is None:
        print(
            "ERROR: no .claude/skills/<stack>/sensors.ini found", file=sys.stderr
        )
        return 2

    print(_BAR)
    print(f"gate_eval_postcommit: feature={feature} round={round_} stack={stack.name}")
    print(
        f"  module_paths={module_path}  l2={l2_path}  l5={l5_path or '<none>'}"
    )
    print(_BAR)

    overall = 0

    # --- L1 ---
    # scope = space-joined union of spec.module_design[*].module_path
    if run_stage(
        "L1 / lint.check (scope=module_design paths)",
        render_sensor(read_sensor(stack, "lint", "check"), scope=module_path),
        project_dir,
    ) != 0:
        overall = 1
    if run_stage(
        "L1 / typecheck (scope=module_design paths)",
        render_sensor(read_sensor(stack, "typecheck", "command"), scope=module_path),
        project_dir,
    ) != 0:
        overall = 1

    # --- L2 ---
    if run_stage(
        "L2 / test.unit (scope=l2_path)",
        render_sensor(read_sensor(stack, "test", "unit"), scope=l2_path),
        project_dir,
    ) != 0:
        overall = 1

    # --- L5 (optional) ---
    if l5_path:
        smoke_tmpl = read_sensor(stack, "test", "smoke")
        if smoke_tmpl:
            if run_stage(
                "L5 / test.smoke (scope=l5_smoke_path)",
                render_sensor(smoke_tmpl, scope=l5_path),
                project_dir,
            ) != 0:
                overall = 1
        else:
            print()
            print(
                "▶ L5 / test.smoke: SKIPPED (sensors.ini test.smoke is empty;"
            )
            print(
                "  declare a command in sensors.ini to enable smoke for this stack)"
            )
    else:
        print()
        print("▶ L5: SKIPPED (feature.test_contract.l5_smoke_path is null)")

    print()
    print(_BAR)
    print(f"gate_eval_postcommit: {'PASS' if overall == 0 else 'FAIL'}")
    print(_BAR)
    return overall


if __name__ == "__main__":
    sys.exit(main())
