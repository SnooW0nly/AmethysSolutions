"""
tasks/automations/tsk_random_gifs.py

Task periódica que pega avatares/banners de membros aleatórios do servidor
e envia nos canais configurados.

SFW:
  - gifs    → avatares animados  (GIF)
  - avatar  → avatares estáticos (PNG/WEBP)
  - banners → banners de usuário

NSFW:
  - gif     → avatares animados
  - icone   → avatares estáticos
  - banner  → banners de usuário

Cada sistema lê o modo (embed/container) do próprio config.
A mensagem é enviada com botões de link: PNG, WEBP e GIF (quando animado).
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Optional

import aiohttp
import disnake
from disnake.ext import commands

from modules.automations.random_gifs.helpers import (
    SISTEMAS,
    TIPOS_NSFW,
    NSFW_INTERVALO_SEGUNDOS,
    PINTEREST_TEMAS,
    ler_config,
    ler_config_nsfw,
    ler_tasks,
)

log = logging.getLogger(__name__)

_ultima_sfw:   dict[str, float] = {s: 0.0 for s in SISTEMAS}
_ultima_nsfw:  dict[str, float] = {t: 0.0 for t in TIPOS_NSFW}
_ultima_tasks: dict[str, float] = {}


# ══════════════════════════════════════════════════════════════════════════════
# Busca de assets dos membros
# ══════════════════════════════════════════════════════════════════════════════

def _membros(bot: commands.Bot) -> list[disnake.Member]:
    return [m for g in bot.guilds for m in g.members if not m.bot]


async def _asset_avatar_animado(bot: commands.Bot) -> Optional[disnake.Asset]:
    candidatos = [m for m in _membros(bot) if m.display_avatar.is_animated()]
    if not candidatos:
        return None
    return random.choice(candidatos).display_avatar


async def _asset_avatar_estatico(bot: commands.Bot) -> Optional[disnake.Asset]:
    candidatos = [m for m in _membros(bot) if not m.display_avatar.is_animated()]
    if not candidatos:
        todos = _membros(bot)
        if not todos:
            return None
        candidatos = todos
    return random.choice(candidatos).display_avatar


async def _asset_banner(bot: commands.Bot) -> Optional[disnake.Asset]:
    membros = _membros(bot)
    random.shuffle(membros)
    for membro in membros[:20]:
        try:
            user = await bot.fetch_user(membro.id)
            if user.banner:
                return user.banner
        except Exception:
            continue
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Montagem da mensagem
# ══════════════════════════════════════════════════════════════════════════════

def _botoes_formato(asset: disnake.Asset) -> list[disnake.ui.Button]:
    """Gera botões de link para cada formato disponível do asset."""
    botoes = [
        disnake.ui.Button(
            label="PNG",
            style=disnake.ButtonStyle.link,
            url=asset.replace(format="png", size=1024).url,
        ),
        disnake.ui.Button(
            label="WEBP",
            style=disnake.ButtonStyle.link,
            url=asset.replace(format="webp", size=1024).url,
        ),
    ]
    if asset.is_animated():
        botoes.append(disnake.ui.Button(
            label="GIF",
            style=disnake.ButtonStyle.link,
            url=asset.replace(format="gif", size=1024).url,
        ))
    return botoes


async def _enviar(
    canal: disnake.TextChannel,
    asset: disnake.Asset,
    modo: str,
) -> Optional[disnake.Message]:
    try:
        botoes = _botoes_formato(asset)
        url_preview = asset.replace(format="gif" if asset.is_animated() else "png", size=1024).url

        # Info do servidor para footer
        guild       = canal.guild
        server_name = guild.name if guild else "Servidor"
        server_icon = guild.icon.replace(format="png", size=64).url if (guild and guild.icon) else None

        if modo == "container":
            # Components v2: imagem + rodapé com ícone+nome do servidor + botões
            footer_parts = [
                disnake.ui.MediaGallery(
                    disnake.ui.MediaGalleryItem(media=url_preview),
                ),
                disnake.ui.ActionRow(*botoes),
            ]
            if server_icon:
                footer_parts.append(
                    disnake.ui.TextDisplay(f"-# {server_name}"),
                )
            else:
                footer_parts.append(
                    disnake.ui.TextDisplay(f"-# {server_name}"),
                )
            container = disnake.ui.Container(*footer_parts)
            return await canal.send(
                components=[container],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
        else:
            embed = disnake.Embed(color=disnake.Color.blurple())
            embed.set_image(url=url_preview)
            if server_icon:
                embed.set_footer(text=server_name, icon_url=server_icon)
            else:
                embed.set_footer(text=server_name)
            return await canal.send(
                embed=embed,
                components=[disnake.ui.ActionRow(*botoes)],
            )

    except disnake.Forbidden:
        log.warning("[RandomGifs] Sem permissão em #%s.", canal.id)
    except disnake.HTTPException as e:
        log.warning("[RandomGifs] HTTPException em #%s: %s", canal.id, e)
    except Exception:
        log.exception("[RandomGifs] Erro ao enviar em #%s.", canal.id)
    return None


async def _resolver_canal(bot: commands.Bot, canal_id: str) -> Optional[disnake.TextChannel]:
    try:
        canal = bot.get_channel(int(canal_id))
        if canal is None:
            canal = await bot.fetch_channel(int(canal_id))
        if isinstance(canal, disnake.TextChannel):
            return canal
    except Exception:
        pass
    return None


# ══════════════════════════════════════════════════════════════════════════════
# Mapeamentos
# ══════════════════════════════════════════════════════════════════════════════

_ASSET_SFW = {
    "gifs":    _asset_avatar_animado,
    "avatar":  _asset_avatar_estatico,
    "banners": _asset_banner,
}

_ASSET_NSFW = {
    "gif":    _asset_avatar_animado,
    "icone":  _asset_avatar_estatico,
    "banner": _asset_banner,
}


_PINTEREST_SEARCH = "https://www.pinterest.com/search/pins/?q={query}&rs=typed"

async def _asset_pinterest(session: aiohttp.ClientSession, tema: str) -> Optional[str]:
    """Busca uma imagem aleatória do Pinterest pelo tema. Retorna URL ou None."""
    query = PINTEREST_TEMAS.get(tema, tema)
    url   = f"https://www.pinterest.com/resource/BaseSearchResource/get/?source_url=/search/pins/&data=%7B%22options%22%3A%7B%22query%22%3A%22{query.replace(' ', '+')}%22%2C%22scope%22%3A%22pins%22%7D%7D"
    headers = {
        "User-Agent":  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Referer":     "https://www.pinterest.com/",
    }
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json(content_type=None)
        pins = (
            data.get("resource_response", {})
                .get("data", {})
                .get("results", [])
        )
        # filtra pins com imagem
        imgs = []
        for p in pins:
            img = (p.get("images") or {}).get("orig") or (p.get("images") or {}).get("736x")
            if img and img.get("url"):
                imgs.append(img["url"])
        if not imgs:
            return None
        return random.choice(imgs)
    except Exception:
        log.debug("[RandomGifs] Pinterest fetch falhou para '%s'.", tema)
        return None


# ══════════════════════════════════════════════════════════════════════════════
# Cog
# ══════════════════════════════════════════════════════════════════════════════

class RandomGifsTask(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def cog_load(self):
        self._iniciar()

    def cog_unload(self):
        self._parar()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._running:
            self._iniciar()

    def _iniciar(self):
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._loop(), name="random_gifs_loop")
        log.info("[RandomGifs] Task iniciada.")

    def _parar(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
        log.info("[RandomGifs] Task encerrada.")

    async def _loop(self):
        await self.bot.wait_until_ready()
        async with aiohttp.ClientSession() as session:
            while self._running:
                try:
                    agora = time.monotonic()
                    await self._ciclo_sfw(agora)
                    await self._ciclo_nsfw(agora)
                    await self._ciclo_tasks(session, agora)
                except asyncio.CancelledError:
                    return
                except Exception:
                    log.exception("[RandomGifs] Erro no loop.")
                await asyncio.sleep(10)

    async def _ciclo_sfw(self, agora: float):
        cfg = ler_config()
        for tipo in SISTEMAS:
            s = cfg["sistemas"][tipo]
            if not s.get("ligado"):
                continue
            canais = s.get("canais") or []
            if not canais:
                continue
            intervalo = max(1, int(s.get("tempo_segundos", 60)))
            if agora - _ultima_sfw[tipo] < intervalo:
                continue

            fn = _ASSET_SFW.get(tipo)
            if not fn:
                continue
            asset = await fn(self.bot)
            if not asset:
                log.debug("[RandomGifs SFW] Nenhum asset para '%s'.", tipo)
                continue

            modo = s.get("modo", "embed")
            for canal_id in canais:
                canal = await _resolver_canal(self.bot, canal_id)
                if canal:
                    await _enviar(canal, asset, modo)
                    await asyncio.sleep(0.5)

            _ultima_sfw[tipo] = agora

    async def _ciclo_nsfw(self, agora: float):
        cfg = ler_config_nsfw()
        for tipo in TIPOS_NSFW:
            s = cfg["sistemas"][tipo]
            if not s.get("ligado"):
                continue
            canais = s.get("canais") or []
            if not canais:
                continue
            if agora - _ultima_nsfw[tipo] < NSFW_INTERVALO_SEGUNDOS:
                continue

            fn = _ASSET_NSFW.get(tipo)
            if not fn:
                continue
            asset = await fn(self.bot)
            if not asset:
                log.debug("[RandomGifs NSFW] Nenhum asset para '%s'.", tipo)
                continue

            modo = s.get("modo", "embed")
            for canal_id in canais:
                canal = await _resolver_canal(self.bot, canal_id)
                if canal:
                    await _enviar(canal, asset, modo)
                    await asyncio.sleep(0.5)

            _ultima_nsfw[tipo] = agora


    async def _ciclo_tasks(self, session: aiohttp.ClientSession, agora: float):
        tasks = ler_tasks()
        for tid, task in tasks.items():
            if not task.get("ligado"):
                continue
            canais = task.get("canais") or []
            if not canais:
                continue
            intervalo = max(1, int(task.get("tempo_segundos", 60)))
            ultima    = _ultima_tasks.get(tid, 0.0)
            if agora - ultima < intervalo:
                continue

            tema = task.get("pinterest_tema")
            modo = task.get("modo", "embed")

            if tema:
                # Busca no Pinterest
                url_img = await _asset_pinterest(session, tema)
                if not url_img:
                    log.debug("[RandomGifs Tasks] Pinterest sem resultado para '%s'.", tema)
                    continue
                for canal_id in canais:
                    canal = await _resolver_canal(self.bot, canal_id)
                    if not canal:
                        continue
                    try:
                        botoes = [
                            disnake.ui.Button(label="Ver no Pinterest", style=disnake.ButtonStyle.link, url=url_img),
                        ]
                        guild       = canal.guild
                        server_name = guild.name if guild else "Servidor"
                        server_icon = guild.icon.replace(format="png", size=64).url if (guild and guild.icon) else None
                        if modo == "container":
                            footer = disnake.ui.TextDisplay(f"-# {server_name} · {tema}")
                            container = disnake.ui.Container(
                                disnake.ui.MediaGallery(disnake.ui.MediaGalleryItem(media=url_img)),
                                disnake.ui.ActionRow(*botoes),
                                footer,
                            )
                            await canal.send(components=[container], flags=disnake.MessageFlags(is_components_v2=True))
                        else:
                            embed = disnake.Embed(color=disnake.Color.blurple())
                            embed.set_image(url=url_img)
                            if server_icon:
                                embed.set_footer(text=f"{server_name} · {tema}", icon_url=server_icon)
                            else:
                                embed.set_footer(text=f"{server_name} · {tema}")
                            await canal.send(embed=embed, components=[disnake.ui.ActionRow(*botoes)])
                        await asyncio.sleep(0.5)
                    except Exception:
                        log.exception("[RandomGifs Tasks] Erro ao enviar Pinterest em #%s.", canal_id)
            else:
                # Usa membros do servidor — comportamento padrão (avatar animado como fallback)
                asset = await _asset_avatar_animado(self.bot) or await _asset_avatar_estatico(self.bot)
                if not asset:
                    continue
                for canal_id in canais:
                    canal = await _resolver_canal(self.bot, canal_id)
                    if canal:
                        await _enviar(canal, asset, modo)
                        await asyncio.sleep(0.5)

            _ultima_tasks[tid] = agora


def setup(bot: commands.Bot):
    bot.add_cog(RandomGifsTask(bot))