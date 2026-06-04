#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PE_SERVICE_HOST="${PE_SERVICE_HOST:-127.0.0.1}"
export PE_SERVICE_PORT="${PE_SERVICE_PORT:-3007}"
export PE_SERVICE_URL="${PE_SERVICE_URL:-http://${PE_SERVICE_HOST}:${PE_SERVICE_PORT}}"
export APP_BASE_URL="${APP_BASE_URL:-$PE_SERVICE_URL}"
export PUBLIC_BASE_URL="${PUBLIC_BASE_URL:-$PE_SERVICE_URL}"
export INCLINIC_SERVICE_URL="${INCLINIC_SERVICE_URL:-http://127.0.0.1:3005}"
export RFA_SERVICE_URL="${RFA_SERVICE_URL:-http://127.0.0.1:3006}"

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="$(command -v python3)"
fi

exec "$PYTHON_BIN" manage.py runserver "${PE_SERVICE_HOST}:${PE_SERVICE_PORT}" --noreload
