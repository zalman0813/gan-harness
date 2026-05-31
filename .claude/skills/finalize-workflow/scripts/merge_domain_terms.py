#!/usr/bin/env python3
"""merge_domain_terms.py — v3.8 finalize Phase 2.

Parses the `### Domain terms` sub-section of `specs/_epic/spec.md`'s
`## Cross-cutting constraints` (format enforced by spec_lint.py L08)
and appends each new term to `CONTEXT.md`'s `## Language` section.

Idempotent: re-running on the same epic produces zero changes (existing
terms are skipped by case-insensitive bold-name match).

The spec.md format is strict (single source of truth: spec_lint.py L08):

    ### Domain terms
    - **<term>** — <definition>
    - **<term-with-context>** — <definition that may continue on the
      next line as long as the continuation indents with two spaces>

CONTEXT.md format mirrors what the planner writes:

    ## Language

    - **<term>** — <definition>
    - **<term>** — <definition>

The script does NOT prompt and never invents terms. If spec.md has no
`### Domain terms` sub-section (or it's empty), exit 0 with appended=[].

Usage:
  merge_domain_terms.py [--spec specs/_epic/spec.md]
                        [--context CONTEXT.md]

Exit:
  0 OK (no error; appended may be empty)
  1 IO error or malformed spec.md (lint L08 violation)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Locate the `## Cross-cutting constraints` section, then within it find
# `### Domain terms`. We use a state machine rather than one mega-regex
# because markdown sections can have arbitrary content.

H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
# Term bullet: `- **name** — definition` (em-dash or `--`).
TERM_BULLET_RE = re.compile(r"^-\s+\*\*([^*]+?)\*\*\s+(?:—|--)\s+(.+?)\s*$")
# Bullet name on its own line (for existing CONTEXT.md scan).
EXISTING_TERM_RE = re.compile(r"^-\s+\*\*([^*]+?)\*\*\s+(?:—|--)\s+")


def extract_domain_terms_block(spec_text: str) -> list[str]:
    """Return the lines belonging to the `### Domain terms` block under
    `## Cross-cutting constraints`. Empty list if the block is absent.

    Refuses to guess: if `### Domain terms` appears OUTSIDE `## Cross-
    cutting constraints`, we still pick it up (planner may have put it
    elsewhere) but only the first occurrence wins. Any ambiguity is
    a lint L08 issue, not this script's concern."""
    lines = spec_text.splitlines()
    in_cc = False
    in_dt = False
    block: list[str] = []
    for line in lines:
        h2 = H2_RE.match(line)
        if h2 and not line.startswith("###"):
            in_cc = h2.group(1).strip() == "Cross-cutting constraints"
            in_dt = False
            continue
        if not in_cc:
            continue
        h3 = H3_RE.match(line)
        if h3:
            in_dt = h3.group(1).strip() == "Domain terms"
            continue
        if in_dt:
            block.append(line)
    return block


def parse_terms(block_lines: list[str]) -> list[tuple[str, list[str]]]:
    """Parse the block into (term_name, full_bullet_lines) tuples.

    A bullet starts at `- **name** —` and continues on subsequent lines
    that are indented with 2+ spaces. Blank lines and stray prose are
    ignored.

    Returns terms in encounter order; the caller dedups."""
    entries: list[tuple[str, list[str]]] = []
    current_name: str | None = None
    current_buf: list[str] = []

    def flush() -> None:
        nonlocal current_name, current_buf
        if current_name is None:
            return
        while current_buf and not current_buf[-1].strip():
            current_buf.pop()
        if current_buf:
            entries.append((current_name, list(current_buf)))
        current_name = None
        current_buf = []

    for line in block_lines:
        if not line.strip():
            # Blank line — keep within the current bullet (for spacing)
            # unless we're not in a bullet, in which case ignore.
            if current_name is not None:
                current_buf.append(line)
            continue
        m = TERM_BULLET_RE.match(line)
        if m:
            flush()
            current_name = m.group(1).strip()
            current_buf = [line]
            continue
        # Continuation: must indent with 2 spaces.
        if current_name is not None and line.startswith("  "):
            current_buf.append(line)
            continue
        # Anything else is malformed (lint L08 territory) — flush and
        # ignore the stray line.
        flush()
    flush()
    return entries


def existing_term_names(context_text: str) -> set[str]:
    """Lower-cased bold names present in CONTEXT.md (anywhere)."""
    found: set[str] = set()
    for line in context_text.splitlines():
        m = EXISTING_TERM_RE.match(line)
        if m:
            found.add(m.group(1).strip().lower())
    return found


def build_default_context() -> str:
    return (
        "# Domain Context\n"
        "\n"
        "## Language\n"
        "\n"
    )


def ensure_language_section(context_text: str) -> tuple[str, int]:
    """Return (normalised_text, insertion_line_index).

    Insertion index = where new bullets should be appended (the line
    *after* the last existing content under `## Language`, but before
    the next H2 or EOF)."""
    lines = context_text.splitlines()
    lang_idx: int | None = None
    for i, ln in enumerate(lines):
        if ln.strip() == "## Language":
            lang_idx = i
            break

    if lang_idx is None:
        # Append a fresh `## Language` block at EOF.
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("## Language")
        lines.append("")
        return "\n".join(lines) + "\n", len(lines)

    # Find next H2 (or H1) after `## Language` -> insert just before it.
    insert_at = len(lines)
    for j in range(lang_idx + 1, len(lines)):
        if lines[j].startswith("## ") or lines[j].startswith("# "):
            insert_at = j
            break
    # Trim trailing blanks immediately before the H2 so we don't pile up.
    while insert_at > lang_idx + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1
    return (
        "\n".join(lines) + ("\n" if not context_text.endswith("\n") else ""),
        insert_at,
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", default="specs/_epic/spec.md")
    ap.add_argument("--context", default="CONTEXT.md")
    args = ap.parse_args(argv)

    spec_path = Path(args.spec)
    ctx_path = Path(args.context)

    if not spec_path.exists():
        print(f"ERROR: {spec_path} not found", file=sys.stderr)
        return 1

    spec_text = spec_path.read_text(encoding="utf-8")
    block = extract_domain_terms_block(spec_text)
    terms = parse_terms(block)

    if ctx_path.exists():
        ctx_text = ctx_path.read_text(encoding="utf-8")
    else:
        ctx_text = build_default_context()

    existing = existing_term_names(ctx_text)

    appended_names: list[str] = []
    skipped_existing: list[str] = []
    skipped_dup: list[str] = []
    seen_in_batch: set[str] = set()
    new_blocks: list[str] = []

    for name, bullet_lines in terms:
        key = name.lower()
        if key in existing:
            skipped_existing.append(name)
            continue
        if key in seen_in_batch:
            skipped_dup.append(name)
            continue
        seen_in_batch.add(key)
        appended_names.append(name)
        new_blocks.append("\n".join(bullet_lines))

    if not new_blocks:
        # Idempotent no-op: write back only if we lazy-created the file.
        if not ctx_path.exists():
            ctx_path.write_text(ctx_text, encoding="utf-8")
        print(json.dumps({
            "appended": [],
            "skipped_existing": skipped_existing,
            "skipped_duplicate_in_batch": skipped_dup,
            "context_path": str(ctx_path),
        }, indent=2))
        return 0

    ctx_text, insert_at = ensure_language_section(ctx_text)
    lines = ctx_text.splitlines()
    addition: list[str] = [""]
    for block_text in new_blocks:
        addition.append(block_text)
    addition.append("")
    new_lines = lines[:insert_at] + addition + lines[insert_at:]
    ctx_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "appended": appended_names,
        "skipped_existing": skipped_existing,
        "skipped_duplicate_in_batch": skipped_dup,
        "context_path": str(ctx_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
