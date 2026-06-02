"""Carrega variaveis de ambiente do arquivo .env (sem dependencias externas).

Permite importar a configuracao em qualquer servico. Tambem adiciona a raiz
do projeto ao sys.path para que `from common import ...` funcione ao rodar
cada servico individualmente.
"""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def load_env(path=None):
    path = path or os.path.join(PROJECT_ROOT, ".env")
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            # Variaveis ja definidas no ambiente tem prioridade (ex: docker).
            if key and key not in os.environ:
                os.environ[key] = value


load_env()


def get(name, default=None):
    return os.environ.get(name, default)


def get_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default
