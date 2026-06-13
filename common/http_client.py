"""Cliente HTTP com suporte a HTTPS (TLS) baseado em urllib (stdlib).

Para comunicacao interna entre microsservicos usa o certificado CA proprio
(certs/ca.crt), validando a identidade do servidor sem precisar de uma CA
publica. O SSL pode ser desabilitado via variavel de ambiente USE_TLS=false.
"""
import json
import os
import ssl
import urllib.error
import urllib.request

from common import config

USE_TLS = config.get("USE_TLS", "true").lower() != "false"
CA_CERT = os.path.join(config.PROJECT_ROOT, "certs", "ca.crt")


def _ssl_context():
    """Contexto SSL que confia apenas no CA proprio do projeto.

    check_hostname e verify_mode sao mantidos nos valores seguros padrao
    (True / CERT_REQUIRED). A verificacao funciona corretamente porque o
    server.crt tem SANs cobrindo localhost, 127.0.0.1 e os nomes Docker.
    """
    if not USE_TLS or not os.path.exists(CA_CERT):
        return None
    return ssl.create_default_context(cafile=CA_CERT)


class HttpResponse:
    def __init__(self, status, body):
        self.status = status
        self.body = body

    def json(self):
        try:
            return json.loads(self.body) if self.body else None
        except json.JSONDecodeError:
            return None

    @property
    def ok(self):
        return 200 <= self.status < 300


def request(method, url, json_body=None, headers=None, timeout=5):
    data = None
    hdrs = dict(headers or {})
    if json_body is not None:
        data = json.dumps(json_body).encode()
        hdrs.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    ctx = _ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return HttpResponse(resp.status, resp.read().decode())
    except urllib.error.HTTPError as exc:
        return HttpResponse(exc.code, exc.read().decode())


def get(url, **kwargs):
    return request("GET", url, **kwargs)


def post(url, **kwargs):
    return request("POST", url, **kwargs)
