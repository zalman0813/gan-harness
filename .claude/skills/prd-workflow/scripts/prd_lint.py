#!/usr/bin/env python3
"""Structural lint for specs/_batch/prd.md.

PASS/FAIL only. No WARN, no STRICT, no TODO.

Checks:
  L01  H1 line matches `# Batch PRD — <kebab-slug>`
  L02  At least one `## R\\d+ — <r-slug>` H2 section
  L03  Each R has ALL six required sub-sections in order:
       Problem / Solution / User Stories / Acceptance Criteria /
       Constraints / Domain terms (draft)
  L04  User Stories has at least one numbered Cohn-form line:
       `\\d+\\. As .+, I (want|need) .+,? so that .+`
  L05  Acceptance Criteria has at least one `- [ ] ` checkbox line
  L06  No forbidden top-level sections present:
       Implementation Decisions / Tech Stack / Architecture /
       Risks / Tech Debt / Timeline (case-insensitive H2 match)

Empty sub-sections must contain the literal text `_(none)_` so this
lint can verify their structure was deliberately filled.

Pure stdlib.

Usage:
  prd_lint.py <path-to-prd.md>

Exit:
  0  PASS
  1  FAIL — structural violations
  2  parse error or file not found
"""
from __future__ import annotations
import sys
import re
import argparse
from pathlib import Path


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
H1_RE = re.compile(r"^# Batch PRD — (\S.*)$")
R_HEADER_RE = re.compile(r"^## (R\d+) — (\S.*)$")
SUB_HEADER_RE = re.compile(r"^### (.+)$")
FORBIDDEN_TOP_LEVEL = {
    "implementation decisions",
    "tech stack",
    "architecture",
    "risks",
    "tech debt",
    "timeline",
}
REQUIRED_SUBS = [
    "Problem",
    "Solution",
    "User Stories",
    "Acceptance Criteria",
    "Constraints",
    "Domain terms (draft)",
]
COHN_RE = re.compile(
    r"^\s*\d+\.\s+as\s+.+?,?\s+i\s+(want|need)\s+.+?,?\s+so that\s+.+",
    re.IGNORECASE,
)
AC_CHECKBOX_RE = re.compile(r"^\s*-\s*\[\s\]\s+\S.+")
NONE_LITERAL = "_(none)_"


def parse_sections(lines: list[str]):
    """Return list of (R-id, R-slug, start_line, end_line, sub_sections).

    sub_sections is dict: header_name → list of body lines
    """
    R_idxs: list[tuple[int, str, str]] = []
    for i, ln in enumerate(lines):
        m = R_HEADER_RE.match(ln)
        if m:
            R_idxs.append((i, m.group(1), m.group(2)))

    if not R_idxs:
        return []

    R_idxs.append((len(lines), None, None))
    Rs = []
    for k in range(len(R_idxs) - 1):
        start, rid, rslug = R_idxs[k]
        end, _, _ = R_idxs[k + 1]
        body = lines[start + 1:end]
        subs: dict[str, list[str]] = {}
        cur = None
        for ln in body:
            m = SUB_HEADER_RE.match(ln)
            if m:
                cur = m.group(1).strip()
                subs[cur] = []
            elif cur is not None:
                subs[cur].append(ln)
        Rs.append({
            "id": rid,
            "slug": rslug,
            "start_line": start + 1,
            "end_line": end,
            "subs": subs,
        })
    return Rs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prd_path")
    args = ap.parse_args()

    p = Path(args.prd_path)
    if not p.is_file():
        print(f'{{"status": "ERROR", "error": "file not found: {p}"}}')
        sys.exit(2)

    text = p.read_text()
    lines = text.split("\n")
    violations: list[dict] = []

    # L01 — H1
    h1 = lines[0] if lines else ""
    m = H1_RE.match(h1)
    if not m:
        violations.append({
            "rule": "L01",
            "kind": "h1_format",
            "expected": "# Batch PRD — <kebab-slug>",
            "got": h1[:80],
        })
    else:
        slug = m.group(1).strip()
        if not SLUG_RE.match(slug):
            violations.append({
                "rule": "L01",
                "kind": "h1_slug_invalid",
                "slug": slug,
            })

    # L06 — forbidden top-level sections
    for i, ln in enumerate(lines):
        if ln.startswith("## "):
            after = ln[3:].strip().lower()
            for f in FORBIDDEN_TOP_LEVEL:
                if after == f or after.startswith(f + " ") or after.startswith(f + ":"):
                    violations.append({
                        "rule": "L06",
                        "kind": "forbidden_top_level_section",
                        "section": ln.strip(),
                        "line": i + 1,
                    })

    # Parse R sections
    Rs = parse_sections(lines)

    # L02 — at least one R
    if not Rs:
        violations.append({
            "rule": "L02",
            "kind": "no_r_sections",
        })

    for R in Rs:
        rid = R["id"]
        rslug = R["slug"]

        if not SLUG_RE.match(rslug):
            violations.append({
                "rule": "L02",
                "kind": "r_slug_invalid",
                "feature": rid,
                "slug": rslug,
            })

        # L03 — required sub-sections in order
        present = list(R["subs"].keys())
        missing = [s for s in REQUIRED_SUBS if s not in present]
        if missing:
            violations.append({
                "rule": "L03",
                "kind": "missing_subsections",
                "feature": rid,
                "missing": missing,
            })

        # check order
        present_required = [s for s in present if s in REQUIRED_SUBS]
        expected_order = [s for s in REQUIRED_SUBS if s in present]
        if present_required != expected_order:
            violations.append({
                "rule": "L03",
                "kind": "subsections_out_of_order",
                "feature": rid,
                "got_order": present_required,
                "expected_order": expected_order,
            })

        # L04 — User Stories
        us_body = R["subs"].get("User Stories", [])
        us_text = "\n".join(us_body).strip()
        if us_text and us_text != NONE_LITERAL:
            cohn_count = sum(
                1 for ln in us_body if COHN_RE.match(ln)
            )
            if cohn_count == 0:
                violations.append({
                    "rule": "L04",
                    "kind": "no_cohn_user_story",
                    "feature": rid,
                    "hint": 'expected "1. As <role>, I want <feature>, so that <benefit>"',
                })

        # L05 — Acceptance Criteria
        ac_body = R["subs"].get("Acceptance Criteria", [])
        ac_text = "\n".join(ac_body).strip()
        if ac_text and ac_text != NONE_LITERAL:
            cb_count = sum(
                1 for ln in ac_body if AC_CHECKBOX_RE.match(ln)
            )
            if cb_count == 0:
                violations.append({
                    "rule": "L05",
                    "kind": "no_ac_checkbox",
                    "feature": rid,
                    "hint": 'expected "- [ ] <claim>"',
                })

    import json
    report = {
        "status": "PASS" if not violations else "FAIL",
        "r_count": len(Rs),
        "violations": violations,
    }
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
