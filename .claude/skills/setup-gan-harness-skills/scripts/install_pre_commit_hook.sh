#!/usr/bin/env bash
# install_pre_commit_hook.sh — copy templates/pre-commit into the target's
# .git/hooks/pre-commit (single self-contained Python file). Every
# `git commit` thereafter runs the gate during a live generator round.
#
# Usage: install_pre_commit_hook.sh <target-dir>
#
# Behaviour:
#   - target/.git missing  → exit 1 (target is not a git repo)
#   - hook absent          → install + chmod +x  → exit 0
#   - hook already present → exit 2 with diff hint (operator reconciles)
set -euo pipefail

TARGET="${1:?usage: install_pre_commit_hook.sh <target-dir>}"
HOOK="$TARGET/.git/hooks/pre-commit"
TEMPLATE_DIR="$(cd "$(dirname "$0")/.." && pwd)/templates"
TEMPLATE="$TEMPLATE_DIR/pre-commit"

if [ ! -d "$TARGET/.git" ]; then
  echo "ERROR: $TARGET is not a git repository (no .git/ directory)" >&2
  exit 1
fi
if [ ! -f "$TEMPLATE" ]; then
  echo "ERROR: template missing at $TEMPLATE" >&2
  exit 1
fi

if [ -e "$HOOK" ]; then
  echo "ERROR: $HOOK already exists." >&2
  echo "       Manual reconciliation required — diff against template:" >&2
  echo "       diff $HOOK $TEMPLATE" >&2
  exit 2
fi

mkdir -p "$TARGET/.git/hooks"
cp "$TEMPLATE" "$HOOK"
chmod +x "$HOOK"
echo "Installed pre-commit hook at $HOOK"
