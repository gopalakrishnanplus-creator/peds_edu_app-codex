#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="$ROOT/output/doc/user-flow-decks"
QA="$OUT/qa-previews"
PDF_DIR="$QA/pdf"
PNG_DIR="$QA/png"

mkdir -p "$PDF_DIR" "$PNG_DIR"
find "$PDF_DIR" -type f -name '*.pdf' -delete
find "$PNG_DIR" -type f -name '*.png' -delete

DECKS=()
if [[ -n "${WORKFLOWS:-}" ]]; then
  while IFS= read -r deck_name; do
    [[ -n "$deck_name" ]] || continue
    DECKS+=("$OUT/$deck_name")
  done < <(
    ROOT_DIR="$ROOT" python3 <<'PY'
import os
import sys

ROOT = os.environ["ROOT_DIR"]
TMP_DOCS = os.path.join(ROOT, "tmp", "docs")
if TMP_DOCS not in sys.path:
    sys.path.insert(0, TMP_DOCS)

from user_flow_pack_data import select_workflows  # type: ignore

for workflow in select_workflows(os.getenv("WORKFLOWS")):
    print(workflow.deck_filename)

if os.getenv("REBUILD_INDEX", "1") == "1":
    print("00-user-flow-training-index.pptx")
PY
  )
  if [[ ${#DECKS[@]} -eq 0 ]]; then
    DECKS=("$OUT"/*.pptx)
  fi
else
  DECKS=("$OUT"/*.pptx)
fi

for deck in "${DECKS[@]}"; do
  [[ -f "$deck" ]] || continue
  soffice --headless --convert-to pdf --outdir "$PDF_DIR" "$deck" >/dev/null
done

for pdf in "$PDF_DIR"/*.pdf; do
  base="$(basename "$pdf" .pdf)"
  pdftoppm -png "$pdf" "$PNG_DIR/$base" >/dev/null
done

echo "Rendered QA previews into $QA"
