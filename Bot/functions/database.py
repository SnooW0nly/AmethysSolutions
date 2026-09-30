import json
import os
import time
import threading
import copy
from typing import Optional, Any
from connections.mongo_db import collection as bot_collection


# ============================================================
# Modo offline / backup local
# ============================================================

_BACKUP_FILE       = "backup/database_backup.json"
_OFFLINE_QUEUE_FILE = "backup/offline_queue.json"

_offline_mode       = False
_offline_lock       = threading.Lock()
_offline_data: dict = {}          # cópia em memória do backup local
_offline_queue_lock = threading.Lock()


def _ensure_backup_dir():
    os.makedirs("backup", exist_ok=True)


def _load_backup_into_memory():
    """Carrega o arquivo de backup para _offline_data (chamado no startup offline)."""
    global _offline_data
    try:
        with open(_BACKUP_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Remove metadados internos antes de usar
        _offline_data = {k: v for k, v in raw.items() if not k.startswith("_backup_meta")}
        print(f"[DB-OFFLINE] Backup local carregado: {len(_offline_data)} documento(s).")
    except FileNotFoundError:
        print("[DB-OFFLINE] Nenhum backup local encontrado. Iniciando com dados vazios.")
        _offline_data = {}
    except json.JSONDecodeError as e:
        print(f"[DB-OFFLINE] Backup corrompido: {e}. Iniciando com dados vazios.")
        _offline_data = {}


def _enqueue_offline_op(op: str, doc_id: str, data: Any = None):
    """Adiciona uma operação à fila offline para ser sincronizada depois."""
    _ensure_backup_dir()
    entry = {"op": op, "id": doc_id, "ts": time.time()}
    if data is not None:
        entry["data"] = data

    with _offline_queue_lock:
        try:
            with open(_OFFLINE_QUEUE_FILE, "r", encoding="utf-8") as f:
                queue = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            queue = []

        queue.append(entry)

        tmp = _OFFLINE_QUEUE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(queue, f, indent=2, ensure_ascii=False)
        os.replace(tmp, _OFFLINE_QUEUE_FILE)


# ============================================================
# Cache em memória (para modo online)
# ============================================================

class _CacheEntry:
    __slots__ = ("data", "expiry")

    def __init__(self, data: Any, expiry: float):
        self.data = data
        self.expiry = expiry

    def is_valid(self, now: float) -> bool:
        return now < self.expiry


class database:
    _cache: dict[str, _CacheEntry] = {}
    _cache_lock = threading.Lock()

    _DEFAULT_TTL = 60
    _LONG_TTL = 300
    _NOT_FOUND_TTL = 10
    _CLEANUP_INTERVAL = 120

    _long_cache_docs = {"custom_mode", "custom_colors", "canais"}

    _last_cleanup: float = 0.0

    # ------------------------------------------------------------------
    # Controle de modo offline
    # ------------------------------------------------------------------

    @staticmethod
    def is_offline_mode() -> bool:
        with _offline_lock:
            return _offline_mode

    @staticmethod
    def set_offline_mode(value: bool):
        global _offline_mode
        with _offline_lock:
            _offline_mode = value
        if value:
            _load_backup_into_memory()
            print("[DB-OFFLINE] Modo OFFLINE ativado. Usando backup local.")
        else:
            print("[DB-OFFLINE] Modo ONLINE restaurado.")

    # ------------------------------------------------------------------
    # Helpers internos de cache
    # ------------------------------------------------------------------

    @classmethod
    def _ttl_for(cls, config_type: str) -> float:
        return cls._LONG_TTL if config_type in cls._long_cache_docs else cls._DEFAULT_TTL

    @classmethod
    def _needs_deepcopy(cls, data: Any) -> bool:
        return isinstance(data, (dict, list))

    @classmethod
    def _safe_copy(cls, data: Any) -> Any:
        if cls._needs_deepcopy(data):
            return copy.deepcopy(data)
        return data

    @classmethod
    def _cache_get(cls, key: str, now: float) -> tuple[bool, Any]:
        with cls._cache_lock:
            entry = cls._cache.get(key)
            if entry is None or not entry.is_valid(now):
                return False, None
            raw = entry.data
        return True, cls._safe_copy(raw)

    @classmethod
    def _cache_set(cls, key: str, data: Any, now: float, ttl: float):
        snapshot = cls._safe_copy(data)
        entry = _CacheEntry(snapshot, now + ttl)
        with cls._cache_lock:
            cls._cache[key] = entry
            cls._maybe_cleanup(now)

    @classmethod
    def _maybe_cleanup(cls, now: float):
        if now - cls._last_cleanup < cls._CLEANUP_INTERVAL:
            return
        cls._cache = {k: v for k, v in cls._cache.items() if v.is_valid(now)}
        cls._last_cleanup = now

    @staticmethod
    def _strip_id(document: dict) -> Any:
        doc = {k: v for k, v in document.items() if k != "_id"}
        if len(doc) == 1 and "items" in doc:
            return doc["items"]
        return doc

    @staticmethod
    def _to_mongo_doc(config_type: str, data: Any) -> tuple[dict, Any]:
        if isinstance(data, list):
            return {"_id": config_type, "items": data}, data
        doc = {**data, "_id": config_type}
        cache_data = database._strip_id(doc)
        return doc, cache_data

    # ------------------------------------------------------------------
    # API de arquivos (mantida por compatibilidade)
    # ------------------------------------------------------------------

    @staticmethod
    def obter(filename: str) -> dict:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def salvar(filename: str, data: dict):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # ------------------------------------------------------------------
    # CRUD principal (com fallback offline)
    # ------------------------------------------------------------------

    @staticmethod
    def get_document(config_type: str) -> Any:
        # ── MODO OFFLINE ──────────────────────────────────────────────
        if database.is_offline_mode():
            raw = _offline_data.get(config_type, {})
            return database._safe_copy(raw)

        # ── MODO ONLINE ───────────────────────────────────────────────
        now = time.time()
        hit, cached = database._cache_get(config_type, now)
        if hit:
            return cached

        try:
            document = bot_collection.find_one({"_id": config_type})
        except Exception:
            return {}

        if document:
            result = database._strip_id(document)
            database._cache_set(config_type, result, now, database._ttl_for(config_type))
            return database._safe_copy(result)

        database._cache_set(config_type, {}, now, database._NOT_FOUND_TTL)
        return {}

    @staticmethod
    def get_documents(query: dict | None = None) -> list[dict]:
        if database.is_offline_mode():
            # Filtragem básica em memória — sem suporte a queries complexas
            if not query:
                return [{"_id": k, **v} if isinstance(v, dict) else {"_id": k, "items": v}
                        for k, v in _offline_data.items()]
            return []

        try:
            docs = list(bot_collection.find(query or {}))
            for doc in docs:
                doc.pop("_id", None)
            return docs
        except Exception:
            return []

    @staticmethod
    def get_documents_cached(ids: list[str]) -> dict[str, Any]:
        if database.is_offline_mode():
            return {doc_id: database._safe_copy(_offline_data.get(doc_id, {})) for doc_id in ids}

        now = time.time()
        result: dict[str, Any] = {}
        missing: list[str] = []

        for doc_id in ids:
            hit, cached = database._cache_get(doc_id, now)
            if hit:
                result[doc_id] = cached
            else:
                missing.append(doc_id)

        if missing:
            try:
                docs = list(bot_collection.find({"_id": {"$in": missing}}))
                found_ids = set()
                for doc in docs:
                    doc_id = doc["_id"]
                    found_ids.add(doc_id)
                    data = database._strip_id(doc)
                    database._cache_set(doc_id, data, now, database._ttl_for(doc_id))
                    result[doc_id] = database._safe_copy(data)

                for doc_id in missing:
                    if doc_id not in found_ids:
                        database._cache_set(doc_id, {}, now, database._NOT_FOUND_TTL)
                        result[doc_id] = {}
            except Exception:
                for doc_id in missing:
                    result.setdefault(doc_id, {})

        return result

    @staticmethod
    def save_document(config_type: str, query_or_data=None, data=None):
        if data is None:
            data = query_or_data

        # ── MODO OFFLINE ──────────────────────────────────────────────
        if database.is_offline_mode():
            _offline_data[config_type] = database._safe_copy(data)
            _enqueue_offline_op("save", config_type, database._safe_copy(data))
            return

        # ── MODO ONLINE ───────────────────────────────────────────────
        mongo_doc, cache_data = database._to_mongo_doc(config_type, data)

        try:
            bot_collection.replace_one({"_id": config_type}, mongo_doc, upsert=True)
        except Exception:
            raise

        now = time.time()
        database._cache_set(config_type, cache_data, now, database._ttl_for(config_type))

    @staticmethod
    def save_documents_bulk(items: dict[str, Any]):
        if not items:
            return

        # ── MODO OFFLINE ──────────────────────────────────────────────
        if database.is_offline_mode():
            for config_type, data in items.items():
                _offline_data[config_type] = database._safe_copy(data)
                _enqueue_offline_op("save", config_type, database._safe_copy(data))
            return

        # ── MODO ONLINE ───────────────────────────────────────────────
        from pymongo import ReplaceOne

        ops = []
        cache_updates: list[tuple[str, Any]] = []

        for config_type, data in items.items():
            mongo_doc, cache_data = database._to_mongo_doc(config_type, data)
            ops.append(ReplaceOne({"_id": config_type}, mongo_doc, upsert=True))
            cache_updates.append((config_type, cache_data))

        bot_collection.bulk_write(ops, ordered=False)

        now = time.time()
        for config_type, cache_data in cache_updates:
            database._cache_set(config_type, cache_data, now, database._ttl_for(config_type))

    @staticmethod
    def delete_document(config_type: str):
        # ── MODO OFFLINE ──────────────────────────────────────────────
        if database.is_offline_mode():
            _offline_data.pop(config_type, None)
            _enqueue_offline_op("delete", config_type)
            return

        # ── MODO ONLINE ───────────────────────────────────────────────
        try:
            bot_collection.delete_one({"_id": config_type})
        finally:
            with database._cache_lock:
                database._cache.pop(config_type, None)

    @staticmethod
    def delete_documents(query: dict):
        if database.is_offline_mode():
            # Sem suporte a queries complexas no modo offline
            print("[DB-OFFLINE] delete_documents ignorado no modo offline.")
            return

        try:
            docs = list(bot_collection.find(query, {"_id": 1}))
            ids_to_delete = [doc["_id"] for doc in docs]
            bot_collection.delete_many(query)
        finally:
            with database._cache_lock:
                for doc_id in ids_to_delete:
                    database._cache.pop(doc_id, None)

    # ------------------------------------------------------------------
    # Inicialização
    # ------------------------------------------------------------------

    @staticmethod
    def initialize_database_if_needed():
        if database.is_offline_mode():
            print("[DB-OFFLINE] initialize_database_if_needed ignorado (modo offline).")
            return

        if bot_collection.find_one({"_id": "_meta_initialization"}):
            return

        print("Primeira inicialização detectada. Populando com valores padrão...")

        try:
            with open("database_template.json", "r", encoding="utf-8") as f:
                all_configs: dict = json.load(f)
        except FileNotFoundError:
            print("ERRO: 'database_template.json' não encontrado!")
            return
        except json.JSONDecodeError as e:
            print(f"ERRO: JSON inválido no template: {e}")
            return

        database.save_documents_bulk(all_configs)
        print(f"{len(all_configs)} configuração(ões) inserida(s).")

        bot_collection.insert_one({
            "_id": "_meta_initialization",
            "initialized_at": os.path.getmtime("database_template.json"),
        })
        print("Inicialização concluída.")

    @staticmethod
    def verify_and_create_missing_documents():
        if database.is_offline_mode():
            print("[DB-OFFLINE] verify_and_create_missing_documents ignorado (modo offline).")
            return

        try:
            with open("database_template.json", "r", encoding="utf-8") as f:
                all_configs: dict = json.load(f)
        except FileNotFoundError:
            print("[MongoDB] ERRO: 'database_template.json' não encontrado!")
            return
        except json.JSONDecodeError as e:
            print(f"[MongoDB] ERRO: JSON inválido no template: {e}")
            return
        except Exception as e:
            print(f"[MongoDB] ERRO ao ler template: {e}")
            return

        template_ids = list(all_configs.keys())

        existing_ids = {
            doc["_id"]
            for doc in bot_collection.find({"_id": {"$in": template_ids}}, {"_id": 1})
        }

        missing = {k: v for k, v in all_configs.items() if k not in existing_ids}

        if not missing:
            print("[MongoDB] Todos os documentos do template estão presentes.")
            return

        database.save_documents_bulk(missing)
        print(f"[MongoDB] {len(missing)} documento(s) faltante(s) criado(s): {list(missing.keys())}")

    # ------------------------------------------------------------------
    # Cache utils
    # ------------------------------------------------------------------

    @staticmethod
    def clear_cache(config_type: Optional[str] = None):
        with database._cache_lock:
            if config_type:
                database._cache.pop(config_type, None)
            else:
                database._cache.clear()

    @staticmethod
    def get_cache_stats() -> dict:
        now = time.time()
        with database._cache_lock:
            total = len(database._cache)
            valid = sum(1 for e in database._cache.values() if e.is_valid(now))
            keys  = list(database._cache.keys())
        return {
            "total_entries":     total,
            "valid_entries":     valid,
            "expired_entries":   total - valid,
            "cached_documents":  keys,
            "offline_mode":      database.is_offline_mode(),
            "offline_docs":      len(_offline_data) if database.is_offline_mode() else 0,
        }
