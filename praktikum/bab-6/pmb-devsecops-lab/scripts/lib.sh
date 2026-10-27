#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

load_env() {
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        echo "[FAIL] .env belum tersedia. Jalankan ./scripts/setup.sh" >&2
        exit 1
    fi
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.env"
    set +a
}

wait_http() {
    local name="$1"
    local url="$2"
    local attempts="${3:-60}"
    local i
    for ((i = 1; i <= attempts; i++)); do
        if curl -fsS --max-time 3 "$url" >/dev/null; then
            echo "[PASS] $name siap"
            return 0
        fi
        sleep 2
    done
    echo "[FAIL] $name tidak siap: $url" >&2
    return 1
}

extract_csrf() {
    sed -n 's/.*name="csrf_token" value="\([^"]*\)".*/\1/p' | head -n 1
}

submit_application() {
    local scenario="$1"
    local cookie_file header_file login_page register_page csrf email request_id
    cookie_file="$(mktemp)"
    header_file="$(mktemp)"
    login_page="$(mktemp)"
    register_page="$(mktemp)"
    trap "rm -f '$cookie_file' '$header_file' '$login_page' '$register_page'" EXIT

    curl -fsS -c "$cookie_file" http://127.0.0.1:8080/login >"$login_page"
    csrf="$(extract_csrf <"$login_page")"
    [[ -n "$csrf" ]] || { echo "[FAIL] CSRF login tidak ditemukan" >&2; return 1; }

    curl -fsS -o /dev/null -b "$cookie_file" -c "$cookie_file" \
        -X POST http://127.0.0.1:8080/login \
        --data-urlencode "csrf_token=$csrf" \
        --data-urlencode "username=${LAB_USERNAME:-student}" \
        --data-urlencode "password=${LAB_LOGIN_PASSWORD:-StudentLab!2026}"

    curl -fsS -b "$cookie_file" -c "$cookie_file" \
        http://127.0.0.1:8080/register >"$register_page"
    csrf="$(extract_csrf <"$register_page")"
    [[ -n "$csrf" ]] || { echo "[FAIL] CSRF pendaftaran tidak ditemukan" >&2; return 1; }

    email="${scenario}.$(date +%s).$(printf '%04d' "$((RANDOM % 10000))")@example.test"
    curl -fsS -D "$header_file" -o /dev/null -b "$cookie_file" -c "$cookie_file" \
        -X POST http://127.0.0.1:8080/register \
        --data-urlencode "csrf_token=$csrf" \
        --data-urlencode "full_name=Mahasiswa ${scenario}" \
        --data-urlencode "email=$email" \
        --data-urlencode "program=Sarjana Terapan Teknik Informatika"

    request_id="$(awk 'BEGIN{IGNORECASE=1} /^X-Request-ID:/ {gsub("\r", "", $2); print $2}' "$header_file" | tail -n 1)"
    [[ -n "$request_id" ]] || { echo "[FAIL] X-Request-ID tidak ditemukan" >&2; return 1; }
    rm -f "$cookie_file" "$header_file" "$login_page" "$register_page"
    trap - EXIT
    echo "$request_id"
}
