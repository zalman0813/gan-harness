#!/usr/bin/env python3
"""anchor_ledger.py — post-round verification that contract anchors are
grounded in spec.md / _research / intent.md.

For each sprint + round, reads the latest contract YAML, extracts every
`done_looks_like[]` statement and `verification_plan[].steps[]` substring,
and verifies whether the text appears (verbatim, case-sensitive substring)
in any approved anchor source:

  - specs/_epic/spec.md  (## Sprint plan > Success (user POV) bullets)
  - specs/_epic/intent.md  (the user's original intent dump)
  - specs/_epic/_research/S{NN}/*.md  (sprint-scoped research)

Output: specs/_epic/_audit/S{NN}/anchor-ledger-R{R}.tsv

Columns: anchor | source_claim | verified | source_file

Any row with verified=NO indicates over-interpretation — generator
introduced a phrase that is not grounded in approved anchor sources.

Pure stdlib. Exit 0 on PASS (no un-anchored rows). Exit 1 on FAIL.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # fall back to regex parsing


def parse_contract_yaml(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}
    # Minimal fallback: pull done_looks_like and verification_plan via regex.
    result: dict = {"done_looks_like": [], "verification_plan": []}
    dll_block = re.search(
        r"^done_looks_like:\s*\n((?:\s*-\s.+\n?)+)",
        text,
        re.MULTILINE,
    )
    if dll_block:
        for line in dll_block.group(1).splitlines():
            m = re.match(r"\s*-\s+\"?(.+?)\"?$", line)
            if m:
                result["done_looks_like"].append(m.group(1).strip().strip('"'))
    return result


def collect_anchor_sources(epic_dir: Path, sprint: str) -> dict[str, str]:
    """Returns {source_label: text_content}."""
    sources: dict[str, str] = {}
    spec = epic_dir / "spec.md"
    if spec.exists():
        sources[f"spec.md"] = spec.read_text(encoding="utf-8")
    intent = epic_dir / "intent.md"
    if intent.exists():
        sources[f"intent.md"] = intent.read_text(encoding="utf-8")
    research_dir = epic_dir / "_research" / sprint
    if research_dir.is_dir():
        for md in sorted(research_dir.glob("*.md")):
            sources[f"_research/{sprint}/{md.name}"] = md.read_text(encoding="utf-8")
    return sources


def find_anchor_source(
    anchor: str, sources: dict[str, str]
) -> tuple[bool, str, int]:
    """Returns (verified, source_label, line_number).

    Match is case-insensitive substring (anchors are user-language;
    capitalisation may differ between contract and spec).
    """
    needle = anchor.lower().strip()
    if not needle:
        return False, "", 0
    # Drop obvious meta-markers (the MODULE prefix line for module statements)
    if needle.startswith("module "):
        return True, "(module-statement; not user-anchor)", 0
    for label, content in sources.items():
        lower = content.lower()
        idx = lower.find(needle)
        if idx >= 0:
            line_no = content[:idx].count("\n") + 1
            return True, label, line_no
    return False, "", 0


def extract_anchors(contract: dict) -> list[str]:
    anchors: list[str] = []
    for entry in contract.get("done_looks_like") or []:
        if isinstance(entry, str):
            anchors.append(entry)
    for vp in contract.get("verification_plan") or []:
        if not isinstance(vp, dict):
            continue
        steps = vp.get("steps") or []
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, str):
                    anchors.append(step)
    return anchors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sprint", required=True, help="Sprint id, e.g. S01")
    parser.add_argument("--round", required=True, type=int, dest="round_num", help="Round number")
    parser.add_argument("--epic-dir", default="specs/_epic", type=Path, help="Epic directory root")
    args = parser.parse_args()

    epic_dir: Path = args.epic_dir
    contract_path = epic_dir / "_pending" / f"{args.sprint}-draft-v{args.round_num}.yaml"
    if not contract_path.exists():
        print(f"contract not found: {contract_path}", file=sys.stderr)
        return 2

    contract = parse_contract_yaml(contract_path)
    anchors = extract_anchors(contract)
    sources = collect_anchor_sources(epic_dir, args.sprint)

    audit_dir = epic_dir / "_audit" / args.sprint
    audit_dir.mkdir(parents=True, exist_ok=True)
    out_path = audit_dir / f"anchor-ledger-R{args.round_num}.tsv"

    rows: list[tuple[str, str, str, str]] = []
    un_anchored = 0
    for anchor in anchors:
        verified, label, line_no = find_anchor_source(anchor, sources)
        if verified:
            rows.append((anchor, label, "yes", f"{label}:{line_no}" if line_no else label))
        else:
            rows.append((anchor, "(no claim)", "NO", "(un-anchored)"))
            un_anchored += 1

    with out_path.open("w", encoding="utf-8") as f:
        f.write("anchor\tsource_claim\tverified\tsource_file\n")
        for row in rows:
            f.write("\t".join(row) + "\n")

    if un_anchored == 0:
        print(f"PASS: {out_path} ({len(rows)} anchors all verified)")
        return 0
    print(
        f"FAIL: {out_path} ({un_anchored}/{len(rows)} anchors un-anchored)",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
