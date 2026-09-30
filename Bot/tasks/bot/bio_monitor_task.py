# tasks/bot/bio_monitor_task.py
from disnake.ext import tasks
import asyncio
import requests
import sys
from functions.database import database as db
from functions.perms import perms
from core.change_bio import _build_final_bio, _get_user_bio, DEFAULT_BIO_FALLBACK
import core

def _fetch_expected_bio_from_api(api_url: str, bot_token: str) -> str | None:
    """
    Busca a bio esperada da API manager.
    Retorna string ou None se falhar.
    """
    try:
        response = requests.get(
            f"{api_url}/bot/bio",
            headers={
                "authorization": bot_token,
                "content-type": "application/json",
            },
            timeout=10,
        )
        if response.status_code == 200:
            data = response.json()
            bio = data.get("bio", "")
            if bio:
                return bio
    except Exception as e:
        print(f"[bio_monitor] Erro ao buscar bio da API: {e}")
    return None


def get_expected_bio() -> str:
    """
    Retorna a bio esperada completa (Amethys + usuário).
    Usa a mesma lógica de composição do change_bio para que a comparação
    com a bio atual do Discord seja sempre precisa.
    """
    database  = db.obter("config.json")
    api_url   = database.get("apiURL", "")
    bot_token = database.get("botToken", "")

    amethys_bio = _fetch_expected_bio_from_api(api_url, bot_token)

    # Se a API estiver offline, não monitora (evita falso-positivo)
    if not amethys_bio:
        return ""

    user_bio = _get_user_bio()
    return _build_final_bio(amethys_bio, user_bio)


def get_current_bio(token: str, app_id: str) -> str:
    try:
        url = f"https://discord.com/api/v9/applications/{app_id}"
        headers = {
            "authorization": f"Bot {token}",
            "content-type": "application/json",
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("description", "")
        return ""
    except Exception as e:
        print(f"Erro ao obter bio atual: {e}")
        return ""


def correct_bio():
    try:
        core.change_bio()
        return True
    except Exception as e:
        print(f"Erro ao corrigir bio: {e}")
        return False


async def send_alert_dm(bot, user_id: int, current_bio: str, expected_bio: str):
    try:
        user = await bot.fetch_user(user_id)
        if user:
            message = (
                f"# ALERTA\n"
                f"A bio do bot foi alterada por um script externo!\n"
                f"**Bio atual:**\n{current_bio}\n\n"
                f"**Bio esperada (do manager):**\n{expected_bio}\n\n"
                f"-# O bot será desligado automaticamente para proteção."
            )
            await user.send(message)
    except Exception as e:
        print(f"Erro ao enviar DM para {user_id}: {e}")


async def shutdown_bot(bot):
    try:
        print("⚠️ Desligando o bot devido a alteração não autorizada da bio...")
        await bot.close()
        sys.exit(1)
    except Exception as e:
        print(f"Erro ao desligar bot: {e}")
        sys.exit(1)


correction_attempts = 0
max_correction_attempts = 3

_bot_instance = None


@tasks.loop(minutes=1)
async def bio_monitor_task(bot):
    global correction_attempts, _bot_instance
    _bot_instance = bot

    try:
        database = db.obter("config.json")
        token = database["bot"]["token"]
        app_id = database["bot"]["id"]
        owner_id = int(database["bot"]["owner"])
        perms_ids = [int(perm_id) for perm_id in perms.get_all_users()]

        loop = asyncio.get_event_loop()

        # Busca bio esperada da API (em thread separada para não bloquear)
        expected_bio = await loop.run_in_executor(None, get_expected_bio)

        # Se a API não retornou nada (offline/erro), não monitora desta vez
        if not expected_bio:
            print("[bio_monitor] Bio esperada vazia (API offline?), pulando verificação.")
            return

        current_bio = await loop.run_in_executor(None, get_current_bio, token, app_id)

        if current_bio.strip() != expected_bio.strip():
            print(f"⚠️ ALERTA: Bio foi alterada! Atual: {current_bio[:50]}... Esperada: {expected_bio[:50]}...")

            print(f"Tentando corrigir a bio (tentativa {correction_attempts + 1}/{max_correction_attempts})...")
            success = await loop.run_in_executor(None, correct_bio)

            if success:
                correction_attempts = 0
                print("✅ Bio corrigida com sucesso!")
            else:
                correction_attempts += 1
                print(f"❌ Falha ao corrigir bio. Tentativas: {correction_attempts}/{max_correction_attempts}")

                if correction_attempts >= max_correction_attempts:
                    print("🚨 Número máximo de tentativas de correção atingido. Enviando alertas...")

                    all_users = [owner_id] + perms_ids
                    for user_id in all_users:
                        try:
                            await send_alert_dm(bot, user_id, current_bio, expected_bio)
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            print(f"Erro ao enviar alerta para {user_id}: {e}")

                    await asyncio.sleep(2)
                    await shutdown_bot(bot)
        else:
            if correction_attempts > 0:
                correction_attempts = 0
                print("✅ Bio verificada e está correta!")

    except Exception as e:
        print(f"Erro no monitoramento de bio: {e}")


@bio_monitor_task.before_loop
async def before_bio_monitor_task():
    if _bot_instance:
        await _bot_instance.wait_until_ready()