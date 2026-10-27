#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."
source scripts/lib.sh
load_env

wait_http "Portal PMB" "http://127.0.0.1:8080/healthz"
./scripts/set-incident.sh none >/dev/null
request_id="$(submit_application NORMAL)"
echo "[INFO] Request ID: $request_id"
sleep 5

docker compose exec -T app-db psql \
    --username "$APP_DB_ADMIN_USER" --dbname "$APP_DB_NAME" \
    --set=request_id="$request_id" <<'SQL'
SELECT public_id, status, attempt, failure_code, request_id
FROM registrations
WHERE request_id = :'request_id';
SQL

echo "[PASS] Demo normal selesai. Status yang diharapkan: VERIFIED."
