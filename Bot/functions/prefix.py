"""
functions/prefix.py
───────────────────
Helper centralizado de prefixo do bot.
O prefixo fica salvo em: db.get_document("bot_config") → { "prefix": "!" }

Como usar em qualquer lugar do bot:
    from functions.prefix import get_prefix, set_prefix, get_prefix_callable
"""

from functions.database import database as db

_DOC_KEY    = "custom_prefix"
_DEFAULT    = "!"


def get_prefix() -> str:
    """Retorna o prefixo atual salvo no banco."""
    config = db.get_document(_DOC_KEY) or {}
    return config.get("prefix", _DEFAULT)


def set_prefix(new_prefix: str) -> str:
    """Salva um novo prefixo no banco e retorna o valor salvo."""
    new_prefix = new_prefix.strip()
    if not new_prefix:
        raise ValueError("Prefixo não pode ser vazio.")
    if len(new_prefix) > 5:
        raise ValueError("Prefixo muito longo (máximo 5 caracteres).")

    config = db.get_document(_DOC_KEY) or {}
    config["prefix"] = new_prefix
    db.save_document(_DOC_KEY, config)
    return new_prefix


def get_prefix_callable(bot, message):
    """
    Callable para passar ao command_prefix do disnake/discord.py.
    Aceita o bot sendo mencionado (@bot) além do prefixo configurado.

    Uso:
        bot = commands.Bot(command_prefix=get_prefix_callable)
    """
    from disnake.ext.commands import when_mentioned_or
    return when_mentioned_or(get_prefix())(bot, message)