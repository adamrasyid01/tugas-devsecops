#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."
source scripts/lib.sh
load_env
mkdir -p reports

docker compose ps >reports/compose-ps.txt
curl -fsS http://127.0.0.1:2020/api/v1/metrics >reports/fluent-bit-metrics.json

docker compose exec -T app-db psql \
    --username "$APP_DB_ADMIN_USER" --dbname "$APP_DB_NAME" \
    --command='SELECT public_id, status, attempt, failure_code, request_id, updated_at FROM registrations ORDER BY submitted_at;' \
    >reports/registration-status.txt

docker compose exec -T log-db psql \
    --username "$LOG_DB_ADMIN_USER" --dbname "$LOG_DB_NAME" \
    --file=/dev/stdin <queries/incident-analysis.sql \
    >reports/incident-analysis.txt

sha256sum compose.yaml app/*.py app/requirements.txt fluent-bit/fluent-bit.conf \
    init-app/01-init-app.sh init-log/01-init-log.sh queries/incident-analysis.sql \
    >reports/config-sha256.txt

echo "[PASS] Evidence dibuat di direktori reports/. File .env tidak disertakan."
