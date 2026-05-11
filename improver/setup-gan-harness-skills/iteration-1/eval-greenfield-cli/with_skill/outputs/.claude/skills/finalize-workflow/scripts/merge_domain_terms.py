#!/usr/bin/env python3
"""Merge `### Domain terms (draft)` blocks from specs/_batch/prd.md into
the project root CONTEXT.md `## Language` section.

PRD format (per .claude/skills/prd-workflow/references/grill-protocol.md
§ Output format):

  ## R1 — <r-slug>
  ...
  ### Domain terms (draft)
  **TermName**:
  <one-sentence definition>
  _Avoid_: <synonym1>, <synonym2>

  ## R2 — <r-slug>
  ### Domain terms (draft)
  **OtherTerm**:
  ...

CONTEXT.md format (per CONTEXT.md § Language already in repo):

  ## Language

  **TermName**:
  <one-sentence definition>
  _Avoid_: <synonym1>, <synonym2>

  **OtherTerm**:
  ...

Behaviour:
  - dedupe by **bold term name** across R sections (first occurrence wins)
  - skip any term whose name already exists in CONTEXT.md (case-insensitive
    equality on the bold-name slot) — never overwrite an existing entry
  - lazy-create CONTEXT.md (with H1 + ## Language stub) if missing
  - lazy-create the `## Language` section if CONTEXT.md exists but lacks it
  - emit JSON-line summary to stdout: appended count + skipped term names

The script does NOT prompt — the SKILL is responsible for any user
review before invoking this. This script is the deterministic merger.

Usage:
  merge_domain_terms.py [--prd specs/_batch/prd.md] [--context CONTEXT.md]

Exit:
  0 OK
  1 IO / parse error
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ### Domain terms (draft)  →  the literal heading we look for under each R
DOMAIN_HEADING_RE = re.compile(r"^###\s+Domain\s+terms\s+\(draft\)\s*$")

# **TermName**:  →  bold name on its own line ending with a colon
TERM_NAME_RE = re.compile(r"^\*\*([^*]+?)\*\*:\s*$")

# Section breaks inside prd.md. We stop a Domain-terms block at the next
# H2 (## ...) or H3 (### ...) heading.
SECTION_BREAK_RE = re.compile(r"^##\s|^###\s")


def parse_prd_terms(prd_text: str) -> list[tuple[str, list[str]]]:
    """Walk prd.md, collect every (term_name, term_block_lines) tuple in
    encounter order across all R sections. Skips literal `_(none)_`
    placeholder blocks. Within a block the term spans from the bold name
    line to the next blank-line-terminated paragraph break."""
    lines = prd_text.splitlines()
    out: list[tuple[str, list[str]]] = []

    i = 0
    while i < len(lines):
        if not DOMAIN_HEADING_RE.match(lines[i]):
            i += 1
            continue

        # We're inside a Domain-terms block. Walk until the next H2/H3.
        i += 1
        block_lines: list[str] = []
        while i < len(lines) and not SECTION_BREAK_RE.match(lines[i]):
            block_lines.append(lines[i])
            i += 1
        # block_lines now holds everything under the Domain-terms heading
        # for this R. Parse it into individual term entries.
        out.extend(_split_terms(block_lines))

    return out


def _split_terms(block_lines: list[str]) -> list[tuple[str, list[str]]]:
    """Split a Domain-terms block into per-term entries.

    Each term entry starts at a `**Name**:` line and runs until the next
    `**Name**:` line or end of block. Trailing blank lines are trimmed."""
    entries: list[tuple[str, list[str]]] = []
    current_name: str | None = None
    current_buf: list[str] = []

    def flush() -> None:
        if current_name is None:
            return
        # Trim trailing blank lines
        while current_buf and not current_buf[-1].strip():
            current_buf.pop()
        if current_buf:
            entries.append((current_name, list(current_buf)))

    for line in block_lines:
        if line.strip() == "_(none)_":
            # Skip the placeholder marker entirely.
            continue
        m = TERM_NAME_RE.match(line)
        if m:
            flush()
            current_name = m.group(1).strip()
            current_buf = [line]
        elif current_name is not None:
            current_buf.append(line)
        # else: stray prose before the first term — ignore.

    flush()
    return entries


def existing_term_names(context_text: str) -> set[str]:
    """Lower-cased term names already present anywhere in CONTEXT.md."""
    found: set[str] = set()
    for line in context_text.splitlines():
        m = TERM_NAME_RE.match(line)
        if m:
            found.add(m.group(1).strip().lower())
    return found


def ensure_language_section(context_text: str) -> tuple[str, int]:
    """Return (context_text_with_language_section, insertion_index).

    insertion_index = the line index where new term blocks should be
    appended (i.e. just before the next H2 after `## Language`, or at EOF
    if `## Language` is the last H2)."""
    lines = context_text.splitlines()

    # Find ## Language
    lang_idx = next(
        (i for i, ln in enumerate(lines) if ln.strip() == "## Language"),
        None,
    )

    if lang_idx is None:
        # Append a fresh `## Language` section at EOF.
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("## Language")
        lines.append("")
        return "\n".join(lines) + "\n", len(lines)

    # Find the next H2 (or H1) after lang_idx — insert before it.
    insert_at = len(lines)
    for j in range(lang_idx + 1, len(lines)):
        if lines[j].startswith("## ") or lines[j].startswith("# "):
            insert_at = j
            break

    # Trim trailing blanks immediately before insert_at so we don't pile
    # up blank lines.
    while insert_at > lang_idx + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1

    return "\n".join(lines) + ("\n" if not context_text.endswith("\n") else ""), insert_at


def build_default_context() -> str:
    return (
        "# Context\n"
        "\n"
        "_Auto-stub created by merge_domain_terms.py on first /finalize._\n"
        "Edit freely — subsequent /finalize runs only append new Domain "
        "terms under `## Language`.\n"
        "\n"
        "## Language\n"
        "\n"
    )


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prd", default="specs/_batch/prd.md")
    ap.add_argument("--context", default="CONTEXT.md")
    args = ap.parse_args(argv)

    prd_path = Path(args.prd)
    ctx_path = Path(args.context)

    if not prd_path.exists():
        print(f"ERROR: {prd_path} not found", file=sys.stderr)
        return 1

    prd_text = prd_path.read_text(encoding="utf-8")
    terms = parse_prd_terms(prd_text)

    if ctx_path.exists():
        ctx_text = ctx_path.read_text(encoding="utf-8")
    else:
        ctx_text = build_default_context()

    existing = existing_term_names(ctx_text)

    appended: list[str] = []
    skipped_existing: list[str] = []
    skipped_dup: list[str] = []
    seen_in_batch: set[str] = set()

    new_blocks: list[str] = []
    for name, block in terms:
        key = name.lower()
        if key in existing:
            skipped_existing.append(name)
            continue
        if key in seen_in_batch:
            skipped_dup.append(name)
            continue
        seen_in_batch.add(key)
        appended.append(name)
        new_blocks.append("\n".join(block))

    if not new_blocks:
        # Still ensure `## Language` exists if CONTEXT.md was missing —
        # but only write back if we actually changed anything.
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

    addition: list[str] = []
    for block in new_blocks:
        addition.append("")
        addition.append(block)
    addition.append("")

    new_lines = lines[:insert_at] + addition + lines[insert_at:]
    ctx_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

    print(json.dumps({
        "appended": appended,
        "skipped_existing": skipped_existing,
        "skipped_duplicate_in_batch": skipped_dup,
        "context_path": str(ctx_path),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
