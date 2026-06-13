"""Servico de Produtos (:5002 primario / :5012 replica).

O mesmo codigo roda nas duas replicas; cada uma recebe porta, arquivo de dados
e a URL da replica par via variaveis de ambiente.

Endpoints:
  GET  /products            -> lista produtos (leitura em qualquer replica)
  GET  /products/<id>       -> detalha produto
  POST /products            -> cria produto (requer JWT de admin); replica antes de confirmar
  POST /internal/replicate  -> recebe escrita replicada da replica par (uso interno)
  GET  /health              -> { "status": "ok" }

Consistencia FORTE: a escrita so e confirmada ao cliente apos ser gravada
em ambas as replicas.
"""
import os
import sys
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request, jsonify

from common import config, http_client
from common.store import SqliteStore as JsonStore
from common.auth import require_admin
from common.tls import flask_ssl_context

PORT = config.get_int("PRODUCTS_PORT", 5002)
DATA_FILE = config.get(
    "PRODUCTS_DATA_FILE",
    os.path.join(config.PROJECT_ROOT, "data", "products.db"),
)
PEER_URL = config.get("PRODUCTS_PEER_URL")  # URL da replica par (ou None)
NODE_NAME = config.get("PRODUCTS_NODE_NAME", f"produtos:{PORT}")
INTERNAL_KEY = config.get("JWT_SECRET", "dev-secret-inseguro")

store = JsonStore(DATA_FILE)
app = Flask(__name__)


def log(msg):
    print(f"[{NODE_NAME} {datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


@app.get("/health")
def health():
    return jsonify(status="ok", node=NODE_NAME)


@app.get("/products")
def list_products():
    return jsonify(store.read_all())


@app.get("/products/<product_id>")
def get_product(product_id):
    product = store.find_by_id(product_id)
    if not product:
        return jsonify(error="Produto nao encontrado"), 404
    return jsonify(product)


@app.post("/internal/replicate")
def replicate():
    """Recebe uma escrita vinda da replica par. Idempotente; NAO re-propaga."""
    if request.headers.get("X-Internal-Key") != INTERNAL_KEY:
        return jsonify(error="Replicacao nao autorizada"), 403
    product = request.get_json(silent=True) or {}
    if not product.get("id"):
        return jsonify(error="Produto invalido para replicacao"), 400
    store.upsert(product)
    log(f"Replica aplicada: produto {product['id']} ({product.get('name')})")
    return jsonify(status="replicated", node=NODE_NAME)


def replicate_to_peer(product):
    if not PEER_URL:
        return
    resp = http_client.post(
        f"{PEER_URL}/internal/replicate",
        json_body=product,
        headers={"X-Internal-Key": INTERNAL_KEY},
        timeout=3,
    )
    if not resp.ok:
        raise RuntimeError(f"replica par respondeu {resp.status}")


@app.post("/products")
@require_admin
def create_product():
    body = request.get_json(silent=True) or {}
    name = body.get("name")
    price = body.get("price")
    if not name or price is None:
        return jsonify(error="name e price sao obrigatorios"), 400

    product = {
        "id": uuid.uuid4().hex[:12],
        "name": name,
        "price": float(price),
        "description": body.get("description", ""),
        "stock": int(body.get("stock", 0)),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    store.upsert(product)
    try:
        replicate_to_peer(product)
    except Exception as exc:  # falha de replicacao -> desfaz escrita local
        items = [p for p in store.read_all() if p["id"] != product["id"]]
        store.write_all(items)
        log(f"ERRO ao replicar produto {product['id']}: {exc}. Escrita desfeita.")
        return jsonify(
            error="Falha ao replicar para a replica par. Escrita nao confirmada.",
            detail=str(exc),
        ), 503

    log(f"Produto criado e replicado: {product['id']} ({product['name']})")
    return jsonify(product), 201


if __name__ == "__main__":
    ssl_ctx = flask_ssl_context()
    proto = "https" if ssl_ctx else "http"
    log(f"Servico de Produtos na porta {PORT} [{proto}] (dados: {DATA_FILE}, par: {PEER_URL or 'nenhum'})")
    app.run(host="0.0.0.0", port=PORT, threaded=True, ssl_context=ssl_ctx)
