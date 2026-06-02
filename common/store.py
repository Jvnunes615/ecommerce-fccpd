"""Armazenamento simples baseado em arquivo JSON.

Cada servico (e cada replica de Produtos) usa seu proprio arquivo, simulando
"uma base de dados por servico" tipica de uma arquitetura de microsservicos.
Um Lock protege contra escritas concorrentes no mesmo processo.
"""
import json
import os
import threading


class JsonStore:
    def __init__(self, file_path):
        self.file_path = file_path
        self._lock = threading.Lock()
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
        if not os.path.exists(file_path):
            self._write([])

    def _write(self, items):
        with open(self.file_path, "w", encoding="utf-8") as fh:
            json.dump(items, fh, indent=2, ensure_ascii=False)

    def read_all(self):
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def write_all(self, items):
        with self._lock:
            self._write(items)
        return items

    def insert(self, item):
        with self._lock:
            items = self.read_all()
            items.append(item)
            self._write(items)
        return item

    def find_by_id(self, item_id):
        for item in self.read_all():
            if str(item.get("id")) == str(item_id):
                return item
        return None

    def upsert(self, item):
        """Insere ou substitui pelo id (idempotente). Usado na replicacao."""
        with self._lock:
            items = self.read_all()
            for idx, existing in enumerate(items):
                if str(existing.get("id")) == str(item.get("id")):
                    items[idx] = item
                    break
            else:
                items.append(item)
            self._write(items)
        return item
