#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

source .venv/bin/activate

WORKFLOW_ARGS=()
if [[ -n "${WORKFLOWS:-}" ]]; then
  WORKFLOW_ARGS=(--workflows "$WORKFLOWS")
fi

if [[ "${BOOTSTRAP_DEMO:-0}" == "1" ]]; then
  ./tmp/docs/bootstrap_demo.sh
fi

if [[ "${CAPTURE_SCREENSHOTS:-0}" == "1" ]]; then
  if [[ -n "${WORKFLOWS:-}" ]]; then
    node tmp/docs/capture_user_flow_screenshots.js --workflows "$WORKFLOWS"
  else
    node tmp/docs/capture_user_flow_screenshots.js
  fi
fi

if [[ ${#WORKFLOW_ARGS[@]} -gt 0 ]]; then
  python tmp/docs/generate_user_flow_docs.py "${WORKFLOW_ARGS[@]}"
  python tmp/docs/generate_user_flow_decks.py "${WORKFLOW_ARGS[@]}"
else
  python tmp/docs/generate_user_flow_docs.py
  python tmp/docs/generate_user_flow_decks.py
fi

if [[ "${REBUILD_INDEX:-1}" == "1" ]]; then
  python tmp/docs/generate_master_index_deck.py
fi

python tmp/docs/verify_user_flow_pack.py

if [[ "${RUN_QA_RENDER:-1}" == "1" ]]; then
  ./tmp/docs/render_user_flow_pack.sh
  python tmp/docs/verify_user_flow_pack.py
fi

if [[ "${RUN_NAV_AUDIT:-0}" == "1" ]]; then
  node tmp/docs/check_user_flow_navigation.js
fi

echo "User-flow pack build complete."
