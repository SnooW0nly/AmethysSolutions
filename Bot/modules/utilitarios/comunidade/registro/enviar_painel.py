"""
modules/utilitarios/comunidade/registro/enviar_painel.py

Envia o painel de registro automático em um canal (botão público).
Chamado pelo painel de config quando o admin quiser postar.
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from .helpers import carregar_config, accent, get_color, BUTTON_STYLE_MAP, _mode
from commands.admin.anunciar.builder import Builder


async def enviar_painel_registro(
    channel: disnake.TextChannel,
    guild: disnake.Guild,
) -> disnake.Message:
    """
    Envia no canal a mensagem configurada (do Builder/Anunciar) com o botão de registro.
    Retorna a mensagem enviada.
    """
    cfg = carregar_config()
    btn_cfg = cfg.get("botao_registro", {})
    btn_nome = btn_cfg.get("nome", "Registrar")
    btn_emoji_raw = btn_cfg.get("emoji", "📋")
    btn_cor = btn_cfg.get("cor", "gray")
    btn_style = BUTTON_STYLE_MAP.get(btn_cor, disnake.ButtonStyle.gray)

    # Tentar montar emoji
    btn_emoji = None
    if btn_emoji_raw:
        try:
            btn_emoji = disnake.PartialEmoji.from_str(btn_emoji_raw)
        except Exception:
            btn_emoji = btn_emoji_raw

    registro_btn = disnake.ui.Button(
        label=btn_nome,
        style=btn_style,
        emoji=btn_emoji,
        custom_id="Registro_IniciarAuto",
    )

    # Verificar se tem mensagem configurada
    mensagem_cfg = cfg.get("mensagem") or db.get_document("messages_anunciar") or {}

    if mensagem_cfg and mensagem_cfg.get("message"):
        built = Builder.build_from_cfg(mensagem_cfg)
        if built["mode"] == "v2":
            comps = built["components"] + [disnake.ui.ActionRow(registro_btn)]
            return await channel.send(
                components=comps,
                flags=built.get("flags", disnake.MessageFlags(is_components_v2=True)),
                allowed_mentions=disnake.AllowedMentions.none(),
            )
        else:
            kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
            if built.get("content"):
                kwargs["content"] = built["content"]
            if built.get("embed"):
                kwargs["embed"] = built["embed"]
            comps = (built.get("components") or []) + [disnake.ui.ActionRow(registro_btn)]
            kwargs["components"] = comps
            return await channel.send(**kwargs)

    # Sem mensagem configurada — enviar só o botão
    return await channel.send(
        components=[
            disnake.ui.Container(
                disnake.ui.TextDisplay("## 📋 Registro\nClique no botão abaixo para se registrar."),
                disnake.ui.ActionRow(registro_btn),
                **accent(),
            )
        ],
        flags=disnake.MessageFlags(is_components_v2=True),
        allowed_mentions=disnake.AllowedMentions.none(),
    )