"""Background verification worker with controllable laboratory failures."""

from __future__ import annotations

import os
import signal
import time

import psycopg
from psycopg.rows import dict_row

from common import db_dsn, emit_event, wait_for_database


SERVICE = "verification-worker"
running = True


def stop_worker(_signum, _frame) -> None:
    global running
    running = False


def claim_registration():
    with psycopg.connect(db_dsn(), row_factory=dict_row) as connection:
        with connection.transaction():
            row = connection.execute(
                """
                SELECT id, public_id::text, user_ref, program, request_id
                FROM registrations
                WHERE status = 'SUBMITTED'
                ORDER BY submitted_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """
            ).fetchone()
            if not row:
                return None
            connection.execute(
                """
                UPDATE registrations
                SET status = 'PROCESSING', attempt = 0,
                    failure_code = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (row["id"],),
            )
            return row


def incident_mode() -> str:
    with psycopg.connect(db_dsn(), row_factory=dict_row) as connection:
        row = connection.execute(
            "SELECT value FROM lab_control WHERE key = 'incident_mode'"
        ).fetchone()
        return row["value"] if row else "none"


def update_result(registration_id: int, status: str, attempt: int, failure_code: str | None) -> None:
    with psycopg.connect(db_dsn()) as connection:
        connection.execute(
            """
            UPDATE registrations
            SET status = %s, attempt = %s, failure_code = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (status, attempt, failure_code, registration_id),
        )


def process_registration(row) -> None:
    request_id = row["request_id"]
    registration_id = row["public_id"]
    mode = incident_mode()
    emit_event(
        SERVICE,
        "INFO",
        "verification_started",
        request_id,
        registration_id=registration_id,
        user_ref=row["user_ref"],
        mode=mode,
    )

    if mode == "timeout":
        for attempt in range(1, 4):
            update_result(row["id"], "PROCESSING", attempt, None)
            emit_event(
                SERVICE,
                "WARN",
                "verification_retry",
                request_id,
                registration_id=registration_id,
                attempt=attempt,
                dependency="document-verifier",
            )
            time.sleep(1)
        update_result(row["id"], "FAILED", 3, "VERIFY-TIMEOUT")
        emit_event(
            SERVICE,
            "ERROR",
            "dependency_timeout",
            request_id,
            registration_id=registration_id,
            attempt=3,
            dependency="document-verifier",
            error_code="VERIFY-TIMEOUT",
        )
        return

    time.sleep(1)
    update_result(row["id"], "VERIFIED", 1, None)
    emit_event(
        SERVICE,
        "INFO",
        "verification_completed",
        request_id,
        registration_id=registration_id,
        attempt=1,
    )


def main() -> None:
    signal.signal(signal.SIGTERM, stop_worker)
    signal.signal(signal.SIGINT, stop_worker)
    poll_seconds = max(1.0, float(os.environ.get("WORKER_POLL_SECONDS", "2")))
    wait_for_database()
    emit_event(SERVICE, "INFO", "worker_started", poll_seconds=poll_seconds)

    while running:
        try:
            row = claim_registration()
            if row:
                process_registration(row)
            else:
                time.sleep(poll_seconds)
        except Exception as error:
            emit_event(SERVICE, "ERROR", "worker_cycle_failed", error_type=type(error).__name__)
            time.sleep(poll_seconds)
    emit_event(SERVICE, "INFO", "worker_stopped")


if __name__ == "__main__":
    main()
