#!/usr/bin/env python3
"""divergence_diff.py — post-round listing of new identifiers / paths /
external references introduced by generator that DON'T appear in any
anchor source (spec.md / intent.md / _research).

For sprint+round, walks the git diff of the round's commit, extracts
candidate "new" tokens (function defs, route literals, class names,
schema keys, file paths), and emits the subset that has no verbatim
appearance in spec.md / intent.md / _research/S{NN}/*.md.

Output: specs/_epic/_audit/S{NN}/divergence-R{R}.md

Designed for fast eyeball review by maintainer — surfaces "what
generator invented this round" so the over-interpretation pattern is
immediately visible.

Pure stdlib (uses git via subprocess). Exit 0 on success regardless of
divergence count; report is the value.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


# Identifier extractors per file kind. Each returns a set of strings.
def extract_python_idents(content: str) -> set[str]:
    idents: set[str] = set()
    idents.update(re.findall(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)", content, re.MULTILINE))
    idents.update(re.findall(r"^\s*class\s+([A-Z][a-zA-Z0-9_]*)", content, re.MULTILINE))
    idents.update(re.findall(r"@app\.(?:get|post|put|delete|patch)\([\"']([^\"']+)", content))
    return idents


def extract_typescript_idents(content: str) -> set[str]:
    idents: set[str] = set()
    idents.update(re.findall(r"function\s+([a-zA-Z_$][a-zA-Z0-9_$]*)", content))
    idents.update(re.findall(r"class\s+([A-Z][a-zA-Z0-9_$]*)", content))
    idents.update(re.findall(r"const\s+([a-zA-Z_$][a-zA-Z0-9_$]*)\s*=", content))
    idents.update(re.findall(r"data-testid=[\"']([^\"']+)", content))
    return idents


def extract_route_strings(content: str) -> set[str]:
    return set(re.findall(r"[\"'](/[a-zA-Z0-9_\-/{}]+)[\"']", content))


def extract_idents_from_diff(diff: str) -> set[str]:
    """Aggregate identifier candidates from a unified diff's added lines."""
    idents: set[str] = set()
    added_lines = [
        ln[1:]
        for ln in diff.splitlines()
        if ln.startswith("+") and not ln.startswith("+++")
    ]
    blob = "\n".join(added_lines)
    idents.update(extract_python_idents(blob))
    idents.update(extract_typescript_idents(blob))
    idents.update(extract_route_strings(blob))
    return idents


def collect_anchor_sources(epic_dir: Path, sprint: str) -> str:
    """Returns concatenated anchor text (spec + intent + sprint research)."""
    chunks: list[str] = []
    for name in ("spec.md", "intent.md"):
        p = epic_dir / name
        if p.exists():
            chunks.append(p.read_text(encoding="utf-8"))
    research_dir = epic_dir / "_research" / sprint
    if research_dir.is_dir():
        for md in sorted(research_dir.glob("*.md")):
            chunks.append(md.read_text(encoding="utf-8"))
    return "\n".join(chunks)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sprint", required=True, help="Sprint id, e.g. S01")
    parser.add_argument("--round", required=True, type=int, dest="round_num")
    parser.add_argument("--epic-dir", default="specs/_epic", type=Path)
    parser.add_argument("--diff-range", default="HEAD~1..HEAD", help="git diff range for this round's commit")
    args = parser.parse_args()

    epic_dir: Path = args.epic_dir

    try:
        diff = subprocess.check_output(
            ["git", "diff", args.diff_range],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        print(f"git diff failed: {e.output}", file=sys.stderr)
        return 2

    introduced = extract_idents_from_diff(diff)
    anchor_text = collect_anchor_sources(epic_dir, args.sprint).lower()
    un_anchored = sorted(
        ident for ident in introduced if ident.lower() not in anchor_text
    )
    anchored = sorted(
        ident for ident in introduced if ident.lower() in anchor_text
    )

    audit_dir = epic_dir / "_audit" / args.sprint
    audit_dir.mkdir(parents=True, exist_ok=True)
    out_path = audit_dir / f"divergence-R{args.round_num}.md"

    lines: list[str] = [
        f"# Divergence Report — {args.sprint} R{args.round_num}",
        "",
        f"Diff range: `{args.diff_range}`",
        f"Identifiers introduced: {len(introduced)}",
        f"Anchored (found in spec / intent / research): {len(anchored)}",
        f"Un-anchored (not in any anchor source): {len(un_anchored)}",
        "",
        "## Un-anchored identifiers",
        "",
    ]
    if un_anchored:
        for ident in un_anchored:
            lines.append(f"- `{ident}`")
    else:
        lines.append("(none — all introduced identifiers traceable to anchor sources)")
    lines.extend(
        [
            "",
            "## Anchored identifiers (informational)",
            "",
        ]
    )
    if anchored:
        for ident in anchored:
            lines.append(f"- `{ident}`")
    else:
        lines.append("(none)")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} ({len(un_anchored)} un-anchored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
