import os
import time
import sys
import json
import asyncio
import traceback
from datetime import datetime, timezone

ERROR_WEBHOOK_URL = os.getenv("AMETHYS_STARTUP_WEBHOOK_URL", "")


def get_bot_info() -> tuple[str, str]:
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return config.get("botID", "N/A"), config.get("bot", {}).get("id", "N/A")
    except Exception:
        return "N/A", "N/A"


def send_startup_log(log_type: str, message: str, details: str = None, color: int = 0x3498db):
    """Envio síncrono de log para webhook — usado SOMENTE na inicialização."""
    if not ERROR_WEBHOOK_URL:
        return
    try:
        import requests

        bot_id, bot_discord_id = get_bot_info()
        icons = {
            "vlan_error":    "🔴",
            "config_error":  "🟠",
            "startup_error": "❌",
            "waiting":       "⏳",
            "success":       "✅",
            "info":          "ℹ️",
        }
        icon = icons.get(log_type, "📋")

        embed = {
            "title":       f"🤖 Bot: {bot_id} | ID: {bot_discord_id}",
            "description": f"{icon} **{message}**",
            "color":       color,
            "timestamp":   datetime.now(timezone.utc).isoformat(),
            "fields":      [],
            "footer":      {"text": f"Startup Log • {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"},
        }
        if details:
            embed["fields"].append({
                "name":   "📝 Detalhes",
                "value":  f"```{details[:1000]}```",
                "inline": False,
            })

        payload = {
            "embeds":   [embed],
            "username": f"{bot_id} - Startup Monitor",
        }

        for attempt in range(3):
            try:
                response = requests.post(ERROR_WEBHOOK_URL, json=payload, timeout=10)
                if response.status_code in [200, 204]:
                    return
                if response.status_code == 429:
                    time.sleep(5)
                    continue
            except Exception:
                if attempt < 2:
                    time.sleep(2)

    except Exception as e:
        print(f"[WEBHOOK] Erro ao enviar log: {e}")


def check_vlan_connection() -> bool:
    """
    Verifica conexão com MongoDB de forma síncrona (usada apenas no startup).
    Timeout curto para não travar o boot.
    """
    try:
        import pymongo

        with open("configs/config_mongo.json", "r", encoding="utf-8") as f:
            mongo_config = json.load(f)

        mongo_url = mongo_config.get("mongoURL")
        client    = pymongo.MongoClient(
            mongo_url,
            serverSelectionTimeoutMS=3000,   # reduzido de 5000 → 3000 ms
            connectTimeoutMS=3000,
            socketTimeoutMS=3000,
        )
        client.admin.command("ping")
        client.close()
        return True
    except Exception:
        return False


BACKUP_FILE = "backup/database_backup.json"


def has_local_backup() -> bool:
    """Verifica se existe um backup local válido para modo offline."""
    try:
        import os
        if not os.path.exists(BACKUP_FILE):
            return False
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return bool(data)
    except Exception:
        return False


def activate_offline_mode():
    """Ativa o modo offline da database usando o backup local."""
    # Importamos aqui porque ainda não chegamos na ETAPA 2
    from functions.database import database as db
    db.set_offline_mode(True)
    print("[OFFLINE] Modo offline ativado com sucesso.")


def wait_for_vlan_or_use_backup():
    """
    Se a VLAN estiver offline:
      - Se houver backup local → inicia em modo offline imediatamente.
      - Se não houver backup  → aguarda a VLAN como antes.
    """
    backup_exists = has_local_backup()

    if backup_exists:
        print("=" * 60)
        print("[VLAN DESATIVADA] Backup local encontrado.")
        print("[OFFLINE] Iniciando bot em modo offline com dados do backup local.")
        print("=" * 60)
        sys.stdout.flush()

        send_startup_log(
            "vlan_error",
            "VLAN DESATIVADA — Modo Offline Ativado",
            f"Backup local encontrado em '{BACKUP_FILE}'.\n"
            "O bot iniciará em modo offline. Quando a VLAN/MongoDB voltar, "
            "as alterações feitas offline serão sincronizadas automaticamente.",
            color=0xe67e22,
        )
        # Modo offline será ativado na ETAPA 2 após importar os módulos
        return "offline"

    else:
        print("=" * 60)
        print("[VLAN DESATIVADA] Nenhum backup local encontrado.")
        print("[AGUARDANDO] Verificando a cada 30 segundos...")
        print("=" * 60)
        sys.stdout.flush()

        send_startup_log(
            "vlan_error",
            "VLAN DESATIVADA",
            "A VLAN do aplicativo está desativada.\n"
            "Não é possível conectar ao MongoDB e não há backup local.\n"
            "Aguardando VLAN ser ativada...",
            color=0xe74c3c,
        )

        while True:
            time.sleep(30)
            print("[VLAN] Verificando conexão...")
            sys.stdout.flush()
            if check_vlan_connection():
                print("[VLAN] Conexão estabelecida! Continuando...")
                sys.stdout.flush()
                send_startup_log("success", "VLAN Ativada", "Conexão com MongoDB estabelecida.", color=0x2ecc71)
                return "online"
            else:
                print("[VLAN DESATIVADA] Próxima verificação em 30s...")
                sys.stdout.flush()


# ============================================================
# ETAPA 1: Verificar VLAN/MongoDB
# ============================================================
_startup_mode = "online"
if not check_vlan_connection():
    _startup_mode = wait_for_vlan_or_use_backup()


# ============================================================
# ETAPA 2: Importar módulos principais
# ============================================================
try:
    import core
    from functions.emojis import emojis
    from functions.database import database
    from functions.utils import utils
    from core.server_protection import apply_server_protection

    # Ativa modo offline se a VLAN estava down mas havia backup local
    if _startup_mode == "offline":
        database.set_offline_mode(True)

except Exception as e:
    error_details = traceback.format_exc()
    print(f"[ERRO] Falha ao importar módulos: {e}")
    print(error_details)
    send_startup_log("startup_error", "Erro ao importar módulos", error_details, color=0xe74c3c)
    while True:
        print("[ERRO] Bot em estado de erro. Aguardando correção...")
        time.sleep(60)


def is_bot_configured() -> bool:
    try:
        config = database.obter("config.json")

        if config.get("saveConfig", False):
            try:
                from core.create_bot import _obter_info
                info  = _obter_info()
                token = info.get("token")
                server = info.get("server")
                if not token or token in ("", "null", "undefined"):
                    return False
                if not server or server in ("", "null", "undefined"):
                    return False
                return True
            except Exception as e:
                print(f"[CONFIG] Erro ao buscar configuração da API: {e}")
                return False

        bot_config = config.get("bot", {})
        token  = bot_config.get("token")
        server = bot_config.get("server")

        if not token or token in ("", "null", "undefined"):
            return False
        if not server or server in ("", "null", "undefined"):
            return False
        return True

    except Exception as e:
        print(f"[CONFIG] Erro ao verificar configuração: {e}")
        return False


def wait_for_configuration():
    print("=" * 60)
    print("[AGUARDANDO CONFIGURAÇÃO] Aguardando token e servidor...")
    print("Verificando a cada 30 segundos...")
    print("=" * 60)
    sys.stdout.flush()

    send_startup_log(
        "config_error",
        "Aguardando Configuração",
        "O bot ainda não foi configurado pelo usuário.",
        color=0xe67e22,
    )

    while True:
        time.sleep(30)
        print("[CONFIG] Verificando configuração...")
        sys.stdout.flush()
        if is_bot_configured():
            print("[CONFIG] Bot configurado! Iniciando...")
            sys.stdout.flush()
            send_startup_log("success", "Bot Configurado", "Iniciando bot...", color=0x2ecc71)
            return
        else:
            print("[CONFIG] Ainda não configurado. Próxima verificação em 30s...")
            sys.stdout.flush()


# ============================================================
# ETAPA 3: Verificar configuração
# ============================================================
if not is_bot_configured():
    wait_for_configuration()


# ============================================================
# ETAPA 4: Inicializar o bot
# ============================================================
try:
    bot, token, id = core.create_bot()

    # Armazena no bot para uso assíncrono no on_ready
    bot._init_token = token
    bot._init_app_id = id

    database.initialize_database_if_needed()
    database.verify_and_create_missing_documents()

    apply_server_protection(bot)

    bot.load_extension("modules")
    bot.load_extension("commands")
    bot.load_extension("events")
    bot.load_extension("tasks")

    async def _log_ram_usage():
        import psutil, os
        process = psutil.Process(os.getpid())
        while True:
            await asyncio.sleep(180)
            mem = process.memory_info().rss / 1024 / 1024
            print(f"[RAM] Uso atual: {mem:.1f} MB")

    if __name__ == "__main__":
        #from core.enable_intents import enable_intents
        #enable_intents(token, id)
        core.change_bio()
        loop = asyncio.get_event_loop()
        loop.create_task(_log_ram_usage())
        bot.run(token)

except Exception as e:
    error_details = traceback.format_exc()
    print(f"[ERRO FATAL] Erro ao inicializar o bot: {e}")
    print(error_details)
    send_startup_log("startup_error", "Erro Fatal na Inicialização", error_details, color=0xe74c3c)
    while True:
        print("[ERRO] Bot em estado de erro. Aguardando correção...")
        sys.stdout.flush()
        time.sleep(60)