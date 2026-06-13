"""Servico de Pedidos (:5003).

Endpoints:
  POST /orders            -> cria pedido vinculando usuario (do JWT) e produto
  GET  /orders/<userId>   -> lista pedidos de um usuario (requer JWT)
  GET  /health            -> { "status": "ok" }

Para criar um pedido, valida a existencia do produto consultando o
Servico de Produtos via REST.
"""
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify

from common import config, http_client
from common.store import SqliteStore as JsonStore
from common.auth import require_auth
from common.tls import flask_ssl_context, scheme as _scheme

PORT = config.get_int("ORDERS_PORT", 5003)
DATA_FILE = config.get(
    "ORDERS_DATA_FILE",
    os.path.join(config.PROJECT_ROOT, "data", "orders.db"),
)
PRODUCTS_URL = config.get("PRODUCTS_URL", f"{_scheme()}://localhost:5002")

store = JsonStore(DATA_FILE)
app = Flask(__name__)


def log(msg):
    print(f"[ORDERS {datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/orders")
@require_auth
def create_order():
    body = request.get_json(silent=True) or {}
    product_id = body.get("productId")
    if not product_id:
        return jsonify(error="productId e obrigatorio"), 400
    quantity = int(body.get("quantity", 1))

    try:
        resp = http_client.get(f"{PRODUCTS_URL}/products/{product_id}", timeout=3)
    except Exception as exc:
        log(f"ERRO ao consultar Servico de Produtos: {exc}")
        return jsonify(error="Servico de Produtos indisponivel", detail=str(exc)), 503

    if resp.status == 404:
        return jsonify(error="Produto nao encontrado"), 404
    if not resp.ok:
        return jsonify(error="Servico de Produtos indisponivel", detail=f"status {resp.status}"), 503

    product = resp.json()
    order = {
        "id": uuid.uuid4().hex[:12],
        "userId": request.user["userId"],
        "productId": product["id"],
        "productName": product["name"],
        "unitPrice": product["price"],
        "quantity": quantity,
        "total": round(product["price"] * quantity, 2),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    store.insert(order)
    log(f"Pedido criado: {order['id']} (user {order['userId']}, produto {order['productId']})")
    return jsonify(order), 201


@app.get("/orders/<user_id>")
@require_auth
def list_orders(user_id):
    # Usuario comum so ve os proprios pedidos; admin ve qualquer um.
    if request.user.get("role") != "admin" and request.user["userId"] != user_id:
        return jsonify(error="Voce so pode consultar seus proprios pedidos"), 403
    orders = [o for o in store.read_all() if o["userId"] == user_id]
    return jsonify(orders)


if __name__ == "__main__":
    ssl_ctx = flask_ssl_context()
    proto = "https" if ssl_ctx else "http"
    log(f"Servico de Pedidos na porta {PORT} [{proto}] (dados: {DATA_FILE})")
    app.run(host="0.0.0.0", port=PORT, threaded=True, ssl_context=ssl_ctx)
