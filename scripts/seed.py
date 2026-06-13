"""Popula o sistema com um usuario admin e alguns produtos de exemplo.

Requer os servicos no ar (rode antes: python scripts/start_all.py).
Usa o API Gateway como ponto de entrada.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from common import config, http_client  # noqa: E402
from common.tls import scheme as _scheme  # noqa: E402

GATEWAY = f"{_scheme()}://localhost:{config.get('GATEWAY_PORT', '8080')}"

ADMIN = {"name": "Admin", "email": "admin@fccpd.com", "password": "admin123", "role": "admin"}
PRODUCTS = [
    {"name": "Teclado Mecanico", "price": 249.90, "stock": 15, "description": "Switches azuis, ABNT2."},
    {"name": "Mouse Gamer", "price": 159.90, "stock": 30, "description": "16000 DPI, RGB."},
    {"name": "Monitor 27\" 144Hz", "price": 1299.00, "stock": 8, "description": "IPS, 1ms."},
    {"name": "Headset 7.1", "price": 329.90, "stock": 12, "description": "Som surround virtual."},
]


def main():
    print("Registrando admin...")
    r = http_client.post(f"{GATEWAY}/users/register", json_body=ADMIN)
    if r.status not in (201, 409):
        print("  Falha:", r.status, r.body)
    print("Login admin...")
    r = http_client.post(f"{GATEWAY}/users/login",
                         json_body={"email": ADMIN["email"], "password": ADMIN["password"]})
    if not r.ok:
        print("  Nao foi possivel logar:", r.body)
        return
    token = r.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    for p in PRODUCTS:
        r = http_client.post(f"{GATEWAY}/products", json_body=p, headers=headers)
        status = "OK" if r.ok else f"FALHA ({r.status})"
        print(f"  Produto '{p['name']}': {status}")

    print("\nSeed concluido. Admin: admin@fccpd.com / admin123")


if __name__ == "__main__":
    main()
