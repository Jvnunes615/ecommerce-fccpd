"""Servico de Usuarios (:5001).

Endpoints:
  POST /users/register  -> cria usuario (senha em hash PBKDF2)
  POST /users/login     -> autentica e retorna JWT
  GET  /users/<id>      -> dados do usuario (requer JWT)
  GET  /health          -> { "status": "ok" }
"""
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify

from common import config
from common.store import SqliteStore as JsonStore
from common.auth import hash_password, verify_password, sign_token, require_auth

PORT = config.get_int("USERS_PORT", 5001)
DATA_FILE = config.get(
    "USERS_DATA_FILE",
    os.path.join(config.PROJECT_ROOT, "data", "users.db"),
)

store = JsonStore(DATA_FILE)
app = Flask(__name__)


def log(msg):
    print(f"[USERS {datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def public_user(user):
    return {k: v for k, v in user.items() if k != "password_hash"}


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/users/register")
def register():
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    email = body.get("email")
    password = body.get("password")
    role = body.get("role")
    if not name or not email or not password:
        return jsonify(error="name, email e password sao obrigatorios"), 400
    if any(u["email"] == email for u in store.read_all()):
        return jsonify(error="E-mail ja cadastrado"), 409

    user = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "email": email,
        "password_hash": hash_password(password),
        "role": "admin" if role == "admin" else "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    store.insert(user)
    log(f"Usuario registrado: {email} ({user['role']})")
    return jsonify(public_user(user)), 201


@app.post("/users/login")
def login():
    body = request.get_json(silent=True) or {}
    email = body.get("email")
    password = body.get("password")
    if not email or not password:
        return jsonify(error="email e password sao obrigatorios"), 400

    user = next((u for u in store.read_all() if u["email"] == email), None)
    if not user or not verify_password(password, user["password_hash"]):
        return jsonify(error="Credenciais invalidas"), 401

    token = sign_token({"userId": user["id"], "email": user["email"], "role": user["role"]})
    log(f"Login efetuado: {email}")
    return jsonify(
        token=token,
        user={"id": user["id"], "name": user["name"], "email": user["email"], "role": user["role"]},
    )


@app.get("/users/<user_id>")
@require_auth
def get_user(user_id):
    user = store.find_by_id(user_id)
    if not user:
        return jsonify(error="Usuario nao encontrado"), 404
    return jsonify(public_user(user))


if __name__ == "__main__":
    log(f"Servico de Usuarios na porta {PORT} (dados: {DATA_FILE})")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
