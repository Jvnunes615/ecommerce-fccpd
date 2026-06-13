"""API Gateway (:8080).

- Ponto de entrada unico: roteia /users, /products e /orders para os servicos.
- Repassa o header Authorization (JWT) aos servicos internos.
- Heartbeat: a cada N ms consulta GET /health de cada servico; apos M falhas
  marca como indisponivel (log com timestamp) e responde 503 nas requisicoes;
  registra a recuperacao quando o servico volta.
- Leitura de produtos com round-robin entre as duas replicas.
- Serve o frontend (loja) e o dashboard de monitoramento.
"""
import os
import sys
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, Response, jsonify, send_from_directory

from common import config, http_client
from common.tls import flask_ssl_context, scheme

PORT = config.get_int("GATEWAY_PORT", 8080)
_s = scheme()   # "https" ou "http" dependendo de USE_TLS
USERS_URL = config.get("USERS_URL", f"{_s}://localhost:5001")
ORDERS_URL = config.get("ORDERS_URL", f"{_s}://localhost:5003")
PRODUCTS_URL = config.get("PRODUCTS_URL", f"{_s}://localhost:5002")
PRODUCTS_REPLICA_URL = config.get("PRODUCTS_REPLICA_URL", f"{_s}://localhost:5012")

HEARTBEAT_INTERVAL_MS = config.get_int("HEARTBEAT_INTERVAL_MS", 5000)
HEARTBEAT_MAX_FAILURES = config.get_int("HEARTBEAT_MAX_FAILURES", 2)

FRONTEND_DIR = os.path.join(config.PROJECT_ROOT, "frontend")


def log(msg):
    print(f"[GATEWAY {datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


# Catalogo de servicos monitorados.
SERVICES = {
    "users": USERS_URL,
    "orders": ORDERS_URL,
    "products-primario": PRODUCTS_URL,
    "products-replica": PRODUCTS_REPLICA_URL,
}

health = {
    key: {"up": True, "failures": 0, "last_change": datetime.now(timezone.utc).isoformat()}
    for key in SERVICES
}


def is_up(key):
    return health[key]["up"]


# ---- Heartbeat (thread em background) -------------------------------------
def ping(url):
    try:
        resp = http_client.get(f"{url}/health", timeout=2)
        return resp.ok
    except Exception:
        return False


def heartbeat_loop():
    while True:
        for key, url in SERVICES.items():
            ok = ping(url)
            state = health[key]
            if ok:
                if not state["up"]:
                    state["up"] = True
                    state["last_change"] = datetime.now(timezone.utc).isoformat()
                    log(f'RECUPERACAO: servico "{key}" voltou a responder.')
                state["failures"] = 0
            else:
                state["failures"] += 1
                if state["up"] and state["failures"] >= HEARTBEAT_MAX_FAILURES:
                    state["up"] = False
                    state["last_change"] = datetime.now(timezone.utc).isoformat()
                    log(f'FALHA: servico "{key}" nao respondeu apos '
                        f'{state["failures"]} tentativas. Marcado INDISPONIVEL.')
        time.sleep(HEARTBEAT_INTERVAL_MS / 1000.0)


app = Flask(__name__)


# ---- Proxy ----------------------------------------------------------------
def forward(target_url):
    url = f"{target_url}{request.full_path.rstrip('?')}"
    headers = {}
    if request.headers.get("Authorization"):
        headers["Authorization"] = request.headers["Authorization"]
    json_body = request.get_json(silent=True) if request.method not in ("GET", "HEAD") else None
    try:
        resp = http_client.request(request.method, url, json_body=json_body,
                                   headers=headers, timeout=5)
        return Response(resp.body, status=resp.status, mimetype="application/json")
    except Exception as exc:
        log(f"ERRO ao encaminhar para {url}: {exc}")
        return jsonify(error="Falha ao contatar o servico de destino", detail=str(exc)), 503


def unavailable(key):
    return jsonify(error=f'Servico "{key}" indisponivel (detectado pelo heartbeat)'), 503


@app.route("/users", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/users/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_users(path):
    if not is_up("users"):
        return unavailable("users")
    return forward(USERS_URL)


@app.route("/orders", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/orders/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_orders(path):
    if not is_up("orders"):
        return unavailable("orders")
    return forward(ORDERS_URL)


_rr = {"i": 0}


def pick_read_replica():
    candidates = [("products-primario", PRODUCTS_URL),
                  ("products-replica", PRODUCTS_REPLICA_URL)]
    healthy = [c for c in candidates if is_up(c[0])]
    if not healthy:
        return None
    chosen = healthy[_rr["i"] % len(healthy)]
    _rr["i"] += 1
    return chosen


@app.route("/products", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/products/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def proxy_products(path):
    if request.method == "GET":
        replica = pick_read_replica()
        if not replica:
            return unavailable("products")
        log(f"Leitura de produtos roteada para {replica[0]}")
        return forward(replica[1])
    # Escritas vao para o primario, que replica para a par.
    if not is_up("products-primario"):
        return unavailable("products-primario")
    return forward(PRODUCTS_URL)


# ---- Monitoramento --------------------------------------------------------
@app.get("/status")
def status():
    return jsonify(
        timestamp=datetime.now(timezone.utc).isoformat(),
        services=[
            {"name": key, "url": SERVICES[key], **health[key]}
            for key in SERVICES
        ],
    )


# ---- Frontend -------------------------------------------------------------
@app.get("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/dashboard")
def dashboard():
    return send_from_directory(FRONTEND_DIR, "dashboard.html")


@app.get("/favicon.ico")
def favicon():
    return ("", 204)


@app.get("/assets/<path:filename>")
def assets(filename):
    return send_from_directory(os.path.join(FRONTEND_DIR, "assets"), filename)


if __name__ == "__main__":
    ssl_ctx = flask_ssl_context()
    proto = "https" if ssl_ctx else "http"
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    log(f"API Gateway na porta {PORT} [{proto}]")
    log(f"Heartbeat a cada {HEARTBEAT_INTERVAL_MS}ms, tolerancia de {HEARTBEAT_MAX_FAILURES} falhas.")
    app.run(host="0.0.0.0", port=PORT, threaded=True, ssl_context=ssl_ctx)
