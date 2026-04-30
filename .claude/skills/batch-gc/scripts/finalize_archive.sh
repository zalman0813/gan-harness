#!/usr/bin/env bash
# Archive a completed batch into specs/completed/{slug}/.
#
# Usage:
#   bash ${CLAUDE_SKILL_DIR}/scripts/finalize_archive.sh <slug>
#
# This script assumes:
#   - preflight.py has already validated the batch is ready
#   - summarize_progress.py has already produced BATCH_SUMMARY.md (or will after this run)
#   - Phase 1 (Dreamer Review) has already rewritten the DREAM-*.md files
#     with their "Applied" audit footer
#
# After this script:
#   - specs/_batch/ is empty (only .gitkeep)
#   - docs/progress/ is empty (only .gitkeep)
#   - specs/completed/{slug}/ contains all batch artifacts

set -euo pipefail

SLUG="${1:?Usage: finalize_archive.sh <slug>}"
DEST="specs/completed/${SLUG}"

if [ -e "${DEST}" ]; then
  echo "ERROR: ${DEST} already exists — refusing to overwrite a prior archive." >&2
  exit 1
fi

mkdir -p "${DEST}"

# 1. Move spec artifacts from specs/_batch/
if [ -d "specs/_batch" ]; then
  shopt -s dotglob nullglob
  # Move every non-.gitkeep file/dir inside specs/_batch to dest
  for path in specs/_batch/*; do
    [ "$(basename "$path")" = ".gitkeep" ] && continue
    mv -- "$path" "${DEST}/"
  done
  shopt -u dotglob nullglob
fi

# 2. Move feature-list.json
if [ -f "docs/feature-list.json" ]; then
  mv docs/feature-list.json "${DEST}/feature-list.json"
fi

# 3. Move DREAM-*.md (must already include the Applied footer)
for f in DREAM-gen.md DREAM-eval.md; do
  if [ -f "docs/progress/${f}" ]; then
    mv "docs/progress/${f}" "${DEST}/${f}"
  fi
done

# 4. Move .traces/ if any — preserves the raw trace stream
if [ -d "docs/progress/.traces" ]; then
  if find docs/progress/.traces -mindepth 1 -print -quit | grep -q .; then
    mkdir -p "${DEST}/traces"
    mv docs/progress/.traces/* "${DEST}/traces/"
  fi
  rmdir docs/progress/.traces 2>/dev/null || true
fi

# 5. Delete raw per-feature progress/eval/trace files — they are
#    summarized (by summarize_progress.py) into BATCH_SUMMARY.md before this
#    script runs, so deletion is safe.
git rm -f docs/progress/F*-progress-R*.md 2>/dev/null || true
git rm -f docs/progress/F*-eval-R*.md 2>/dev/null || true
git rm -f docs/progress/F*-gen-trace-R*.md 2>/dev/null || true
git rm -f docs/progress/F*-eval-trace-R*.md 2>/dev/null || true
git rm -f docs/progress/F*-contract.md 2>/dev/null || true
# Any stragglers (non-git-tracked) — remove from disk too.
rm -f docs/progress/F*-progress-R*.md \
      docs/progress/F*-eval-R*.md \
      docs/progress/F*-gen-trace-R*.md \
      docs/progress/F*-eval-trace-R*.md \
      docs/progress/F*-contract.md 2>/dev/null || true

# 6. Re-create empty sentinels for next batch
mkdir -p docs/progress specs/_batch
touch docs/progress/.gitkeep specs/_batch/.gitkeep

echo "Archived to ${DEST}/"
ls "${DEST}/"
