#!/usr/bin/env python3
"""gate_gen_precommit.py — generator's pre-commit batch gate.

The generator subagent reads its handbook, sees the doctrine to run this
script before `git commit`, and subprocess-invokes it. Inlined here:

    Stage 1 (autofix in place):
        [lint] fix          via stack's sensors.ini

    Stage 2 (read-only verification):
        [lint] check        via stack's sensors.ini
        [typecheck] command via stack's sensors.ini
        [test] unit         via stack's sensors.ini, scope=changed-files
        ac_coverage         INLINE (was sensor_ac_coverage.py)
        module_acl          INLINE (was sensor_module_acl.py)

There is NO separate sensor_*.py file. AC literal coverage and module ACL
boundaries are implemented as functions in this file — single caller, no
reuse, no subprocess hop.

The auto-fired Claude SubagentStop hook does NOT re-run ac_coverage. The
adversarial verification of AC literal coverage is performed by the
evaluator subagent's verdict process (see evaluator.md and
evaluator-handbook). This is the GAN pattern: generator self-checks here,
evaluator independently re-verifies on the next stage.

Usage:
    gate_gen_precommit.py <feature_id> [round]

Exit codes:
    0  all stages PASS; safe to commit
    1  any stage FAILED; do NOT commit (fix above + retry)
    2  script error (bad args, sensors.ini missing, no stack skill,
       feature not found in feature-list.json)
"""
from __future__ import annotations

import ast
import configparser
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

_BAR = "──────────────────────────────────────────────────────────────"


# ---------------------------------------------------------------------------
# sensors.ini reader (was sensor_io.py — inlined, no module dep)
# ---------------------------------------------------------------------------

def _read_sensor(stack: Path | str, section: str, key: str) -> str:
    parser = configparser.ConfigParser(interpolation=None, allow_no_value=True)
    if not parser.read(Path(stack) / "sensors.ini", encoding="utf-8"):
        return ""
    if not parser.has_section(section) or not parser.has_option(section, key):
        return ""
    return parser.get(section, key) or ""


def _render_sensor(template: str, **subs: str) -> str:
    out = template
    for k, v in subs.items():
        out = out.replace("{" + k + "}", str(v))
    return out


# ---------------------------------------------------------------------------
# Stack discovery + change scope
# ---------------------------------------------------------------------------

def _find_stack(project_dir: Path) -> Path | None:
    skills_root = project_dir / ".claude" / "skills"
    if not skills_root.is_dir():
        return None
    for d in sorted(skills_root.iterdir()):
        if d.is_dir() and (d / "sensors.ini").is_file():
            return d
    return None


def _collect_changed_scope(project_dir: Path) -> str:
    """Combined staged + unstaged + untracked changed file list, space-joined."""
    parts: set[str] = set()
    for cmd in (
        ["git", "diff", "--name-only", "--cached"],
        ["git", "diff", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        try:
            out = subprocess.run(
                cmd, cwd=project_dir, capture_output=True, text=True, timeout=10
            )
        except (subprocess.SubprocessError, OSError):
            continue
        if out.returncode == 0:
            for line in out.stdout.splitlines():
                line = line.strip()
                if line:
                    parts.add(line)
    return " ".join(sorted(parts))


def _run_shell(label: str, cmd: str, project_dir: Path) -> int:
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


# ---------------------------------------------------------------------------
# AC coverage check (was sensor_ac_coverage.py — inlined)
# ---------------------------------------------------------------------------

_TEST_FILE_GLOBS = [
    "test_*.py", "*_test.py",
    "*.test.ts", "*.test.tsx", "*.test.js", "*.test.jsx",
    "*.spec.ts", "*.spec.tsx", "*.spec.js", "*.spec.jsx",
    "*_test.go",
    "*_test.rs",
    "*Test.java",
    "*_test.dart",
]
_NON_PY_TEST_STARTERS = (
    "func Test", "fn test_",
    "void test_", "public void test",
    "it(", "test(", "describe(",
    "@Test",
)
_ABSENCE_MARKERS = (
    "not in",
    "not_in",
    "assert_absent", "assertNotIn", "assertNotEquals", "assertNotContains",
    "findsNothing",
    "toBeFalsy",
    "not.toBe", "not.toEqual", "not.toContain",
    ".not.",
    "to_not",
    "not contain", "doesNotContain",
    "shouldNot",
    "expect_not",
    "isFalse",
    "== false", "!== true", "!= true",
)
_LINE_HASH_COMMENT = re.compile(r"(?m)\s*#[^\n]*$")
_LINE_SLASH_COMMENT = re.compile(r"(?m)//[^\n]*$")
_BLOCK_C_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def _detect_lang(path: Path) -> str:
    return {
        ".py": "python",
        ".ts": "javascript", ".tsx": "javascript",
        ".js": "javascript", ".jsx": "javascript",
        ".go": "go", ".rs": "rust",
        ".java": "java", ".dart": "dart",
    }.get(path.suffix.lower(), "unknown")


def _strip_comments(src: str, lang: str) -> str:
    if lang == "python":
        return _LINE_HASH_COMMENT.sub("", src)
    src = _LINE_SLASH_COMMENT.sub("", src)
    src = _BLOCK_C_COMMENT.sub("", src)
    src = _LINE_HASH_COMMENT.sub("", src)
    return src


def _find_test_files(roots: Iterable[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if root is None or not root.exists():
            continue
        if root.is_file():
            out.append(root)
            continue
        for pat in _TEST_FILE_GLOBS:
            out.extend(root.rglob(pat))
    return sorted({p.resolve() for p in out})


def _python_function_bodies(source: str) -> dict[str, str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not node.name.startswith("test_"):
            continue
        try:
            body_src = "\n".join(ast.unparse(n) for n in node.body)
        except Exception:
            body_src = ""
        out[node.name] = f"{node.name}\n{body_src}"
    return out


def _fallback_test_blocks(source: str) -> list[tuple[str, str]]:
    lines = source.splitlines()
    blocks: list[list[str]] = [[]]
    for line in lines:
        stripped = line.lstrip()
        if any(stripped.startswith(s) for s in _NON_PY_TEST_STARTERS):
            blocks.append([line])
        else:
            blocks[-1].append(line)
    out: list[tuple[str, str]] = []
    for i, b in enumerate(blocks):
        if not b:
            continue
        out.append((f"block-{i}", "\n".join(b)))
    return out


def _collect_test_blocks(test_files: list[Path]) -> dict[Path, list[tuple[str, str]]]:
    out: dict[Path, list[tuple[str, str]]] = {}
    for path in test_files:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lang = _detect_lang(path)
        blocks: list[tuple[str, str]] = []
        if lang == "python":
            for name, body in _python_function_bodies(source).items():
                blocks.append((name, _strip_comments(body, "python")))
        else:
            for block_id, body in _fallback_test_blocks(source):
                blocks.append((block_id, _strip_comments(body, lang)))
        out[path] = blocks
    return out


def _ac_id_in_body(ac_id: str, body: str) -> bool:
    return ac_id in body or ac_id.replace("-", "_") in body


def _check_one_ac(ac: dict, test_index: dict[Path, list[tuple[str, str]]]) -> list[dict]:
    ac_id = ac["id"]
    missing: list[dict] = []
    blocks_containing_id: list[tuple[Path, str, str]] = []
    for path, blocks in test_index.items():
        for block_id, body in blocks:
            if _ac_id_in_body(ac_id, body):
                blocks_containing_id.append((path, block_id, body))
    if not blocks_containing_id:
        missing.append({
            "ac_id": ac_id, "kind": "ac_id_missing",
            "detail": f"literal '{ac_id}' (or underscore variant) not found in any test body after stripping comments",
        })
        return missing
    for anchor in ac.get("eval_anchors", []) or []:
        if not any(anchor in body for _, _, body in blocks_containing_id):
            missing.append({
                "ac_id": ac_id, "kind": "eval_anchor_missing", "anchor": anchor,
                "detail": f"eval_anchor '{anchor}' not present in any test body that references {ac_id}",
            })
    if ac.get("kind") == "negative":
        for must_not in ac.get("must_not", []) or []:
            paired = any(
                must_not in body and any(m in body for m in _ABSENCE_MARKERS)
                for _, _, body in blocks_containing_id
            )
            if not paired:
                missing.append({
                    "ac_id": ac_id, "kind": "must_not_unpaired", "must_not": must_not,
                    "detail": f"must_not literal '{must_not}' for negative AC {ac_id} has no paired absence-assertion",
                })
    return missing


def _stage_ac_coverage(feature: dict, project_dir: Path) -> int:
    """Return 0 if PASS, 1 if FAIL. Prints banner + missing entries."""
    print()
    print("▶ Stage 2 / ac_coverage")
    tc = feature.get("test_contract", {}) or {}
    roots: list[Path] = []
    for key in ("l2_path", "l5_smoke_path"):
        v = tc.get(key)
        if v:
            roots.append((project_dir / v).resolve())
    mp = feature.get("module_path")
    if mp:
        roots.append((project_dir / mp).resolve())
    if not roots:
        print("  ✗ FAIL: feature has no l2_path / l5_smoke_path / module_path")
        return 1
    test_files = _find_test_files(roots)
    if not test_files:
        print(f"  ✗ FAIL: no test files matched globs under {[str(r) for r in roots]}")
        return 1
    test_index = _collect_test_blocks(test_files)
    all_missing: list[dict] = []
    for ac in feature.get("spec", {}).get("ac", []) or []:
        all_missing.extend(_check_one_ac(ac, test_index))
    if all_missing:
        print(f"  ✗ FAIL ({len(all_missing)} missing across {len(test_files)} test files)")
        for m in all_missing:
            print(f"    - {m.get('ac_id', '-')}: {m['kind']}: {m['detail']}")
        return 1
    print(f"  ✓ pass (scanned {len(test_files)} test files)")
    return 0


# ---------------------------------------------------------------------------
# Module ACL check (was sensor_module_acl.py — inlined)
# ---------------------------------------------------------------------------

_ACL_TOOLS = ("import-linter", "dependency-cruiser", "none")


def _read_acl_section(sensors_ini: Path) -> dict[str, str] | None:
    cp = configparser.ConfigParser(interpolation=None, allow_no_value=True)
    if not cp.read(sensors_ini):
        return None
    if not cp.has_section("acl"):
        return None
    return {k: cp.get("acl", k, fallback="") or "" for k in cp.options("acl")}


def _render_import_linter(acl_pairs: list[dict], root_package: str) -> str:
    lines = [
        "[importlinter]",
        "root_packages =",
        f"    {root_package}",
        "include_external_packages = True",
        "",
    ]
    for i, pair in enumerate(acl_pairs, start=1):
        domain = pair["domain"]
        name = f"acl-{i}-domain-{domain.replace('.', '-')}"
        lines.append(f"[importlinter:contract:{i}]")
        lines.append(f"name = {name}")
        lines.append("type = forbidden")
        lines.append("source_modules =")
        lines.append(f"    {domain}")
        lines.append("forbidden_modules =")
        for fm in pair["forbidden"]:
            lines.append(f"    {fm}")
        if pair.get("adapter_hint"):
            lines.append(f"# adapter_hint: {pair['adapter_hint']}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def _render_dependency_cruiser(acl_pairs: list[dict]) -> str:
    rules: list[str] = []
    for i, pair in enumerate(acl_pairs, start=1):
        domain = pair["domain"]
        forbidden_pat = "|".join(pair["forbidden"])
        hint = pair.get("adapter_hint", "")
        comment = f"// adapter_hint: {hint}" if hint else ""
        rules.append(
            f"    {{\n"
            f"      name: 'acl-{i}-{domain.replace('.', '-').replace('/', '-')}',\n"
            f"      severity: 'error',\n"
            f"      from: {{ path: '^{domain.replace('.', '/')}' }},\n"
            f"      to: {{ path: '^node_modules/({forbidden_pat})' }}\n"
            f"    }}{comment}"
        )
    body = ",\n".join(rules)
    return f"module.exports = {{\n  forbidden: [\n{body}\n  ]\n}};\n"


def _stage_module_acl(feature: dict, stack: Path, project_dir: Path) -> int:
    print()
    print("▶ Stage 2 / module_acl")
    acl_pairs = feature.get("acl_pairs", []) or []
    if not acl_pairs:
        print("  (skipped: feature has no acl_pairs)")
        return 0
    acl = _read_acl_section(stack / "sensors.ini")
    if acl is None:
        print("  (skipped: sensors.ini has no [acl] section)")
        return 0
    tool = acl.get("tool", "").strip()
    if tool not in _ACL_TOOLS:
        print(f"  ✗ FAIL: acl.tool='{tool}' not in {_ACL_TOOLS}")
        return 1
    if tool == "none":
        print(f"  (skipped: stack '{stack.name}' has acl.tool=none)")
        return 0

    invoke = acl.get("invoke", "").strip()
    config_format = acl.get("config_format", "").strip()

    if tool == "import-linter":
        if config_format != "ini":
            print(f"  ✗ FAIL: import-linter expects config_format=ini, got '{config_format}'")
            return 1
        root = acl_pairs[0]["domain"].split(".")[0].split("/")[0]
        config_text = _render_import_linter(acl_pairs, root)
        suffix = ".ini"
    else:  # dependency-cruiser
        if config_format != "cjs":
            print(f"  ✗ FAIL: dependency-cruiser expects config_format=cjs, got '{config_format}'")
            return 1
        config_text = _render_dependency_cruiser(acl_pairs)
        suffix = ".cjs"

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    ) as tf:
        tf.write(config_text)
        config_path = Path(tf.name)
    try:
        cmd = invoke.replace("{config_path}", str(config_path))
        print(f"  $ {cmd}")
        res = subprocess.run(
            cmd, shell=True, cwd=str(project_dir),
            capture_output=True, text=True, check=False,
        )
    finally:
        try:
            config_path.unlink()
        except OSError:
            pass

    if res.returncode == 0:
        print("  ✓ pass")
        return 0
    print(f"  ✗ FAIL (exit {res.returncode})")
    if res.stdout:
        for line in res.stdout.splitlines()[:30]:
            print(f"    {line}")
    if res.stderr:
        for line in res.stderr.splitlines()[:30]:
            print(f"    err: {line}")
    return 1


# ---------------------------------------------------------------------------
# Feature lookup
# ---------------------------------------------------------------------------

def _find_feature(feature_list_path: Path, fid: str) -> dict | None:
    try:
        data = json.loads(feature_list_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    for f in data.get("features", []):
        if f.get("id") == fid:
            return f
    return None


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    if len(sys.argv) < 2:
        print("usage: gate_gen_precommit.py <feature_id> [round]", file=sys.stderr)
        return 2
    feature_id = sys.argv[1]
    round_ = sys.argv[2] if len(sys.argv) > 2 else "0"

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
    feature_list_path = project_dir / "specs" / "_batch" / "feature-list.json"

    stack = _find_stack(project_dir)
    if stack is None:
        print(
            f"ERROR: no .claude/skills/<stack>/sensors.ini found under {project_dir}",
            file=sys.stderr,
        )
        return 2

    scope = _collect_changed_scope(project_dir)

    print(_BAR)
    print(f"gate_gen_precommit: feature={feature_id} round={round_} stack={stack.name}")
    print(_BAR)
    if not scope:
        print("WARN: no changed files detected; running gates with empty scope.")

    overall = 0

    # --- Stage 1: autofix ---
    fix_cmd = _render_sensor(_read_sensor(stack, "lint", "fix"), scope=scope)
    rc = _run_shell("Stage 1 / lint.fix", fix_cmd, project_dir)
    if rc != 0:
        print()
        print(_BAR)
        print("gate_gen_precommit: FAIL (stage 1)")
        print(_BAR)
        return 1

    # --- Stage 2 read-only checks ---
    for label, cmd in (
        ("Stage 2 / lint.check",
         _render_sensor(_read_sensor(stack, "lint", "check"), scope=scope)),
        ("Stage 2 / typecheck",
         _render_sensor(_read_sensor(stack, "typecheck", "command"), scope=scope)),
        ("Stage 2 / test.unit (scope=changed)",
         _render_sensor(_read_sensor(stack, "test", "unit"), scope=scope)),
    ):
        if _run_shell(label, cmd, project_dir) != 0:
            overall = 1

    # --- Stage 2 inlined sensors (need feature dict) ---
    feature = _find_feature(feature_list_path, feature_id)
    if feature is None:
        print()
        print(f"WARN: {feature_list_path} missing or feature {feature_id} not found; "
              "skipping ac_coverage + module_acl")
    else:
        if _stage_ac_coverage(feature, project_dir) != 0:
            overall = 1
        if _stage_module_acl(feature, stack, project_dir) != 0:
            overall = 1

    print()
    print(_BAR)
    if overall == 0:
        print("gate_gen_precommit: PASS — safe to commit")
    else:
        print("gate_gen_precommit: FAIL — do NOT commit; fix above and retry")
    print(_BAR)
    return overall


if __name__ == "__main__":
    sys.exit(main())
