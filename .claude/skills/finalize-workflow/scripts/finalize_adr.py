#!/usr/bin/env python3
"""finalize_adr.py — v3.8 finalize Phase 1.

For every `docs/adr/NNNN-*.md` whose frontmatter has `status: proposed`:
  1. Change `status: proposed` -> `status: accepted`.
  2. Set `accepted_date: <today>` (ISO 8601). If the key exists, replace
     the value; if missing, insert it after `proposed_date:`.
  3. If the ADR's `supersedes:` lists predecessor ids (`["ADR-XXXX"]`),
     retroactively backfill the predecessor's `superseded_by` field
     to point at this ADR — but ONLY if the predecessor's current
     `superseded_by` is null (we never overwrite an existing pointer).

After all promotions, regenerate `docs/adr/index.md` from the accepted
set (sorted by ADR id), pulling title + status + accepted_date from
frontmatter.

This script is the SINGLE place that knows the frontmatter schema for
status/date/supersedes. It uses a hand-rolled YAML subset parser (no
PyYAML dependency) so gan-harness target projects don't inherit a third-
party install requirement.

Idempotent: re-running after a successful promotion is a no-op (every
ADR is already accepted, indexing produces byte-identical output).

Usage:
  finalize_adr.py [--adr-dir docs/adr]
                  [--today YYYY-MM-DD]   (default: today's date in local TZ)
                  [--check]              dry-run; print what would change

Exit:
  0 OK (with JSON summary on stdout)
  1 IO / parse error
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

FRONTMATTER_DELIM = "---"
ADR_FILE_RE = re.compile(r"^(\d{4})-.+\.md$")
ADR_ID_RE = re.compile(r"^ADR-(\d{4})$")


@dataclass
class ADRFile:
    path: Path
    frontmatter: dict[str, str | list[str] | None]
    frontmatter_lines: list[str]
    body_lines: list[str]


def parse_frontmatter(text: str) -> tuple[list[str], list[str]]:
    """Split the file into (frontmatter_lines, body_lines).

    Frontmatter is the block between the first two `---` lines, exactly.
    If there is no frontmatter, returns ([], all_lines)."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIM:
        return [], lines
    closing = None
    for i in range(1, len(lines)):
        if lines[i].strip() == FRONTMATTER_DELIM:
            closing = i
            break
    if closing is None:
        return [], lines
    return lines[1:closing], lines[closing + 1:]


def parse_yaml_subset(frontmatter_lines: list[str]) -> dict[str, str | list[str] | None]:
    """Tiny YAML subset parser sufficient for our frontmatter schema.

    Handles:
      key: value           -> str (stripped)
      key: null            -> None (also "" / "~" as null)
      key: []              -> []
      key: [a, b]          -> ["a", "b"]  (inline flow sequence)
      key:                 -> reads following `  - item` lines (block sequence)
        - item
        - item

    Refuses anything more exotic. Other constructs surface as a string
    value containing the raw RHS so we can write it back verbatim, but
    callers that need to mutate the value must handle the simple cases.
    """
    out: dict[str, str | list[str] | None] = {}
    i = 0
    while i < len(frontmatter_lines):
        line = frontmatter_lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$", line)
        if not m:
            i += 1
            continue
        key = m.group(1)
        raw_val = m.group(2)
        if raw_val == "" or raw_val.lower() in {"null", "~"}:
            # Possibly start of block sequence
            block_items: list[str] = []
            j = i + 1
            while j < len(frontmatter_lines):
                bl = frontmatter_lines[j]
                bm = re.match(r"^\s{2,}-\s+(.+?)\s*$", bl)
                if bm:
                    block_items.append(bm.group(1).strip())
                    j += 1
                    continue
                if not bl.strip() or bl.strip().startswith("#"):
                    j += 1
                    continue
                break
            if block_items:
                out[key] = block_items
                i = j
                continue
            out[key] = None if raw_val == "" or raw_val.lower() in {"null", "~"} else raw_val
            i += 1
            continue
        if raw_val.startswith("[") and raw_val.endswith("]"):
            inner = raw_val[1:-1].strip()
            if not inner:
                out[key] = []
            else:
                out[key] = [s.strip().strip('"').strip("'") for s in inner.split(",")]
            i += 1
            continue
        # Strip optional quotes on plain scalars
        if (raw_val.startswith('"') and raw_val.endswith('"')) or (
            raw_val.startswith("'") and raw_val.endswith("'")
        ):
            raw_val = raw_val[1:-1]
        out[key] = raw_val
        i += 1
    return out


def render_yaml_subset(
    original_lines: list[str], mutations: dict[str, str | list[str] | None]
) -> list[str]:
    """Apply key-level mutations to original frontmatter lines, preserving
    line order, comments, and unrelated keys verbatim.

    Mutations whose key is NOT present in original_lines are appended at
    the end, in mutations-insertion order. Block-sequence values
    (list of str) are emitted as inline flow style `[a, b]` to keep this
    script simple; we don't currently mutate the `authors:` field which
    is the only block sequence in the frontmatter spec.
    """
    out: list[str] = []
    consumed_keys: set[str] = set()
    # Build a lookup of which lines belong to a multi-line block sequence
    # so we copy them verbatim when not mutating that key.
    i = 0
    while i < len(original_lines):
        line = original_lines[i]
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*?)\s*$", line)
        if not m:
            out.append(line)
            i += 1
            continue
        key = m.group(1)
        raw_val = m.group(2)
        is_block_start = (raw_val == "" or raw_val.lower() in {"null", "~"})
        block_run_end = i + 1
        if is_block_start:
            # Scan forward over `  - item` lines
            while block_run_end < len(original_lines):
                bl = original_lines[block_run_end]
                if re.match(r"^\s{2,}-\s+\S", bl) or (
                    not bl.strip() or bl.strip().startswith("#")
                ):
                    block_run_end += 1
                else:
                    break

        if key in mutations:
            consumed_keys.add(key)
            new_val = mutations[key]
            if isinstance(new_val, list):
                if not new_val:
                    out.append(f"{key}: []")
                else:
                    out.append(f"{key}: [{', '.join(new_val)}]")
            elif new_val is None:
                out.append(f"{key}: null")
            else:
                out.append(f"{key}: {new_val}")
            # Skip past the original block run if there was one.
            i = block_run_end if is_block_start else i + 1
            continue

        # Not mutating this key — copy verbatim, including any block run.
        if is_block_start:
            for k in range(i, block_run_end):
                out.append(original_lines[k])
            i = block_run_end
        else:
            out.append(line)
            i += 1

    # Append insertions for keys not present in the original frontmatter.
    for key, val in mutations.items():
        if key in consumed_keys:
            continue
        if isinstance(val, list):
            if not val:
                out.append(f"{key}: []")
            else:
                out.append(f"{key}: [{', '.join(val)}]")
        elif val is None:
            out.append(f"{key}: null")
        else:
            out.append(f"{key}: {val}")
    return out


def load_adrs(adr_dir: Path) -> dict[str, ADRFile]:
    """Return {adr_id: ADRFile} for every NNNN-*.md in adr_dir."""
    adrs: dict[str, ADRFile] = {}
    for p in sorted(adr_dir.glob("*.md")):
        if p.name == "index.md":
            continue
        if not ADR_FILE_RE.match(p.name):
            continue
        text = p.read_text(encoding="utf-8")
        fm_lines, body_lines = parse_frontmatter(text)
        fm = parse_yaml_subset(fm_lines)
        adr_id = fm.get("id")
        if not adr_id or not isinstance(adr_id, str):
            print(f"WARN: {p} has no `id` in frontmatter — skipping", file=sys.stderr)
            continue
        adrs[adr_id] = ADRFile(
            path=p,
            frontmatter=fm,
            frontmatter_lines=fm_lines,
            body_lines=body_lines,
        )
    return adrs


def write_adr(adr: ADRFile, new_fm_lines: list[str]) -> None:
    out = [FRONTMATTER_DELIM] + new_fm_lines + [FRONTMATTER_DELIM] + adr.body_lines
    text = "\n".join(out)
    if not text.endswith("\n"):
        text += "\n"
    adr.path.write_text(text, encoding="utf-8")


def render_index(
    adrs: dict[str, ADRFile], adr_dir: Path
) -> str:
    rows: list[tuple[str, str, str, str, str]] = []
    for adr_id, adr in sorted(adrs.items()):
        m = ADR_ID_RE.match(adr_id)
        num = m.group(1) if m else adr_id
        title = adr.frontmatter.get("title") or ""
        status = adr.frontmatter.get("status") or "?"
        accepted_date = adr.frontmatter.get("accepted_date") or "—"
        filename = adr.path.name
        rows.append((adr_id, str(title), str(status), str(accepted_date), filename))
    out: list[str] = [
        "# Architecture Decision Records",
        "",
        "| ID | Title | Status | Date |",
        "|----|-------|--------|------|",
    ]
    for adr_id, title, status, date, filename in rows:
        out.append(f"| [{adr_id}]({filename}) | {title} | {status} | {date} |")
    out.append("")
    return "\n".join(out)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--adr-dir", default="docs/adr")
    ap.add_argument("--today", default=dt.date.today().isoformat())
    ap.add_argument("--check", action="store_true",
                    help="Dry-run; print plan, do not modify files.")
    args = ap.parse_args(argv)

    adr_dir = Path(args.adr_dir)
    if not adr_dir.is_dir():
        print(f"ERROR: {adr_dir} is not a directory", file=sys.stderr)
        return 1

    adrs = load_adrs(adr_dir)
    if not adrs:
        print(json.dumps({
            "promoted": [],
            "backfilled_superseded_by": [],
            "index_path": str(adr_dir / "index.md"),
            "note": "no ADR files found",
        }, indent=2))
        return 0

    promoted: list[str] = []
    backfilled: list[dict[str, str]] = []

    # Plan promotions
    for adr_id, adr in adrs.items():
        if adr.frontmatter.get("status") == "proposed":
            promoted.append(adr_id)

    # Plan supersedes backfill — predecessor's superseded_by must be null/None
    for adr_id, adr in adrs.items():
        if adr_id not in promoted:
            # Only newly-promoted ADRs trigger backfill on their predecessors.
            # Already-accepted ADRs were handled in a prior run.
            continue
        supersedes_val = adr.frontmatter.get("supersedes") or []
        if not isinstance(supersedes_val, list):
            continue
        for predecessor_id in supersedes_val:
            predecessor = adrs.get(predecessor_id)
            if predecessor is None:
                print(
                    f"WARN: {adr_id} declares supersedes: [{predecessor_id}] "
                    f"but {predecessor_id} not found in {adr_dir}",
                    file=sys.stderr,
                )
                continue
            current = predecessor.frontmatter.get("superseded_by")
            if current and current != "null":
                # Predecessor already pointed at someone else — refuse to overwrite.
                print(
                    f"WARN: {predecessor_id}.superseded_by already set to "
                    f"{current!r}; leaving alone (would-be: {adr_id}).",
                    file=sys.stderr,
                )
                continue
            backfilled.append({"predecessor": predecessor_id, "by": adr_id})

    if args.check:
        print(json.dumps({
            "promoted": promoted,
            "backfilled_superseded_by": backfilled,
            "index_path": str(adr_dir / "index.md"),
            "mode": "check",
        }, indent=2))
        return 0

    # Apply promotions
    for adr_id in promoted:
        adr = adrs[adr_id]
        mutations: dict[str, str | list[str] | None] = {
            "status": "accepted",
            "accepted_date": args.today,
        }
        new_fm_lines = render_yaml_subset(adr.frontmatter_lines, mutations)
        write_adr(adr, new_fm_lines)
        adr.frontmatter["status"] = "accepted"
        adr.frontmatter["accepted_date"] = args.today
        adr.frontmatter_lines = new_fm_lines

    # Apply backfills
    for entry in backfilled:
        pred = adrs[entry["predecessor"]]
        mutations = {"superseded_by": entry["by"]}
        new_fm_lines = render_yaml_subset(pred.frontmatter_lines, mutations)
        write_adr(pred, new_fm_lines)
        pred.frontmatter["superseded_by"] = entry["by"]
        pred.frontmatter_lines = new_fm_lines

    # Regenerate index
    index_path = adr_dir / "index.md"
    index_path.write_text(render_index(adrs, adr_dir) + "\n", encoding="utf-8")

    print(json.dumps({
        "promoted": promoted,
        "backfilled_superseded_by": backfilled,
        "index_path": str(index_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
