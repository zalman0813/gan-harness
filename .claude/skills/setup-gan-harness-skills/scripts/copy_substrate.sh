#!/usr/bin/env bash
# Copy gan-harness .claude/ tree from <src> into <dst>.
#
# Exclusions (always skipped, regardless of caller):
#   - setup-gan-harness-skills/  (this skill itself; bootstrap-only)
#   - __pycache__/               (Python compile cache)
#   - .DS_Store                  (macOS metadata)
#
# Idempotency:
#   - Refuses to overwrite an existing <dst>/.claude/. The SKILL's
#     preflight is supposed to catch this earlier; this script defends
#     anyway in case it's invoked directly.
#
# Usage:
#   copy_substrate.sh --src <gan-harness-clone> --dst <target-repo>

set -euo pipefail

SRC=""
DST=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --src) SRC="$2"; shift 2;;
    --dst) DST="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

if [[ -z "${SRC}" || -z "${DST}" ]]; then
  echo "Usage: copy_substrate.sh --src <gan-harness-clone> --dst <target-repo>" >&2
  exit 2
fi

if [[ ! -d "${SRC}/.claude" ]]; then
  echo "ERROR: ${SRC}/.claude not found — is --src really a gan-harness clone?" >&2
  exit 1
fi

if [[ -d "${DST}/.claude" ]]; then
  echo "ERROR: ${DST}/.claude already exists. Refusing to overwrite." >&2
  exit 1
fi

mkdir -p "${DST}/.claude"

# rsync gives us pattern-based exclusion + clean reporting. Fall back to
# cp + post-prune if rsync isn't available.
if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude='setup-gan-harness-skills/' \
    --exclude='__pycache__/' \
    --exclude='.DS_Store' \
    "${SRC}/.claude/" "${DST}/.claude/"
else
  cp -R "${SRC}/.claude/." "${DST}/.claude/"
  rm -rf "${DST}/.claude/skills/setup-gan-harness-skills"
  find "${DST}/.claude" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
  find "${DST}/.claude" -type f -name ".DS_Store" -delete 2>/dev/null || true
fi

# Sanity check the copy excluded the right things.
if [[ -d "${DST}/.claude/skills/setup-gan-harness-skills" ]]; then
  echo "ERROR: setup-gan-harness-skills leaked into target. Aborting." >&2
  exit 1
fi

echo "OK: copied .claude/ from ${SRC} to ${DST}"
