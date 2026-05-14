#!/usr/bin/env bash
# archive_epic.sh — v3.8 finalize Phase 4.
#
# Moves specs/_epic/ -> specs/epics/<slug>/ atomically.
#
# Usage:
#   bash ${CLAUDE_SKILL_DIR}/scripts/archive_batch.sh <epic-slug>
#
# Pre-conditions (caller's responsibility — SKILL.md Phase 0 + 1 + 2 + 3):
#   - epic_status.py --is-done returned 0
#   - finalize_adr.py promoted proposed ADRs
#   - merge_domain_terms.py merged Domain terms into CONTEXT.md
#   - regen_codemap.py refreshed CODEMAP.md
#
# Post-conditions:
#   - specs/_epic/ no longer exists
#   - specs/epics/<slug>/ contains everything that was under specs/_epic/
#     INCLUDING dotfiles (_pending/, _evals/, _traces/, .gitkeep, ...)
#   - exit 0 on success
#
# Idempotency: refuses to overwrite an existing specs/epics/<slug>/.
# The check happens BEFORE any mv, so a collision is non-destructive.

set -euo pipefail

SLUG="${1:?Usage: archive_batch.sh <epic-slug>}"
SRC="specs/_epic"
DEST="specs/epics/${SLUG}"

if [ ! -d "${SRC}" ]; then
  echo "ERROR: ${SRC}/ does not exist — nothing to archive." >&2
  exit 1
fi

if [ -e "${DEST}" ]; then
  echo "ERROR: ${DEST}/ already exists — refusing to overwrite a prior archive." >&2
  exit 1
fi

mkdir -p "$(dirname "${DEST}")"

# Use find -mindepth 1 -maxdepth 1 -exec to handle dotfiles correctly.
# This avoids the dotglob/.gitkeep failure mode that bit the Apollo run
# (see handoff D6): the previous script tried `mv specs/_batch/*` which
# silently skipped dotfiles, leaving _pending/_evals/_traces stranded.
mkdir "${DEST}"
moved=0
while IFS= read -r -d '' path; do
  mv -- "$path" "${DEST}/"
  moved=$((moved + 1))
done < <(find "${SRC}" -mindepth 1 -maxdepth 1 -print0)

rmdir "${SRC}"

echo "Archived ${moved} entries: ${SRC}/ -> ${DEST}/"
ls -1A "${DEST}"
