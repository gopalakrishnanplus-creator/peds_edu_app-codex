#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d ".venv" ]]; then
  echo "Missing .venv. Create it first with: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt python-pptx pypdf" >&2
  exit 1
fi

set -a
source "$ROOT_DIR/tmp/docs/demo.env"
set +a

mysql -uroot <<SQL
DROP DATABASE IF EXISTS \`${DB_NAME}\`;
DROP DATABASE IF EXISTS \`${MASTER_DB_NAME}\`;

CREATE DATABASE \`${DB_NAME}\`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
CREATE DATABASE \`${MASTER_DB_NAME}\`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';

GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'127.0.0.1';
GRANT ALL PRIVILEGES ON \`${MASTER_DB_NAME}\`.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${MASTER_DB_NAME}\`.* TO '${DB_USER}'@'127.0.0.1';
FLUSH PRIVILEGES;
SQL

source "$ROOT_DIR/.venv/bin/activate"

python manage.py migrate contenttypes --noinput
python manage.py migrate auth --noinput
python manage.py migrate sessions --noinput
python manage.py migrate --run-syncdb --noinput
python manage.py migrate admin --noinput
python manage.py import_master_data --path "$ROOT_DIR/CSV"
python "$ROOT_DIR/tmp/docs/seed_demo_data.py"

echo "Demo environment is ready."
