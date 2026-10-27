#!/usr/bin/env bash
# Push the typography-fidelity project to GitHub via the Git Data API
# helper (~/workspace/custom-connectors/custom.github/bin/gh_push.py).
#
# Prerequisites (both must be true before running):
#   1. The repository exists on GitHub (created via the web UI, because
#      the fine-grained token cannot create repositories: API returns 403).
#   2. The repository has been added to the fine-grained token's selected
#      repositories with Contents read/write, otherwise the API returns 403.
#      (Same step Noorullah did for Car_Project on 2026-10-22.)
#
# Usage: ./scripts/push_to_github.sh [branch]
# Branch defaults to main. The script stops on the first failed commit.
# It never touches any other repository.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OWNER="NoorullahZamindar-007"
REPO="typography-fidelity"
BRANCH="${1:-main}"
GH="$HOME/workspace/custom-connectors/custom.github/bin/gh_push.py"

push() {
  echo "--- $1"
  shift
  local msg="$1"; shift
  local abs=()
  for f in "$@"; do abs+=("$ROOT/$f"); done
  python3 "$GH" "$OWNER" "$REPO" "$BRANCH" "$msg" "${abs[@]}"
}

cd "$ROOT"
push "code, docs, config, data" "Code and docs" \
  README.md config.json requirements.txt .gitignore \
  data/prompts.json \
  src/generate.py src/evaluate.py src/verify.py src/figures.py \
  src/build_manuscript.py src/make_evaluation_sheet.py src/merge_scores.py \
  src/ocr_check.py src/second_pass.py \
  docs/evaluation-protocol.md docs/references.bib docs/ocr-crosscheck.md

push "results (manifest, evaluation, ocr)" "Results" \
  results/manifest.csv results/evaluation.csv results/scores.json results/ocr.csv

# Images in batches of 20 (keeps each tree commit small).
i=0
batch=()
for f in images/*.webp; do
  batch+=("$f")
  i=$((i + 1))
  if [ "$i" -eq 20 ]; then
    push "images batch" "Images batch" "${batch[@]}"
    batch=(); i=0
  fi
done
if [ "${#batch[@]}" -gt 0 ]; then
  push "images batch (final)" "Images batch" "${batch[@]}"
fi
echo "done"
