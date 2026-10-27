#!/usr/bin/env sh
set -eu

: "${POSTGRES_USER:?POSTGRES_USER belum diatur}"
: "${POSTGRES_DB:?POSTGRES_DB belum diatur}"
: "${APP_DB_USER:?APP_DB_USER belum diatur}"
: "${APP_DB_PASSWORD:?APP_DB_PASSWORD belum diatur}"

psql \
  --set=ON_ERROR_STOP=1 \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" \
  --set=app_user="$APP_DB_USER" \
  --set=app_password="$APP_DB_PASSWORD" <<'SQL'
SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', :'app_user', :'app_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'app_user')
\gexec

CREATE TABLE IF NOT EXISTS registrations (
    id BIGSERIAL PRIMARY KEY,
    public_id UUID NOT NULL UNIQUE,
    user_ref VARCHAR(64) NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    program VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL
        CHECK (status IN ('SUBMITTED', 'PROCESSING', 'VERIFIED', 'FAILED')),
    attempt INTEGER NOT NULL DEFAULT 0 CHECK (attempt BETWEEN 0 AND 10),
    failure_code VARCHAR(64),
    request_id VARCHAR(128) NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_registrations_user_time
    ON registrations(user_ref, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_registrations_status_time
    ON registrations(status, submitted_at);

CREATE INDEX IF NOT EXISTS idx_registrations_request
    ON registrations(request_id);

CREATE TABLE IF NOT EXISTS lab_control (
    key VARCHAR(64) PRIMARY KEY,
    value VARCHAR(64) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO lab_control(key, value)
VALUES ('incident_mode', 'none')
ON CONFLICT (key) DO NOTHING;

SELECT format('GRANT CONNECT ON DATABASE %I TO %I', current_database(), :'app_user')
\gexec
SELECT format('GRANT USAGE ON SCHEMA public TO %I', :'app_user')
\gexec
SELECT format('GRANT SELECT, INSERT, UPDATE ON TABLE registrations TO %I', :'app_user')
\gexec
SELECT format('GRANT SELECT ON TABLE lab_control TO %I', :'app_user')
\gexec
SELECT format('GRANT USAGE, SELECT ON SEQUENCE registrations_id_seq TO %I', :'app_user')
\gexec
SQL
