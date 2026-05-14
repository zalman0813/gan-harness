#!/usr/bin/env python3
"""regen_codemap.py — v3.8 finalize Phase 3.

Generates CODEMAP.md from real source-tree evidence — module-level
docstrings AND public-function signatures. The script never invents:
when a module lacks a barrel docstring, the row says
`_(no barrel docstring — add one to surface this module)_` so the gap
is visible in the diff instead of silently swept under "AI summary".

Two top-level passes:

A. Module pass — walks every package directory that has an `__init__.py`
   (Python's barrel convention; other stacks add their own barrel via
   `--barrel-glob` if needed). For each directory:
     1. Read `__init__.py`'s module docstring -> Purpose column.
     2. For each `*.py` sibling (excluding `__init__.py` and tests):
        - Read its module docstring (first triple-quoted string).
        - Scan top-level `def <name>(...)` and `class <Name>` definitions
          where the name does NOT start with `_`.
        - Render as one table row.

B. Test pass — walks `tests/**/test_*.py`. For each file:
     1. Read module docstring -> "Covers" column.
     2. If no docstring, fall back to the first `def test_*` function
        name -> "Covers: <name>" surrogate.
     3. If neither exists, write `_(no docstring; first test: ?)_`.

Output is deterministic: directories sorted alphabetically, files
sorted within their directory. Re-running produces byte-identical
output (idempotent under no source-tree changes).

Usage:
  regen_codemap.py [--root .]
                   [--out CODEMAP.md]
                   [--tests-dir tests]
                   [--exclude-dir <pattern> ...]   (default: .venv, node_modules,
                                                    .git, dist, build, __pycache__,
                                                    .pytest_cache)

Exit:
  0 OK (CODEMAP.md written)
  1 IO error
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_EXCLUDES = {
    ".venv",
    "venv",
    "node_modules",
    ".git",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "specs",  # epic / archive artefacts, not source
    "docs",   # ADRs, not source
}


@dataclass
class ModuleRow:
    rel_path: str
    purpose: str
    entry_points: list[str] = field(default_factory=list)


@dataclass
class PackageBlock:
    package_dir: str  # relative directory, e.g. "onboarding"
    barrel_purpose: str  # __init__.py docstring or sentinel
    modules: list[ModuleRow] = field(default_factory=list)


@dataclass
class TestRow:
    rel_path: str
    covers: str


def short_docstring(node_or_str: ast.AST | str | None) -> str:
    """Return the first paragraph of a docstring as one line, or empty."""
    if node_or_str is None:
        return ""
    if isinstance(node_or_str, str):
        doc = node_or_str
    else:
        doc = ast.get_docstring(node_or_str) or ""
    if not doc:
        return ""
    # First paragraph: text up to the first blank line.
    para = re.split(r"\n\s*\n", doc.strip(), maxsplit=1)[0]
    para = re.sub(r"\s+", " ", para).strip()
    if len(para) > 200:
        para = para[:199].rstrip() + "…"
    return para


def parse_module(py_path: Path) -> tuple[str, list[str]]:
    """Return (module_docstring_one_line, public_entry_points_signature_list).

    Entry points are top-level `def` and `class` whose name does NOT
    start with `_`. Signatures are pretty-printed as `name(arg1, arg2)`
    without type annotations to keep the table readable.
    """
    try:
        text = py_path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(py_path))
    except (SyntaxError, OSError):
        return "", []
    doc = short_docstring(tree)
    entries: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("_"):
                continue
            args = [a.arg for a in node.args.args]
            entries.append(f"`{node.name}({', '.join(args)})`")
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("_"):
                continue
            entries.append(f"`class {node.name}`")
    return doc, entries


def collect_packages(
    root: Path, excludes: set[str], tests_dir_name: str
) -> list[PackageBlock]:
    """Walk `root` for directories containing `__init__.py`.

    The tests directory (default name `tests`) is excluded here because
    it has its own dedicated section in the output — see `collect_tests`.
    """
    blocks: list[PackageBlock] = []
    for init in sorted(root.rglob("__init__.py")):
        rel = init.parent.relative_to(root)
        parts = rel.parts
        if any(p in excludes for p in parts):
            continue
        if parts and parts[0] == tests_dir_name:
            # Tests get their own section; skip from the package pass.
            continue
        if str(rel) == ".":
            # Project-root __init__.py — uncommon, skip.
            continue
        # Barrel docstring
        try:
            tree = ast.parse(init.read_text(encoding="utf-8"), filename=str(init))
            barrel_doc = short_docstring(tree)
        except (SyntaxError, OSError):
            barrel_doc = ""
        block = PackageBlock(
            package_dir=str(rel),
            barrel_purpose=barrel_doc or (
                "_(no barrel docstring — add one to surface this module)_"
            ),
        )
        # Sibling .py files
        for sib in sorted(init.parent.iterdir()):
            if not sib.is_file() or sib.suffix != ".py":
                continue
            if sib.name in {"__init__.py"}:
                continue
            if sib.name.startswith("test_") or sib.name.startswith("_test_"):
                continue
            doc, entries = parse_module(sib)
            block.modules.append(ModuleRow(
                rel_path=str(sib.relative_to(root)),
                purpose=doc or "_(no module docstring)_",
                entry_points=entries,
            ))
        blocks.append(block)
    return blocks


def collect_tests(
    root: Path, tests_dir: Path, excludes: set[str]
) -> list[TestRow]:
    rows: list[TestRow] = []
    if not tests_dir.is_dir():
        return rows
    for path in sorted(tests_dir.rglob("test_*.py")):
        rel = path.relative_to(root)
        if any(p in excludes for p in rel.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=str(path))
        except (SyntaxError, OSError):
            rows.append(TestRow(str(rel), "_(parse error)_"))
            continue
        doc = short_docstring(tree)
        if doc:
            covers = doc
        else:
            # Fall back to first def test_*
            first_test = None
            for node in tree.body:
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name.startswith("test_")
                ):
                    first_test = node.name
                    break
            if first_test:
                covers = f"_(no docstring; first test: `{first_test}`)_"
            else:
                covers = "_(no docstring; no `test_*` function found)_"
        rows.append(TestRow(str(rel), covers))
    return rows


def render(
    blocks: list[PackageBlock], tests: list[TestRow]
) -> str:
    out: list[str] = [
        "# CODEMAP",
        "",
        "Navigation guide regenerated by `/finalize regen_codemap.py` from",
        "real source-tree evidence (`__init__.py` docstrings + module docstrings + public",
        "`def`/`class` signatures). Empty cells mean the source lacks a docstring —",
        "this is a prompt to ADD one to surface the module, not for /finalize to invent.",
        "",
    ]
    for block in blocks:
        out.append(f"## {block.package_dir} — {block.barrel_purpose}")
        out.append("")
        if not block.modules:
            out.append("_(package has `__init__.py` but no sibling modules)_")
            out.append("")
            continue
        out.append("| Module | Purpose | Entry points |")
        out.append("|--------|---------|--------------|")
        for m in block.modules:
            entries = ", ".join(m.entry_points) if m.entry_points else "—"
            out.append(f"| `{m.rel_path}` | {m.purpose} | {entries} |")
        out.append("")
    if tests:
        out.append("## tests — Test suite")
        out.append("")
        out.append("| File | Covers |")
        out.append("|------|--------|")
        for t in tests:
            out.append(f"| `{t.rel_path}` | {t.covers} |")
        out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="CODEMAP.md")
    ap.add_argument("--tests-dir", default="tests")
    ap.add_argument("--exclude-dir", action="append", default=[])
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    excludes = set(DEFAULT_EXCLUDES) | set(args.exclude_dir)

    blocks = collect_packages(root, excludes, args.tests_dir)
    tests = collect_tests(root, root / args.tests_dir, excludes)

    if not blocks and not tests:
        print(
            "WARN: no Python packages or tests found — CODEMAP would be "
            "empty. Refusing to write.",
            file=sys.stderr,
        )
        return 1

    text = render(blocks, tests)
    out_path = (root / args.out) if not Path(args.out).is_absolute() else Path(args.out)
    out_path.write_text(text + ("\n" if not text.endswith("\n") else ""), encoding="utf-8")

    print(json.dumps({
        "packages": len(blocks),
        "modules": sum(len(b.modules) for b in blocks),
        "tests": len(tests),
        "missing_barrel_docstrings": [
            b.package_dir for b in blocks
            if b.barrel_purpose.startswith("_(no barrel docstring")
        ],
        "missing_module_docstrings": [
            m.rel_path for b in blocks for m in b.modules
            if m.purpose.startswith("_(no module docstring")
        ],
        "missing_test_docstrings": [
            t.rel_path for t in tests
            if t.covers.startswith("_(no docstring")
        ],
        "out_path": str(out_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
