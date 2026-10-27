"""Internal authentication service for the PMB laboratory."""

from __future__ import annotations

import hashlib
import hmac
import os

from flask import Flask, g, jsonify, request

from common import emit_event, normalize_request_id, require_env


SERVICE = "auth-service"
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024


def password_digest(password: str) -> str:
    salt = require_env("LAB_PASSWORD_SALT").encode("utf-8")
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000).hex()


def username_fingerprint(username: str) -> str:
    return hashlib.sha256(username.encode("utf-8")).hexdigest()[:12]


@app.before_request
def assign_request_id() -> None:
    g.request_id = normalize_request_id(request.headers.get("X-Request-ID"))


@app.after_request
def attach_request_id(response):
    response.headers["X-Request-ID"] = g.request_id
    response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/healthz")
def healthz():
    return jsonify(status="ok", service=SERVICE)


@app.post("/api/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", ""))[:128]
    password = str(payload.get("password", ""))[:256]

    expected_username = require_env("LAB_USERNAME")
    expected_hash = require_env("LAB_PASSWORD_HASH")
    username_ok = hmac.compare_digest(username, expected_username)
    password_ok = hmac.compare_digest(password_digest(password), expected_hash)

    if not (username_ok and password_ok):
        emit_event(
            SERVICE,
            "WARN",
            "login_failed",
            g.request_id,
            username_fingerprint=username_fingerprint(username),
            remote_addr=request.remote_addr,
        )
        return jsonify(error="invalid_credentials", request_id=g.request_id), 401

    user_ref = require_env("LAB_USER_REF")
    emit_event(SERVICE, "INFO", "login_success", g.request_id, user_ref=user_ref)
    return jsonify(user_ref=user_ref, display_name="Mahasiswa Laboratorium", request_id=g.request_id)


@app.errorhandler(413)
def payload_too_large(_error):
    emit_event(SERVICE, "WARN", "payload_rejected", g.request_id, reason="too_large")
    return jsonify(error="payload_too_large", request_id=g.request_id), 413
