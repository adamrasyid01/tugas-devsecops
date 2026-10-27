#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

for script in scripts/*.sh; do
    bash -n "$script"
done
sh -n init-app/01-init-app.sh
sh -n init-log/01-init-log.sh

python3 -m compileall -q app tests 2>/dev/null || python3 -m compileall -q app

python3 - <<'PY'
from pathlib import Path
import yaml

with Path("compose.yaml").open(encoding="utf-8") as stream:
    document = yaml.safe_load(stream)
assert isinstance(document, dict)
assert set(document["services"]) == {
    "app-db", "log-db", "fluent-bit", "auth-service",
    "registration-api", "verification-worker"
}
print("[PASS] YAML Compose dapat diparse dan enam service ditemukan")
PY

python3 -m unittest discover -s app/tests -v

if command -v docker >/dev/null 2>&1; then
    [[ -f .env ]] || { echo "[FAIL] Jalankan ./scripts/setup.sh terlebih dahulu" >&2; exit 1; }
    docker compose config --quiet
    echo "[PASS] docker compose config"
else
    echo "[SKIP] Docker CLI tidak tersedia; validasi runtime dijalankan di laptop laboratorium."
fi

echo "[PASS] Validasi statis selesai."
