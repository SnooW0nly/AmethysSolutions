import time
from typing import Optional, Callable, Iterable

import disnake

from functions.database import database as db
from functions.emoji import emoji


def obter_canal_id(chave: str) -> Optional[int]:
    dados = db.get_document("canais") or {}
    valor = dados.get(chave)
    if not valor:
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def criar_container_log(titulo: str, linhas: list[str]) -> disnake.ui.Container:
    linhas_filtradas = [l for l in linhas if l]
    corpo = "\n".join(linhas_filtradas) if linhas_filtradas else ""
    
    primary_color = db.get_document("custom_colors").get("primary", "#5c5ef0")

    return disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# {titulo}"),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(corpo),
        disnake.ui.Separator(),
        disnake.ui.TextDisplay(
            f"{emoji.calendar} **Data:** <t:{int(time.time())}:f> (<t:{int(time.time())}:R>)"
        ),
        accent_colour=disnake.Colour(int(primary_color.replace("#", ""), 16))
    )

def criar_embed_log(guild: disnake.Guild, titulo: str, linhas: list[str]) -> disnake.Embed:
    linhas_filtradas = [l for l in linhas if l]
    corpo = "\n".join(linhas_filtradas) if linhas_filtradas else "Nenhuma informação adicional."
    
    primary_color = db.get_document("custom_colors").get("primary", "#5c5ef0")
    
    embed = disnake.Embed(
        title=titulo,
        description=corpo,
        color=int(primary_color.replace("#", ""), 16),
        # timestamp=disnake.utils.utcnow()
    )
    # embed.set_footer(text=guild.name, icon_url=guild.icon.url if guild.icon else None)
    return embed


async def enviar_log_container(
    guild: disnake.Guild,
    canal_id: Optional[int],
    titulo: str,
    linhas: list[str],
    extra_components: Optional[list] = None,
) -> None:
    if not canal_id:
        return
    canal = guild.get_channel(canal_id)
    if not canal:
        return
    try:
        container = criar_container_log(titulo, linhas)
        components = [container]
        if extra_components:
            components.extend(extra_components)
        await canal.send(
            components=components,
            flags=disnake.MessageFlags(is_components_v2=True),
            allowed_mentions=disnake.AllowedMentions.none()
        )
    except Exception:
        return


async def enviar_log(
    guild: disnake.Guild,
    canal_id: Optional[int],
    titulo: str,
    linhas: list[str],
    extra_components: Optional[list] = None,
    file: Optional[disnake.File] = None
) -> Optional[disnake.Message]:
    if not canal_id:
        return
    canal = guild.get_channel(canal_id)
    if not canal:
        return

    mode = db.get_document("custom_mode").get("mode")

    try:
        if mode == "components":
            container = criar_container_log(titulo, linhas)
            components = [container]
            if extra_components:
                components.extend(extra_components)
            message = await canal.send(
                components=components,
                flags=disnake.MessageFlags(is_components_v2=True),
                allowed_mentions=disnake.AllowedMentions.none()
            )
        else: # mode == "embed"
            embed = criar_embed_log(guild, titulo, linhas)
            message = await canal.send(
                embed=embed,
                components=extra_components,
                allowed_mentions=disnake.AllowedMentions.none()
            )
        
        return message
            
    except Exception:
        return


async def buscar_executor_auditlog(
    guild: disnake.Guild,
    actions: Iterable[disnake.AuditLogAction],
    matcher: Callable[[disnake.AuditLogEntry], bool],
    max_age_seconds: int = 60,
    retries: int = 3,
    delay_seconds: float = 0.8,
) -> Optional[disnake.abc.User]:
    agora = time.time()
    try:
        for attempt in range(retries):
            for action in actions:
                async for entry in guild.audit_logs(action=action, limit=20):
                    created = getattr(entry, "created_at", None)
                    if created and (agora - created.timestamp()) > max_age_seconds:
                        break
                    try:
                        if matcher(entry):
                            return entry.user
                    except Exception:
                        continue
            # pequena espera para o audit log propagar
            await disnake.utils.sleep_until(disnake.utils.utcnow())  # no-op fallback
            try:
                import asyncio
                await asyncio.sleep(delay_seconds)
            except Exception:
                pass
    except Exception:
        return None
    return None

def verificar_guild(guild: int) -> bool:
    """
    Verifica se o servidor é o servidor do bot.
    @return: True se o servidor é o servidor do bot, False caso contrário.
    """
    config = db.obter("config.json")
    guild_id = config["bot"]["server"]
    if not guild_id:
        return False
    
    return str(guild) == str(guild_id)