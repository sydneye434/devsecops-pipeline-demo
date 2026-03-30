"""
Minimal Flask demo for DevSecOps pipeline exercises.

Read top-to-bottom: health check, a JSON API, a login stub, and a small SQLite-backed
query used to illustrate unsafe SQL patterns. Not for production.
"""

from __future__ import annotations

import os

import requests
from flask import Flask, jsonify, request
from sqlalchemy import create_engine, text

app = Flask(__name__)

# -----------------------------------------------------------------------------
# INTENTIONAL DEMO VULNERABILITY (secrets / SAST):
# Hardcoded credential. Semgrep and many secret scanners flag literals that look
# like API keys. TruffleHog may only alert on *verified* secrets — this is still
# useful for SAST demos and unsafe-pattern teaching.
# -----------------------------------------------------------------------------
DEMO_INTERNAL_API_KEY = "sk-demo-intentional-hardcoded-key-9f2b7c1a4e"

# -----------------------------------------------------------------------------
# INTENTIONAL DEMO VULNERABILITY (SCA):
# `requests` pulls in urllib3; requirements.txt pins a vulnerable urllib3 version.
# The CVE is in the dependency tree, not in this file.
# -----------------------------------------------------------------------------


def _db_path() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.db")


engine = create_engine(
    f"sqlite:///{_db_path()}",
    connect_args={"check_same_thread": False},
)


def _init_db() -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS users "
                "(id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
        )
        count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar_one()
        if count == 0:
            conn.execute(
                text(
                    "INSERT INTO users (name) VALUES ('alice'), ('bob'), ('carol')"
                )
            )


_db_ready = False


@app.before_request
def _ensure_db() -> None:
    """Seed SQLite once per process (OK for a single-worker demo)."""
    global _db_ready
    if _db_ready:
        return
    _init_db()
    _db_ready = True


@app.get("/health")
def health() -> tuple[dict, int]:
    """Liveness/readiness style check for load balancers and DAST."""
    return jsonify(status="ok", service="devsecops-demo"), 200


@app.get("/api/info")
def api_info() -> tuple[dict, int]:
    """Tiny JSON endpoint — shows normal app behavior; references `requests` for SCA realism."""
    return jsonify(
        app="demo-flask",
        version="0.1.0",
        requests_version=requests.__version__,
    ), 200


@app.post("/login")
def login() -> tuple[dict, int]:
    """
    Login stub: accepts JSON {"username": ..., "password": ...}.

    Demonstrates comparing client input to server-side material (not production-safe).
    """
    payload = request.get_json(silent=True) or {}
    username = payload.get("username", "")
    password = payload.get("password", "")

    # Demo-only: never ship static password checks like this.
    if username == "demo" and password == "demo":
        return jsonify(ok=True, token=DEMO_INTERNAL_API_KEY), 200

    return jsonify(ok=False, error="invalid_credentials"), 401


@app.get("/api/users")
def api_users() -> tuple[dict, int]:
    """
    Lookup users by name query parameter.

    INTENTIONAL DEMO VULNERABILITY (SAST — SQL injection):
    User-controlled input is concatenated into SQL. A scanner should flag this.
    Example (demo only): /api/users?name=' OR '1'='1
    """
    name = request.args.get("name", "")

    # Safe pattern would be: conn.execute(text("SELECT ... WHERE name = :n"), {"n": name})
    # INTENTIONAL: string concatenation into SQL.
    raw_sql = f"SELECT id, name FROM users WHERE name = '{name}'"

    with engine.connect() as conn:
        rows = conn.execute(text(raw_sql)).mappings().all()

    return jsonify(users=[dict(r) for r in rows]), 200


if __name__ == "__main__":
    _init_db()
    _db_ready = True
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8000")), debug=False)
