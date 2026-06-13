"""Sobe todos os microsservicos + gateway em processos separados.

Uso:  python scripts/start_all.py
Encerra todos com Ctrl+C.

Cada processo recebe as variaveis de ambiente apropriadas. As duas replicas
de Produtos usam arquivos de dados distintos e apontam uma para a outra.
"""
import os
import signal
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from common import config  # noqa: E402  (carrega .env)

PY = sys.executable
DATA = os.path.join(ROOT, "data")

USERS_PORT = config.get("USERS_PORT", "5001")
PRODUCTS_PORT = config.get("PRODUCTS_PORT", "5002")
PRODUCTS_REPLICA_PORT = config.get("PRODUCTS_REPLICA_PORT", "5012")
ORDERS_PORT = config.get("ORDERS_PORT", "5003")
GATEWAY_PORT = config.get("GATEWAY_PORT", "8080")

from common.tls import scheme as _scheme  # noqa: E402

_s = _scheme()
PRODUCTS_URL = config.get("PRODUCTS_URL", f"{_s}://localhost:{PRODUCTS_PORT}")
PRODUCTS_REPLICA_URL = config.get("PRODUCTS_REPLICA_URL", f"{_s}://localhost:{PRODUCTS_REPLICA_PORT}")


def env_with(extra):
    env = os.environ.copy()
    env.update({k: str(v) for k, v in extra.items()})
    return env


SERVICES = [
    ("USERS", os.path.join(ROOT, "users", "app.py"), {}),
    ("PRODUCTS-PRIMARIO", os.path.join(ROOT, "products", "app.py"), {
        "PRODUCTS_PORT": PRODUCTS_PORT,
        "PRODUCTS_DATA_FILE": os.path.join(DATA, "products_primary.db"),
        "PRODUCTS_PEER_URL": PRODUCTS_REPLICA_URL,
        "PRODUCTS_NODE_NAME": "produtos-primario",
    }),
    ("PRODUCTS-REPLICA", os.path.join(ROOT, "products", "app.py"), {
        "PRODUCTS_PORT": PRODUCTS_REPLICA_PORT,
        "PRODUCTS_DATA_FILE": os.path.join(DATA, "products_replica.db"),
        "PRODUCTS_PEER_URL": PRODUCTS_URL,
        "PRODUCTS_NODE_NAME": "produtos-replica",
    }),
    ("ORDERS", os.path.join(ROOT, "orders", "app.py"), {}),
    ("GATEWAY", os.path.join(ROOT, "gateway", "app.py"), {}),
]

procs = []


def shutdown(*_):
    print("\nEncerrando servicos...")
    for name, p in procs:
        if p.poll() is None:
            p.terminate()
    sys.exit(0)


def ensure_certs():
    """Gera os certificados TLS se ainda nao existirem."""
    ca = os.path.join(ROOT, "certs", "ca.crt")
    if not os.path.exists(ca):
        print("Certificados TLS nao encontrados. Gerando...")
        subprocess.check_call([PY, os.path.join(ROOT, "scripts", "generate_certs.py")])


def main():
    ensure_certs()
    signal.signal(signal.SIGINT, shutdown)
    for name, script, extra in SERVICES:
        p = subprocess.Popen([PY, script], env=env_with(extra), cwd=ROOT)
        procs.append((name, p))
        print(f"  -> {name} iniciado (pid {p.pid})")
    print("\nTodos os servicos no ar. Acesse https://localhost:%s" % GATEWAY_PORT)
    print("Pressione Ctrl+C para encerrar.\n")
    for _, p in procs:
        p.wait()


if __name__ == "__main__":
    main()
