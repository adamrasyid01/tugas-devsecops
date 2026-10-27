"""Web interface and registration API for the PMB laboratory."""

from __future__ import annotations

import hmac
import os
import re
import secrets
import uuid
from functools import wraps

import psycopg
import requests
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from psycopg.rows import dict_row
from werkzeug.exceptions import HTTPException

from common import db_dsn, emit_event, normalize_request_id, require_env


SERVICE = "registration-api"
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,190}$")
ALLOWED_PROGRAMS = {
    "D3 Teknik Informatika",
    "Sarjana Terapan Teknik Informatika",
    "Magister Terapan Teknik Informatika",
}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=require_env("SESSION_SECRET"),
    MAX_CONTENT_LENGTH=64 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=False,
)


def connect():
    return psycopg.connect(db_dsn(), row_factory=dict_row)


def csrf_token() -> str:
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


app.jinja_env.globals["csrf_token"] = csrf_token


def verify_csrf() -> bool:
    supplied = request.form.get("csrf_token", "")
    expected = session.get("csrf_token", "")
    return bool(supplied and expected and hmac.compare_digest(supplied, expected))


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_ref"):
            flash("Silakan masuk terlebih dahulu.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.before_request
def assign_request_id() -> None:
    g.request_id = normalize_request_id(request.headers.get("X-Request-ID"))


@app.after_request
def harden_response(response):
    response.headers["X-Request-ID"] = g.request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self'; img-src 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    if request.path != "/static/style.css":
        response.headers["Cache-Control"] = "no-store"
    emit_event(
        SERVICE,
        "INFO" if response.status_code < 400 else "WARN",
        "http_request",
        g.request_id,
        method=request.method,
        path=request.path,
        status=response.status_code,
    )
    return response


@app.get("/healthz")
def healthz():
    try:
        with connect() as connection:
            connection.execute("SELECT 1")
        return jsonify(status="ok", service=SERVICE)
    except Exception:
        return jsonify(status="degraded", service=SERVICE), 503


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    if not verify_csrf():
        emit_event(SERVICE, "WARN", "csrf_rejected", g.request_id, path=request.path)
        return render_template("login.html", error="Token formulir tidak valid."), 400

    username = request.form.get("username", "")[:128]
    password = request.form.get("password", "")[:256]
    try:
        response = requests.post(
            f"{require_env('AUTH_URL')}/api/login",
            json={"username": username, "password": password},
            headers={"X-Request-ID": g.request_id},
            timeout=3,
        )
    except requests.RequestException:
        emit_event(SERVICE, "ERROR", "auth_dependency_unavailable", g.request_id)
        return render_template("login.html", error="Layanan autentikasi tidak tersedia."), 503

    if response.status_code != 200:
        return render_template("login.html", error="Nama pengguna atau kata sandi salah."), 401

    result = response.json()
    session.clear()
    session["user_ref"] = result["user_ref"]
    session["display_name"] = result["display_name"]
    session["csrf_token"] = secrets.token_urlsafe(32)
    flash("Login berhasil.", "success")
    return redirect(url_for("register"))


@app.post("/logout")
@login_required
def logout():
    if not verify_csrf():
        return "CSRF validation failed", 400
    user_ref = session.get("user_ref")
    session.clear()
    emit_event(SERVICE, "INFO", "logout", g.request_id, user_ref=user_ref)
    return redirect(url_for("login"))


@app.route("/", methods=["GET"])
def index():
    return redirect(url_for("status" if session.get("user_ref") else "login"))


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    if request.method == "GET":
        return render_template("register.html", programs=sorted(ALLOWED_PROGRAMS))
    if not verify_csrf():
        emit_event(SERVICE, "WARN", "csrf_rejected", g.request_id, path=request.path)
        return render_template("register.html", programs=sorted(ALLOWED_PROGRAMS), error="Token formulir tidak valid."), 400

    full_name = " ".join(request.form.get("full_name", "").split())[:120]
    email = request.form.get("email", "").strip().lower()[:255]
    program = request.form.get("program", "")
    if len(full_name) < 3 or not EMAIL_RE.fullmatch(email) or program not in ALLOWED_PROGRAMS:
        emit_event(SERVICE, "WARN", "registration_validation_failed", g.request_id, user_ref=session["user_ref"])
        return render_template(
            "register.html",
            programs=sorted(ALLOWED_PROGRAMS),
            error="Nama, email, atau program studi tidak valid.",
        ), 400

    public_id = str(uuid.uuid4())
    try:
        with connect() as connection:
            connection.execute(
                """
                INSERT INTO registrations
                    (public_id, user_ref, full_name, email, program, status, request_id)
                VALUES (%s, %s, %s, %s, %s, 'SUBMITTED', %s)
                """,
                (public_id, session["user_ref"], full_name, email, program, g.request_id),
            )
    except psycopg.errors.UniqueViolation:
        emit_event(SERVICE, "WARN", "duplicate_registration", g.request_id, user_ref=session["user_ref"])
        return render_template(
            "register.html",
            programs=sorted(ALLOWED_PROGRAMS),
            error="Email tersebut sudah digunakan pada pendaftaran lain.",
        ), 409

    emit_event(
        SERVICE,
        "INFO",
        "registration_submitted",
        g.request_id,
        user_ref=session["user_ref"],
        registration_id=public_id,
        program=program,
    )
    flash("Pendaftaran diterima dan menunggu verifikasi.", "success")
    return redirect(url_for("status"))


@app.get("/status")
@login_required
def status():
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT public_id::text, program, status, attempt, failure_code,
                   submitted_at, updated_at, request_id
            FROM registrations
            WHERE user_ref = %s
            ORDER BY submitted_at DESC
            LIMIT 20
            """,
            (session["user_ref"],),
        ).fetchall()
        mode = connection.execute(
            "SELECT value FROM lab_control WHERE key = 'incident_mode'"
        ).fetchone()["value"]
    return render_template("status.html", registrations=rows, incident_mode=mode)


@app.get("/api/registrations/<public_id>")
@login_required
def registration_status(public_id: str):
    try:
        parsed_id = uuid.UUID(public_id)
    except ValueError:
        return jsonify(error="invalid_registration_id", request_id=g.request_id), 400
    with connect() as connection:
        row = connection.execute(
            """
            SELECT public_id::text, program, status, attempt, failure_code,
                   submitted_at, updated_at, request_id
            FROM registrations
            WHERE public_id = %s AND user_ref = %s
            """,
            (parsed_id, session["user_ref"]),
        ).fetchone()
    if not row:
        return jsonify(error="not_found", request_id=g.request_id), 404
    return jsonify(row)


@app.errorhandler(413)
def payload_too_large(_error):
    emit_event(SERVICE, "WARN", "payload_rejected", g.request_id, reason="too_large")
    return "Payload too large", 413


@app.errorhandler(Exception)
def unexpected_error(error):
    if isinstance(error, HTTPException):
        return error
    if isinstance(error, psycopg.Error):
        category = "database_error"
    else:
        category = "unexpected_error"
    emit_event(SERVICE, "ERROR", category, getattr(g, "request_id", None), error_type=type(error).__name__)
    return render_template("error.html", request_id=getattr(g, "request_id", "unknown")), 500
