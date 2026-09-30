from typing import Optional

import disnake
import time
import traceback
from functions.emoji import emoji
from functions.database import database as db  

def _criar_container_log(titulo: str, linhas: list[str], **kwargs) -> disnake.ui.Container:
    """Cria um container de log formatado."""
    linhas_filtradas = [l for l in linhas if l]
    corpo = "\n".join(linhas_filtradas) if linhas_filtradas else ""
    return disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# {titulo}"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(corpo),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(
            f"{emoji.calendar} **Data:** <t:{int(time.time())}:f> (<t:{int(time.time())}:R>)"
        ),
        **kwargs,
    )

async def enviar_log(guild: disnake.Guild, canal_id: Optional[int], titulo: str, linhas: list[str]) -> None:
    """Envia uma mensagem de log para o canal configurado, respeitando o modo (embed/components)."""
    if not canal_id:
        return
    
    canal = guild.get_channel(canal_id)
    if not canal:
        return

    mode = db.get_document("custom_mode").get("mode")
    colors = db.get_document("custom_colors")
    primary_color_hex = colors.get("primary")
    
    corpo = "\n".join(l for l in linhas if l)

    try:
        if mode == "embed":
            embed = disnake.Embed(
                title=f"{titulo}",
                description=corpo,
                timestamp=disnake.utils.utcnow()
            )
            if primary_color_hex:
                embed.color = int(primary_color_hex.replace("#", ""), 16)
            await canal.send(embed=embed, allowed_mentions=disnake.AllowedMentions.none())
        else: # components
            container_kwargs = {}
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
                container_kwargs["accent_colour"] = disnake.Colour(primary_color)
            
            container = _criar_container_log(titulo, linhas, **container_kwargs)
            await canal.send(components=[container], allowed_mentions=disnake.AllowedMentions.none())
    except Exception:
        print(f"Falha ao enviar log de proteção para o servidor {guild.id}")
        traceback.print_exc()
