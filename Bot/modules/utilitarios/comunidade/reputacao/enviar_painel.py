"""
modules/utilitarios/comunidade/reputacao/enviar_painel.py

Envia o painel de busca de reputação e o painel de ranking em canais.
Usa o Builder igual ao Registro/Verificação para personalização de mensagem.
"""
from __future__ import annotations

from datetime import datetime, timezone

import disnake
from commands.admin.anunciar.builder import Builder
from functions.database import database as db

from .helpers import (
    accent, color, gerar_ranking, nota_cor, barra_nota, estrelas_nota,
    carregar_config,
)


async def enviar_painel_pesquisa(
    channel: disnake.TextChannel,
    guild: disnake.Guild,
    cfg: dict,
) -> disnake.Message:
    """
    Envia o painel de busca de membro no canal.
    Usa mensagem personalizada (Builder) se configurada, caso contrário usa padrão.
    """
    mensagem_cfg = cfg.get("mensagem_pesquisa") or {}

    buscar_btn = disnake.ui.Button(
        label="🔍 Buscar Membro",
        style=disnake.ButtonStyle.blurple,
        custom_id="Reputacao_NovaBusca",
    )

    if mensagem_cfg and mensagem_cfg.get("message"):
        built = Builder.build_from_cfg(mensagem_cfg)
        if built["mode"] == "v2":
            comps = built["components"] + [disnake.ui.ActionRow(buscar_btn)]
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
            comps = (built.get("components") or []) + [disnake.ui.ActionRow(buscar_btn)]
            kwargs["components"] = comps
            return await channel.send(**kwargs)

    # Padrão
    return await channel.send(
        components=[
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# 🔍 Busca de Reputação\n"
                    f"Pesquise um membro pelo nome ou ID para ver e avaliar o perfil de reputação dele.\n\n"
                    f"-# As avaliações são de **1 a 10** e cada usuário pode avaliar uma vez por membro."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(buscar_btn),
                **accent(),
            ),
        ],
        flags=disnake.MessageFlags(is_components_v2=True),
        allowed_mentions=disnake.AllowedMentions.none(),
    )


async def enviar_painel_ranking(
    channel: disnake.TextChannel,
    guild: disnake.Guild,
    cfg: dict,
    limit: int = 15,
) -> disnake.Message:
    """
    Envia o ranking de reputação no canal.
    Usa mensagem personalizada (Builder) como header se configurada.
    """
    ranking = gerar_ranking(limit=limit)
    agora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M") + " UTC"

    if not ranking:
        corpo = "`Ainda não há avaliações registradas neste servidor.`"
    else:
        linhas = []
        medalhas = ["🥇", "🥈", "🥉"]
        for i, item in enumerate(ranking):
            member = guild.get_member(int(item["user_id"]))
            nome = member.display_name if member else f"Usuário {item['user_id']}"
            mention = member.mention if member else f"<@{item['user_id']}>"
            medalha = medalhas[i] if i < 3 else f"`#{i+1}`"
            cor = nota_cor(item["media"])
            barra = barra_nota(item["media"])
            linhas.append(
                f"{medalha} {mention} — {cor} **`{item['media']}/10`** · `{item['count']}` avaliações\n"
                f"   `{barra}`"
            )
        corpo = "\n".join(linhas)

    mensagem_cfg = cfg.get("mensagem_ranking") or {}

    ranking_container = disnake.ui.Container(
        disnake.ui.TextDisplay(
            f"# 🏆 Ranking de Reputação\n"
            f"-# Atualizado em {agora}\n\n"
            f"{corpo}"
        ),
        **accent(),
    )

    if mensagem_cfg and mensagem_cfg.get("message"):
        built = Builder.build_from_cfg(mensagem_cfg)
        if built["mode"] == "v2":
            comps = built["components"] + [ranking_container]
            return await channel.send(
                components=comps,
                flags=built.get("flags", disnake.MessageFlags(is_components_v2=True)),
                allowed_mentions=disnake.AllowedMentions.none(),
            )

    # Padrão
    return await channel.send(
        components=[ranking_container],
        flags=disnake.MessageFlags(is_components_v2=True),
        allowed_mentions=disnake.AllowedMentions.none(),
    )
