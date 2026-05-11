#!/usr/bin/env bash
# Archive a completed batch into specs/completed/{slug}/.
#
# Usage:
#   bash ${CLAUDE_SKILL_DIR}/scripts/archive_batch.sh <slug>
#
# Pre-conditions (caller's responsibility):
#   - preflight.py validated the batch is ready
#   - finalize_adr.py promoted proposed → accepted ADRs
#   - merge_domain_terms.py merged Domain terms into CONTEXT.md
#   - regen_codemap.py refreshed CODEMAP.md
#   - summarize_batch.py wrote specs/_batch/BATCH_SUMMARY.md (this script
#     moves it into the archive along with everything else under _batch/)
#
# Post-conditions:
#   - specs/_batch/ contains only .gitkeep
#   - specs/completed/{slug}/ contains every artefact that was under
#     specs/_batch/ at invocation time
#
# Idempotency: refuses to overwrite an existing specs/completed/{slug}/.

set -euo pipefail

SLUG="${1:?Usage: archive_batch.sh <slug>}"
DEST="specs/completed/${SLUG}"

if [ -e "${DEST}" ]; then
  echo "ERROR: ${DEST} already exists — refusing to overwrite a prior archive." >&2
  exit 1
fi

if [ ! -d "specs/_batch" ]; then
  echo "ERROR: specs/_batch/ does not exist — nothing to archive." >&2
  exit 1
fi

mkdir -p "${DEST}"

shopt -s dotglob nullglob
moved=0
for path in specs/_batch/*; do
  base="$(basename "$path")"
  [ "${base}" = ".gitkeep" ] && continue
  mv -- "$path" "${DEST}/"
  moved=$((moved + 1))
done
shopt -u dotglob nullglob

touch specs/_batch/.gitkeep

echo "Archived ${moved} entries to ${DEST}/"
ls -1 "${DEST}/"
