#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
    echo "[INFO] .env sudah ada; konfigurasi dipertahankan."
else
    cp .env.example .env
    chmod 600 .env

    random_hex() {
        if command -v openssl >/dev/null 2>&1; then
            openssl rand -hex 24
        else
            python3 -c 'import secrets; print(secrets.token_hex(24))'
        fi
    }

    sed -i "s/change-me-app-admin/$(random_hex)/" .env
    sed -i "s/change-me-app-writer/$(random_hex)/" .env
    sed -i "s/change-me-log-admin/$(random_hex)/" .env
    sed -i "s/change-me-log-writer/$(random_hex)/" .env
    sed -i "s/change-me-session-secret/$(random_hex)/" .env
    echo "[PASS] .env dibuat dengan credential acak."
fi

chmod +x init-app/01-init-app.sh init-log/01-init-log.sh
chmod +x scripts/*.sh

echo "[INFO] Login laboratorium: student / StudentLab!2026"
echo "[INFO] Berikutnya: make validate && make up"
