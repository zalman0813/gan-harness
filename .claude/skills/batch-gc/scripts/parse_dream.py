#!/usr/bin/env python3
"""Parse a DREAM-*.md proposal list into structured JSON.

Usage:
    python3 parse_dream.py <path-to-DREAM-gen.md|DREAM-eval.md>

Output (stdout, JSON):
    {
      "source": "docs/progress/DREAM-gen.md",
      "gate_status": {
        "dormant_pct": 44.4,
        "threshold": 30,
        "gate_tripped": true
      },
      "proposals": [
        {
          "id": "P-01",
          "category": "create-recipe",
          "title": "<title-after-category>",
          "body": "<raw markdown body, up to next ### or ##>"
        },
        ...
      ],
      "trends": "<Batch Trends section body>",
      "recommendations": "<Recommendations for Next Batch body>"
    }

The skill layer parses `body` per-category; this script stays dumb on
purpose — it's a splitter, not a semantic understander.

Exit 0 on success; exit 1 if the file is malformed (no Proposals
heading, unparsable proposal IDs, etc.).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROPOSAL_HEADER_RE = re.compile(
    r"^###\s+(?P<pid>P-\d{2,3})\s+\[(?P<category>[a-z-]+)\]\s*(?P<title>.*)$"
)
GATE_FIELD_RE = re.compile(r"^-\s+(?P<key>[a-z_]+):\s+(?P<value>.+)\s*$")


def split_sections(lines: list[str]) -> dict[str, list[str]]:
    """Split by H2 (`## Heading`). Returns {heading: body_lines}."""
    sections: dict[str, list[str]] = {}
    current_heading: str | None = None
    current_body: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current_heading is not None:
                sections[current_heading] = current_body
            current_heading = line[3:].strip()
            current_body = []
        else:
            current_body.append(line)
    if current_heading is not None:
        sections[current_heading] = current_body
    return sections


def parse_proposals(body: list[str]) -> list[dict]:
    """Within the `## Proposals` body, split by H3 proposal headers."""
    proposals: list[dict] = []
    current: dict | None = None
    current_body: list[str] = []
    for line in body:
        m = PROPOSAL_HEADER_RE.match(line.rstrip())
        if m:
            if current is not None:
                current["body"] = "".join(current_body).rstrip() + "\n"
                proposals.append(current)
            current = {
                "id": m.group("pid"),
                "category": m.group("category"),
                "title": m.group("title").strip(),
            }
            current_body = []
        else:
            if current is not None:
                current_body.append(line)
    if current is not None:
        current["body"] = "".join(current_body).rstrip() + "\n"
        proposals.append(current)
    return proposals


def parse_gate_status(body: list[str]) -> dict:
    """Parse `## Gate Status` body into {dormant_pct, threshold, gate_tripped}."""
    out: dict = {}
    for line in body:
        m = GATE_FIELD_RE.match(line.rstrip())
        if not m:
            continue
        key, value = m.group("key"), m.group("value").strip()
        if key == "dormant_pct":
            # Strip "%" if present
            try:
                out["dormant_pct"] = float(value.rstrip("%"))
            except ValueError:
                out["dormant_pct"] = None
        elif key == "threshold":
            try:
                out["threshold"] = float(value.rstrip("%"))
            except ValueError:
                out["threshold"] = None
        elif key == "gate_tripped":
            out["gate_tripped"] = value.lower() in ("true", "yes")
    return out


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: parse_dream.py <path-to-DREAM-*.md>", file=sys.stderr)
        return 1
    path = Path(argv[0])
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        return 1

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    sections = split_sections(lines)

    if "Proposals" not in sections:
        print(f"ERROR: {path} has no `## Proposals` section", file=sys.stderr)
        return 1

    proposals = parse_proposals(sections["Proposals"])
    gate_status = parse_gate_status(sections.get("Gate Status", []))

    out = {
        "source": str(path),
        "gate_status": gate_status,
        "proposals": proposals,
        "trends": "".join(sections.get("Batch Trends", [])).strip(),
        "recommendations": "".join(
            sections.get("Recommendations for Next Batch", [])
        ).strip(),
    }

    json.dump(out, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
