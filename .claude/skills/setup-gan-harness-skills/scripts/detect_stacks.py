#!/usr/bin/env python3
"""Detect language/framework stacks in a target repo by scanning for
known manifest files. Output is consumed by SKILL.md Section D to drive
per-stack chain-calls of stack-skill-creator.

We deliberately keep detection coarse: the goal is to suggest a sensible
stack-skill name, not to lock the user in. They can rename or skip each
suggestion.

Usage:
  detect_stacks.py --target <path>

Output: JSON list to stdout.
  [
    {"manifest": "pyproject.toml", "suggested_skill_name": "python-fastapi",
     "evidence": "fastapi in dependencies"},
    {"manifest": "package.json", "suggested_skill_name": "typescript-nextjs",
     "evidence": "next in dependencies"}
  ]

Exit:
  0 always (empty list is valid; user picks "skip" in SKILL Section D)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def detect_python(target: Path) -> dict | None:
    """pyproject.toml or requirements*.txt → infer framework from deps."""
    pyproject = target / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(errors="ignore").lower()
        if "fastapi" in text:
            return {
                "manifest": "pyproject.toml",
                "suggested_skill_name": "python-fastapi",
                "evidence": "fastapi referenced in pyproject.toml",
            }
        if "django" in text:
            return {
                "manifest": "pyproject.toml",
                "suggested_skill_name": "python-django",
                "evidence": "django referenced in pyproject.toml",
            }
        if "flask" in text:
            return {
                "manifest": "pyproject.toml",
                "suggested_skill_name": "python-flask",
                "evidence": "flask referenced in pyproject.toml",
            }
        return {
            "manifest": "pyproject.toml",
            "suggested_skill_name": "python",
            "evidence": "pyproject.toml present (no framework heuristic matched)",
        }

    for req in ("requirements.txt", "requirements-dev.txt"):
        rp = target / req
        if rp.is_file():
            text = rp.read_text(errors="ignore").lower()
            if "fastapi" in text:
                return {"manifest": req, "suggested_skill_name": "python-fastapi",
                        "evidence": f"fastapi in {req}"}
            if "django" in text:
                return {"manifest": req, "suggested_skill_name": "python-django",
                        "evidence": f"django in {req}"}
            return {"manifest": req, "suggested_skill_name": "python",
                    "evidence": f"{req} present"}
    return None


def detect_js_ts(target: Path) -> dict | None:
    pkg = target / "package.json"
    if not pkg.is_file():
        return None
    text = pkg.read_text(errors="ignore").lower()

    if '"next"' in text:
        # Next.js — TS or JS?
        is_ts = (target / "tsconfig.json").is_file() or '"typescript"' in text
        name = "typescript-nextjs" if is_ts else "javascript-nextjs"
        return {"manifest": "package.json", "suggested_skill_name": name,
                "evidence": f"next in package.json ({'TS' if is_ts else 'JS'})"}
    if '"react"' in text:
        is_ts = (target / "tsconfig.json").is_file() or '"typescript"' in text
        name = "typescript-react" if is_ts else "javascript-react"
        return {"manifest": "package.json", "suggested_skill_name": name,
                "evidence": f"react in package.json ({'TS' if is_ts else 'JS'})"}
    if '"express"' in text:
        return {"manifest": "package.json", "suggested_skill_name": "javascript-express",
                "evidence": "express in package.json"}

    # Generic fallback
    is_ts = (target / "tsconfig.json").is_file() or '"typescript"' in text
    return {"manifest": "package.json",
            "suggested_skill_name": "typescript" if is_ts else "javascript",
            "evidence": f"package.json present ({'TS' if is_ts else 'JS'})"}


def detect_rust(target: Path) -> dict | None:
    if (target / "Cargo.toml").is_file():
        return {"manifest": "Cargo.toml", "suggested_skill_name": "rust",
                "evidence": "Cargo.toml present"}
    return None


def detect_go(target: Path) -> dict | None:
    gomod = target / "go.mod"
    if not gomod.is_file():
        return None
    text = gomod.read_text(errors="ignore").lower()
    if "github.com/gin-gonic/gin" in text:
        return {"manifest": "go.mod", "suggested_skill_name": "go-gin",
                "evidence": "gin in go.mod"}
    if "github.com/labstack/echo" in text:
        return {"manifest": "go.mod", "suggested_skill_name": "go-echo",
                "evidence": "echo in go.mod"}
    return {"manifest": "go.mod", "suggested_skill_name": "go",
            "evidence": "go.mod present"}


def detect_dart(target: Path) -> dict | None:
    pubspec = target / "pubspec.yaml"
    if not pubspec.is_file():
        return None
    text = pubspec.read_text(errors="ignore").lower()
    if re.search(r"^\s*flutter:", text, re.MULTILINE):
        return {"manifest": "pubspec.yaml", "suggested_skill_name": "dart-flutter",
                "evidence": "flutter section in pubspec.yaml"}
    return {"manifest": "pubspec.yaml", "suggested_skill_name": "dart",
            "evidence": "pubspec.yaml present"}


def detect_ruby(target: Path) -> dict | None:
    gemfile = target / "Gemfile"
    if not gemfile.is_file():
        return None
    text = gemfile.read_text(errors="ignore").lower()
    if "rails" in text:
        return {"manifest": "Gemfile", "suggested_skill_name": "ruby-rails",
                "evidence": "rails in Gemfile"}
    return {"manifest": "Gemfile", "suggested_skill_name": "ruby",
            "evidence": "Gemfile present"}


def detect_php(target: Path) -> dict | None:
    composer = target / "composer.json"
    if not composer.is_file():
        return None
    text = composer.read_text(errors="ignore").lower()
    if "laravel/framework" in text:
        return {"manifest": "composer.json", "suggested_skill_name": "php-laravel",
                "evidence": "laravel/framework in composer.json"}
    return {"manifest": "composer.json", "suggested_skill_name": "php",
            "evidence": "composer.json present"}


DETECTORS = (detect_python, detect_js_ts, detect_rust, detect_go,
             detect_dart, detect_ruby, detect_php)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    args = ap.parse_args()

    target = Path(args.target).resolve()
    results = []
    for fn in DETECTORS:
        try:
            r = fn(target)
        except Exception as exc:
            print(f"WARN: {fn.__name__} raised {exc}", file=sys.stderr)
            continue
        if r:
            results.append(r)

    json.dump(results, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
