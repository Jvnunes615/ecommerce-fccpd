"""Armazenamento baseado em SQLite (sqlite3 da stdlib).

Cada servico (e cada replica de Produtos) usa seu proprio arquivo .db,
simulando "uma base de dados por servico" tipica de microsservicos.

A tabela unica `items` guarda cada registro como JSON no campo `data`,
com `id` como chave primaria textual. Isso preserva a API da versao JSON
anterior (read_all / insert / find_by_id / upsert / write_all) sem
precisar de nenhuma dependencia externa.

Vantagens em relacao ao JSON plano:
  - Transacoes ACID via SQLite (sem risco de arquivo corrompido).
  - Escritas atomicas mesmo com concorrencia entre threads.
  - Consulta por id via indice em vez de varredura linear.
"""
import json
import os
import sqlite3
import threading


class SqliteStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.Lock()
        directory = os.path.dirname(db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS items "
                "(id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            conn.commit()

    # ---- leitura --------------------------------------------------------

    def read_all(self) -> list:
        with self._connect() as conn:
            rows = conn.execute("SELECT data FROM items").fetchall()
        return [json.loads(r["data"]) for r in rows]

    def find_by_id(self, item_id) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data FROM items WHERE id = ?", (str(item_id),)
            ).fetchone()
        return json.loads(row["data"]) if row else None

    # ---- escrita --------------------------------------------------------

    def insert(self, item: dict) -> dict:
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO items (id, data) VALUES (?, ?)",
                    (str(item["id"]), json.dumps(item, ensure_ascii=False)),
                )
                conn.commit()
        return item

    def upsert(self, item: dict) -> dict:
        """Insere ou substitui pelo id (idempotente). Usado na replicacao."""
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO items (id, data) VALUES (?, ?)",
                    (str(item["id"]), json.dumps(item, ensure_ascii=False)),
                )
                conn.commit()
        return item

    def write_all(self, items: list) -> list:
        """Substitui todo o conteudo atomicamente (usado no rollback de replicacao)."""
        with self._lock:
            with self._connect() as conn:
                conn.execute("DELETE FROM items")
                conn.executemany(
                    "INSERT INTO items (id, data) VALUES (?, ?)",
                    [(str(i["id"]), json.dumps(i, ensure_ascii=False)) for i in items],
                )
                conn.commit()
        return items
