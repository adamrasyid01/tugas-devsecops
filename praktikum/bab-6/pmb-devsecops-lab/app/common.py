"""Shared utilities for the PMB DevSecOps laboratory."""

from __future__ import annotations

import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any


REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")
SENSITIVE_MARKERS = (
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "session",
    "token",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def new_request_id() -> str:
    return f"REQ-{uuid.uuid4().hex}"


def normalize_request_id(candidate: str | None) -> str:
    if candidate and REQUEST_ID_RE.fullmatch(candidate):
        return candidate
    return new_request_id()


def require_env(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"Environment variable {name} wajib diatur")
    return value


def redact(value: Any, key: str = "") -> Any:
    lowered = key.lower()
    if any(marker in lowered for marker in SENSITIVE_MARKERS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    if isinstance(value, str) and len(value) > 1000:
        return value[:1000] + "...[TRUNCATED]"
    return value


def emit_event(
    service: str,
    severity: str,
    event: str,
    request_id: str | None = None,
    **fields: Any,
) -> None:
    record: dict[str, Any] = {
        "timestamp": utc_now(),
        "service": service,
        "severity": severity.upper(),
        "event": event,
        "request_id": normalize_request_id(request_id),
    }
    record.update(redact(fields))
    print(json.dumps(record, ensure_ascii=False, separators=(",", ":")), file=sys.stdout, flush=True)


def db_dsn() -> str:
    host = require_env("APP_DB_HOST")
    port = os.environ.get("APP_DB_PORT", "5432")
    database = require_env("APP_DB_NAME")
    user = require_env("APP_DB_USER")
    password = require_env("APP_DB_PASSWORD")
    return f"host={host} port={port} dbname={database} user={user} password={password} connect_timeout=3"


def wait_for_database(max_attempts: int = 30, delay_seconds: float = 2.0) -> None:
    import psycopg

    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            with psycopg.connect(db_dsn()) as connection:
                connection.execute("SELECT 1")
            return
        except Exception as exc:  # startup retry path
            last_error = exc
            time.sleep(delay_seconds)
    raise RuntimeError(f"Database belum siap setelah {max_attempts} percobaan") from last_error
