"""
modules/utilitarios/comunidade/conversor/enviar_painel.py

Envia o painel público do Conversor de Mídia no canal configurado.
"""
from __future__ import annotations

import disnake

from .helpers import accent, conversoes_disponiveis, CONVERSOES


async def enviar_painel_conversor(
    channel: disnake.TextChannel,
    guild: disnake.Guild,
    cfg: dict,
) -> disnake.Message:
    """
    Envia o painel público com botão de iniciar conversão.
    """
    disponiveis = conversoes_disponiveis(cfg)

    # Monta lista visual dos tipos disponíveis
    tipos_txt = "\n".join(
        f"{v['emoji']} **{v['label']}** — {v['desc']}"
        for v in disponiveis.values()
    ) or "`Nenhuma conversão disponível no momento.`"

    return await channel.send(
        components=[
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# Conversor de Mídia\n"
                    f"Converta seus arquivos de forma rápida e privada.\n"
                    f"Um tópico exclusivo será criado só para você!\n\n"
                    f"**Conversões disponíveis:**\n{tipos_txt}"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Converter agora",
                        style=disnake.ButtonStyle.green,
                        custom_id="Conversor_Iniciar",
                    )
                ),
                **accent(),
            )
        ],
        flags=disnake.MessageFlags(is_components_v2=True),
        allowed_mentions=disnake.AllowedMentions.none(),
    )