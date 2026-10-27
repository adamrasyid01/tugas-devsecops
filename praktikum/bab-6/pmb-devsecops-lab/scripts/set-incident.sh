#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."
source scripts/lib.sh
load_env

mode="${1:-}"
case "$mode" in
    none|timeout) ;;
    *) echo "Penggunaan: $0 {none|timeout}" >&2; exit 2 ;;
esac

docker compose exec -T app-db \
    psql --set=ON_ERROR_STOP=1 \
    --username "$APP_DB_ADMIN_USER" \
    --dbname "$APP_DB_NAME" \
    --set=mode="$mode" <<'SQL'
UPDATE lab_control
SET value = :'mode', updated_at = CURRENT_TIMESTAMP
WHERE key = 'incident_mode';
TABLE lab_control;
SQL

echo "[PASS] Mode insiden: $mode"
