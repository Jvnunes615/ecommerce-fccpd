"""Autenticacao: hashing de senha (PBKDF2-HMAC-SHA256) e JWT (HS256).

Implementado apenas com a biblioteca padrao do Python, para evitar
dependencias que possam nao ter wheels disponiveis (bcrypt/PyJWT).
O algoritmo do JWT (HS256) e identico ao de bibliotecas como PyJWT.
"""
import base64
import hashlib
import hmac
import json
import os
import time

from functools import wraps
from flask import request, jsonify

from common import config

JWT_SECRET = config.get("JWT_SECRET", "dev-secret-inseguro")
JWT_EXPIRES_SECONDS = config.get_int("JWT_EXPIRES_SECONDS", 3600)


# ---- Hash de senha (PBKDF2-HMAC-SHA256) -----------------------------------
def hash_password(password, iterations=120_000):
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def verify_password(password, stored):
    try:
        algo, iterations, salt_hex, hash_hex = stored.split("$")
        iterations = int(iterations)
        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, AttributeError):
        return False


# ---- JWT (HS256) -----------------------------------------------------------
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(seg: str) -> bytes:
    padding = "=" * (-len(seg) % 4)
    return base64.urlsafe_b64decode(seg + padding)


def sign_token(payload: dict) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    body = dict(payload)
    now = int(time.time())
    body.setdefault("iat", now)
    body["exp"] = now + JWT_EXPIRES_SECONDS

    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(body, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


class JWTError(Exception):
    pass


def verify_token(token: str) -> dict:
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        raise JWTError("Formato de token invalido")

    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64url_decode(sig_b64)):
        raise JWTError("Assinatura invalida")

    payload = json.loads(_b64url_decode(payload_b64))
    if "exp" in payload and int(time.time()) > int(payload["exp"]):
        raise JWTError("Token expirado")
    return payload


# ---- Helpers de requisicao / decorators -----------------------------------
def _extract_token():
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[7:].strip()
    return None


def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        token = _extract_token()
        if not token:
            return jsonify(error="Token JWT ausente"), 401
        try:
            request.user = verify_token(token)
        except JWTError as exc:
            return jsonify(error=f"Token JWT invalido: {exc}"), 401
        return fn(*args, **kwargs)
    return wrapper


def require_admin(fn):
    @wraps(fn)
    @require_auth
    def wrapper(*args, **kwargs):
        if request.user.get("role") != "admin":
            return jsonify(error="Acesso restrito a administradores"), 403
        return fn(*args, **kwargs)
    return wrapper
