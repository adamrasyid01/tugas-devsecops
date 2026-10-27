#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."
source scripts/lib.sh
load_env

docker compose ps
wait_http "Fluent Bit" "http://127.0.0.1:2020/api/v1/health"
wait_http "Portal PMB" "http://127.0.0.1:8080/healthz"

app_rows="$(docker compose exec -T app-db psql \
    --username "$APP_DB_ADMIN_USER" --dbname "$APP_DB_NAME" \
    --tuples-only --no-align --command='SELECT count(*) FROM registrations;')"
log_rows="$(docker compose exec -T log-db psql \
    --username "$LOG_DB_ADMIN_USER" --dbname "$LOG_DB_NAME" \
    --tuples-only --no-align --command='SELECT count(*) FROM logs.fluentbit;')"

echo "[INFO] Pendaftaran: $app_rows"
echo "[INFO] Record log: $log_rows"

if (( app_rows < 1 )); then
    echo "[FAIL] Belum ada transaksi. Jalankan make normal dan make incident." >&2
    exit 1
fi
if (( log_rows < 1 )); then
    echo "[FAIL] Belum ada log terpusat." >&2
    exit 1
fi

suspicious="$(docker compose exec -T log-db psql \
    --username "$LOG_DB_ADMIN_USER" --dbname "$LOG_DB_NAME" \
    --tuples-only --no-align \
    --command="SELECT count(*) FROM logs.fluentbit WHERE data ->> 'log' ~* '(password|authorization|bearer|cookie|session[_-]?secret|api[_-]?key)';")"
if (( suspicious > 0 )); then
    echo "[FAIL] Ditemukan $suspicious log yang memerlukan review secret." >&2
    exit 1
fi

echo "[PASS] Service sehat, transaksi tersedia, log tersimpan, dan pemeriksaan secret bersih."
