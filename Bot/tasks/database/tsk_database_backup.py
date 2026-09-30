"""
tasks/database/tsk_database_backup.py

Responsabilidades:
  1. Backup periódico: salva todos os documentos do MongoDB num JSON local.
  2. Monitor de reconexão: quando a VLAN/MongoDB voltar, sincroniza todas as
     escritas pendentes (queue offline) de volta para o MongoDB.
"""

import asyncio
import json
import os
import time
import threading
import copy
from datetime import datetime, timezone
from disnake.ext import tasks, commands

# Arquivo onde o backup local é gravado
BACKUP_FILE  = "backup/database_backup.json"
# Arquivo com a fila de operações feitas enquanto estava offline
OFFLINE_QUEUE_FILE = "backup/offline_queue.json"

BACKUP_INTERVAL_MINUTES = 30       # frequência do backup completo
RECONNECT_CHECK_SECONDS  = 30      # frequência para checar se o MongoDB voltou


# ---------------------------------------------------------------------------
# Helpers de I/O (síncronos — rodam em executor para não bloquear o loop)
# ---------------------------------------------------------------------------

def _ensure_backup_dir():
    os.makedirs("backup", exist_ok=True)


def _load_json_file(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _mongo_safe(obj):
    """
    Converte recursivamente tipos do MongoDB / Python que não são
    serializáveis em JSON para representações seguras:
      bytes      → hex string prefixado com "b64:"
      datetime   → ISO-8601
      ObjectId   → string
      Decimal128 → float
      qualquer outro não-serializável → str()
    """
    if isinstance(obj, dict):
        return {k: _mongo_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_mongo_safe(v) for v in obj]
    if isinstance(obj, bytes):
        import base64
        return "b64:" + base64.b64encode(obj).decode("ascii")
    if isinstance(obj, datetime):
        return obj.isoformat()
    # bson types (importação lazy para não quebrar se bson não estiver instalado)
    try:
        from bson import ObjectId, Decimal128
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, Decimal128):
            return float(obj.to_decimal())
    except ImportError:
        pass
    # fallback para qualquer outro tipo estranho
    if not isinstance(obj, (str, int, float, bool, type(None))):
        return str(obj)
    return obj


def _save_json_file(path: str, data):
    _ensure_backup_dir()
    safe = _mongo_safe(data)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(safe, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)          # atômica — evita corrupção em crash


# ---------------------------------------------------------------------------
# Backup completo (snapshot de todos os documentos do MongoDB)
# ---------------------------------------------------------------------------

def _do_full_backup() -> tuple[bool, int]:
    """
    Lê todos os documentos da collection e salva em BACKUP_FILE.
    Retorna (sucesso, quantidade_de_docs).
    """
    try:
        from connections.mongo_db import collection as bot_collection
        docs = list(bot_collection.find({}))
        snapshot: dict = {}
        for doc in docs:
            doc_id = str(doc.get("_id", ""))
            clean  = {k: v for k, v in doc.items() if k != "_id"}
            # Se tem só "items", achata para lista (espelho do _strip_id)
            if len(clean) == 1 and "items" in clean:
                snapshot[doc_id] = clean["items"]
            else:
                snapshot[doc_id] = clean

        meta = {
            "_backup_meta": {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_docs": len(snapshot),
            }
        }
        _save_json_file(BACKUP_FILE, {**meta, **snapshot})
        return True, len(snapshot)
    except Exception as e:
        print(f"[DB-BACKUP] Erro ao fazer backup: {e}")
        return False, 0


# ---------------------------------------------------------------------------
# Sync da fila offline → MongoDB
# ---------------------------------------------------------------------------

def _load_offline_queue() -> list[dict]:
    return _load_json_file(OFFLINE_QUEUE_FILE, [])


def _save_offline_queue(queue: list[dict]):
    _save_json_file(OFFLINE_QUEUE_FILE, queue)


def _clear_offline_queue():
    _save_json_file(OFFLINE_QUEUE_FILE, [])


def _do_sync_offline_queue() -> tuple[bool, int]:
    """
    Aplica todas as operações da fila offline no MongoDB.
    Retorna (sucesso, total_sincronizados).
    """
    queue = _load_offline_queue()
    if not queue:
        return True, 0

    try:
        from connections.mongo_db import collection as bot_collection
        from pymongo import ReplaceOne, DeleteOne

        ops_replace = []
        ops_delete  = []
        synced = 0

        for op in queue:
            kind      = op.get("op")
            doc_id    = op.get("id")
            data      = op.get("data")
            timestamp = op.get("ts", 0)

            if kind == "save" and doc_id and data is not None:
                if isinstance(data, list):
                    mongo_doc = {"_id": doc_id, "items": data}
                else:
                    mongo_doc = {**data, "_id": doc_id}
                ops_replace.append(ReplaceOne({"_id": doc_id}, mongo_doc, upsert=True))
                synced += 1

            elif kind == "delete" and doc_id:
                ops_delete.append(DeleteOne({"_id": doc_id}))
                synced += 1

        all_ops = ops_replace + ops_delete
        if all_ops:
            bot_collection.bulk_write(all_ops, ordered=True)

        _clear_offline_queue()
        return True, synced

    except Exception as e:
        print(f"[DB-BACKUP] Erro ao sincronizar fila offline: {e}")
        return False, 0


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class DatabaseBackupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()
        _ensure_backup_dir()

    # ------------------------------------------------------------------
    # on_ready: inicia tasks
    # ------------------------------------------------------------------

    @commands.Cog.listener("on_ready")
    async def on_ready(self):
        if not self.backup_task.is_running():
            self.backup_task.start()
        if not self.reconnect_monitor.is_running():
            self.reconnect_monitor.start()

    # ------------------------------------------------------------------
    # Task 1 — Backup periódico completo
    # ------------------------------------------------------------------

    @tasks.loop(minutes=BACKUP_INTERVAL_MINUTES)
    async def backup_task(self):
        from functions.database import database as db

        # Não faz backup se está em modo offline (o backup local JÁ é a fonte)
        if db.is_offline_mode():
            return

        async with self._lock:
            loop = asyncio.get_event_loop()
            ok, total = await loop.run_in_executor(None, _do_full_backup)
            if ok:
                print(f"[DB-BACKUP] Backup completo: {total} documentos salvos em '{BACKUP_FILE}'")
            else:
                print("[DB-BACKUP] Falha no backup periódico.")

    @backup_task.before_loop
    async def before_backup(self):
        await self.bot.wait_until_ready()
        # Primeiro backup logo após o bot ficar pronto
        await asyncio.sleep(10)

    # ------------------------------------------------------------------
    # Task 2 — Monitor de reconexão (sincroniza queue offline)
    # ------------------------------------------------------------------

    @tasks.loop(seconds=RECONNECT_CHECK_SECONDS)
    async def reconnect_monitor(self):
        from functions.database import database as db

        if not db.is_offline_mode():
            return   # já online, nada a fazer

        # Tenta reconectar
        loop   = asyncio.get_event_loop()
        online = await loop.run_in_executor(None, _check_mongo_connection)
        if not online:
            return

        # MongoDB voltou → sincroniza
        async with self._lock:
            print("[DB-BACKUP] MongoDB reconectado! Iniciando sincronização da fila offline...")
            ok, total = await loop.run_in_executor(None, _do_sync_offline_queue)
            if ok:
                # Volta ao modo online DEPOIS de sincronizar com sucesso
                db.set_offline_mode(False)
                # Faz backup imediato para refletir o estado atual
                await loop.run_in_executor(None, _do_full_backup)
                print(f"[DB-BACKUP] Sincronização concluída: {total} operação(ões) enviada(s). Modo online restaurado.")
            else:
                print("[DB-BACKUP] Falha na sincronização. Tentará novamente no próximo ciclo.")

    @reconnect_monitor.before_loop
    async def before_reconnect_monitor(self):
        await self.bot.wait_until_ready()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def cog_unload(self):
        self.backup_task.cancel()
        self.reconnect_monitor.cancel()


# ---------------------------------------------------------------------------
# Helper de checagem de conexão (síncrono)
# ---------------------------------------------------------------------------

def _check_mongo_connection() -> bool:
    try:
        import pymongo, json
        with open("configs/config_mongo.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        client = pymongo.MongoClient(
            cfg.get("mongoURL"),
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
            socketTimeoutMS=3000,
        )
        client.admin.command("ping")
        client.close()
        return True
    except Exception:
        return False


def setup(bot: commands.Bot):
    bot.add_cog(DatabaseBackupCog(bot))
