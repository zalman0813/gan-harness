#!/usr/bin/env python3
"""question_lint.py — validate _research/S{NN}/_questions.json before fact-finder dispatch.

Gates the per-sprint research questions drafted by MAIN session at /loop start.
Rejects questions that leak goal language, ask for design recommendations,
miss fact-form openers, contain extra schema fields, or pre-suppose where the
facts live (filename leaks).

Rules:
  Q01  no goal language (we want, we need, should, would it be good, ...)
  Q02  no design-asking verbs (recommend, suggest, propose, should ... use, ...)
  Q03  fact-form opener required (What, Which, How many, Where, Does, Is, Are)
  Q05  schema strict — only `id` / `question` / `rationale` allowed per entry;
       extra fields like `target_files` violate the blindfold (fact-finder
       discovers where facts live, never told)
  Q06  no filename pre-supposition — question text must not mention a specific
       file (e.g., `DESIGN.md`, `package.json`, `pyproject.toml`); fact-finder
       finds the file, doesn't get told

Pure stdlib. Exit 0 on PASS; exit 1 with JSON-on-stderr on FAIL.

Usage:
  question_lint.py path/to/_questions.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Q01: phrases that signal goal language / opinionated framing.
GOAL_LANGUAGE_PHRASES = [
    "we want",
    "we need",
    "we plan",
    "we intend",
    "we will",
    "we should",
    "should we",
    "is it correct to",
    "would it be good if",
    "would it make sense",
    "do we need",
    "do we want",
    "let's",
    "our goal",
    "our plan",
    "going to",
]

# Q02: phrases that ask for design / recommendation instead of facts.
# Note: "design" as a bare word is intentionally NOT here — it matches too
# broadly (e.g., "DESIGN.md" filenames). Design-asking is a verb pattern,
# not a noun.
DESIGN_ASKING_PHRASES = [
    "recommend",
    "suggest",
    "propose",
    "should ... use",
    "best way",
    "best practice",
    "what should",
    "how should",
    "approach for",
    "strategy for",
    "pattern for",
]

# Q05: only these fields are allowed per question entry. Extra fields
# (like `target_files`) leak the blindfold — fact-finder should discover
# WHERE facts live, not be told.
ALLOWED_QUESTION_FIELDS = {"id", "question", "rationale"}

# Q06: filename patterns. Question text mentioning these is pre-supposing
# where the answer lives.
FILENAME_PATTERN = re.compile(
    r"\b[A-Za-z][A-Za-z0-9_.-]*\.(md|MD|py|json|toml|yaml|yml|lock|js|ts|tsx|html|css|sql|sh|cfg|ini|env)\b"
)

# Q03: allowed fact-form openers (case-insensitive, first word check).
FACT_FORM_OPENERS = {
    "what",
    "which",
    "how",
    "where",
    "when",
    "does",
    "do",
    "is",
    "are",
    "was",
    "were",
    "has",
    "have",
    "did",
    "list",
    "name",
    "count",
    "enumerate",
}


@dataclass
class Failure:
    rule: str
    question_id: str
    message: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "rule": self.rule,
            "question_id": self.question_id,
            "message": self.message,
        }
        d.update(self.extra)
        return d


def check_q01_goal_language(text: str) -> tuple[bool, str]:
    lower = text.lower()
    for phrase in GOAL_LANGUAGE_PHRASES:
        if phrase in lower:
            return True, phrase
    return False, ""


def check_q02_design_asking(text: str) -> tuple[bool, str]:
    lower = text.lower()
    for phrase in DESIGN_ASKING_PHRASES:
        # Handle wildcard "should ... use" pattern
        if "..." in phrase:
            parts = phrase.split("...")
            if all(p.strip() in lower for p in parts):
                return True, phrase
        elif phrase in lower:
            return True, phrase
    return False, ""


def check_q03_fact_form(text: str) -> tuple[bool, str]:
    """Returns (violation, first_word) — violation True if opener is NOT fact-form."""
    words = text.strip().split()
    if not words:
        return True, ""
    first = words[0].lower().rstrip(",.?:;")
    if first not in FACT_FORM_OPENERS:
        return True, first
    return False, first


def lint(questions_data: dict[str, Any]) -> list[Failure]:
    failures: list[Failure] = []
    questions = questions_data.get("questions", [])
    if not isinstance(questions, list):
        failures.append(
            Failure(
                rule="schema",
                question_id="(root)",
                message="`questions` field must be a list",
            )
        )
        return failures

    for idx, q in enumerate(questions):
        qid = q.get("id") or f"<index {idx}>"
        text = q.get("question", "")
        if not isinstance(text, str) or not text.strip():
            failures.append(
                Failure(
                    rule="schema",
                    question_id=qid,
                    message="`question` field must be a non-empty string",
                )
            )
            continue

        # Q05: schema strict — only allowed fields
        if isinstance(q, dict):
            extra_fields = set(q.keys()) - ALLOWED_QUESTION_FIELDS
            if extra_fields:
                failures.append(
                    Failure(
                        rule="Q05",
                        question_id=qid,
                        message=f"Extra schema field(s) not allowed: {sorted(extra_fields)}. Only {sorted(ALLOWED_QUESTION_FIELDS)} are permitted. Fields like `target_files` violate the blindfold — fact-finder discovers WHERE facts live, never told.",
                        extra={"extra_fields": sorted(extra_fields)},
                    )
                )

        # Q06: no filename pre-supposition in question text
        filename_matches = FILENAME_PATTERN.findall(text)
        if filename_matches:
            # findall returns just the extension group; re-match to get full token
            full_tokens = [m.group(0) for m in FILENAME_PATTERN.finditer(text)]
            failures.append(
                Failure(
                    rule="Q06",
                    question_id=qid,
                    message=f"Question pre-supposes filename(s): {full_tokens}. Fact-finder discovers WHERE facts live. Rephrase to ask about the concept (e.g., 'What color tokens are defined for this project?'), not the file.",
                    extra={"filenames": full_tokens, "question": text},
                )
            )

        # Q01
        v, phrase = check_q01_goal_language(text)
        if v:
            failures.append(
                Failure(
                    rule="Q01",
                    question_id=qid,
                    message=f"Goal language detected: '{phrase}'. Questions must be neutral fact-finding, not opinionated framing.",
                    extra={"phrase": phrase, "question": text},
                )
            )

        # Q02
        v, phrase = check_q02_design_asking(text)
        if v:
            failures.append(
                Failure(
                    rule="Q02",
                    question_id=qid,
                    message=f"Design-asking language detected: '{phrase}'. Fact-finder documents what IS, not what SHOULD be.",
                    extra={"phrase": phrase, "question": text},
                )
            )

        # Q03
        v, first = check_q03_fact_form(text)
        if v:
            failures.append(
                Failure(
                    rule="Q03",
                    question_id=qid,
                    message=f"Question must start with a fact-form opener (What/Which/How/Where/Does/Is/Are/List/Name). Got first word: '{first}'.",
                    extra={"first_word": first, "question": text},
                )
            )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("questions_path", type=Path, help="Path to _questions.json")
    args = parser.parse_args()

    if not args.questions_path.exists():
        print(f"questions file not found: {args.questions_path}", file=sys.stderr)
        return 2
    try:
        data = json.loads(args.questions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"invalid JSON in {args.questions_path}: {e}", file=sys.stderr)
        return 2

    failures = lint(data)
    if not failures:
        print(f"PASS: {args.questions_path} ({len(data.get('questions', []))} questions)")
        return 0
    print(f"FAIL: {args.questions_path} ({len(failures)} issues)", file=sys.stderr)
    for f in failures:
        print(json.dumps(f.to_dict(), ensure_ascii=False), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
