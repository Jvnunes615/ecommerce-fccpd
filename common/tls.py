"""Helpers de TLS para Flask (servidor) e urllib (cliente).

Centraliza a leitura dos certificados gerados em certs/ para que todos
os microsservicos usem a mesma configuracao de forma consistente.
"""
import os
import ssl

from common import config

USE_TLS = config.get("USE_TLS", "true").lower() != "false"

CERTS_DIR = os.path.join(config.PROJECT_ROOT, "certs")
SERVER_CERT = os.path.join(CERTS_DIR, "server.crt")
SERVER_KEY = os.path.join(CERTS_DIR, "server.key")
CA_CERT = os.path.join(CERTS_DIR, "ca.crt")


def flask_ssl_context():
    """Retorna ssl_context para app.run() ou None se TLS desabilitado."""
    if not USE_TLS:
        return None
    if not os.path.exists(SERVER_CERT) or not os.path.exists(SERVER_KEY):
        import warnings
        warnings.warn(
            "Certificados TLS nao encontrados em certs/. "
            "Execute: python scripts/generate_certs.py  ou defina USE_TLS=false.",
            RuntimeWarning,
            stacklevel=2,
        )
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(SERVER_CERT, SERVER_KEY)
    ctx.load_verify_locations(CA_CERT)
    return ctx


def scheme():
    """Retorna 'https' ou 'http' conforme USE_TLS."""
    return "https" if USE_TLS else "http"
