from functions.database import database as db
from functions.prefix import get_prefix
from disnake.ext import commands
import disnake
import requests


def _get_prefix(bot, message):
    return commands.when_mentioned_or(get_prefix())(bot, message)


def _obter_info() -> dict:
    """Busca informações do bot na API da plataforma."""
    config = db.obter("config.json")

    api_url  = config.get("apiURL")
    bot_id   = config.get("botID")
    bot_token = config.get("botToken")

    if not api_url or not bot_id or not bot_token:
        raise RuntimeError(
            "[create_bot] apiURL / botID / botToken não configurados em config.json"
        )

    headers  = {"authorization": bot_token, "content-type": "application/json"}
    url      = f"{api_url}/api/bot/{bot_id}/info"

    try:
        response = requests.get(url, headers=headers, timeout=15)
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(f"[create_bot] Não foi possível conectar à API ({url}): {exc}")

    if response.status_code == 200:
        return response.json()

    raise RuntimeError(
        f"[create_bot] Erro na requisição à API. "
        f"Status: {response.status_code} | Body: {response.text[:200]}"
    )


def _salvar_info(info: dict) -> None:
    """Salva as informações obtidas da API no config.json local."""
    config = db.obter("config.json")

    config["bot"] = {k: info[k] for k in ("token", "owner", "id", "perms", "server") if k in info}

    if "version" in info:
        config["version"] = info["version"]

    db.salvar("config.json", config)


def create_bot() -> tuple[commands.Bot, str, str]:
    config = db.obter("config.json")

    # Se saveConfig estiver ativo, busca dados frescos da API e persiste localmente.
    # Caso contrário, usa o que já está salvo em config["bot"].
    if config.get("saveConfig", False):
        info = _obter_info()
        _salvar_info(info)
        # Recarrega para garantir que usamos os dados recém-salvos
        config = db.obter("config.json")

    bot_info = config.get("bot", {})

    if not bot_info.get("token"):
        raise RuntimeError(
            "[create_bot] Token do bot não encontrado em config.json. "
            "Configure saveConfig=true ou preencha bot.token manualmente."
        )

    intents = disnake.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True

    bot = commands.Bot(
        command_prefix=_get_prefix,
        intents=intents,
        help_command=None,
        reload=True,
    )

    return bot, bot_info["token"], bot_info["id"]