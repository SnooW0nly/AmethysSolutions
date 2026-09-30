import asyncio
import logging
import struct

import aiohttp
import disnake
from disnake.ext import commands
from typing import Optional

from functions.emoji import emoji
from functions.database import database as db

from .helpers import (
    # Compartilhado
    MAX_CANAIS,
    formatar_canais,
    formatar_canais_curto,
    # SFW
    SISTEMAS,
    ler_config,
    adicionar_canal,
    remover_canal,
    toggle_sistema,
    set_tempo,
    label_sistema,
    resumo_sistemas,
    # NSFW
    TIPOS_NSFW,
    NSFW_INTERVALO_SEGUNDOS,
    ler_config_nsfw,
    adicionar_canal_nsfw,
    remover_canal_nsfw,
    toggle_nsfw,
    set_ligado_nsfw,
    label_nsfw,
    resumo_nsfw,
    # Tasks
    PINTEREST_TEMAS,
    ler_tasks,
    criar_task,
    deletar_task,
    atualizar_task,
    toggle_task,
    adicionar_canal_task,
    remover_canal_task,
    set_tema_pinterest,
    set_tempo_task,
    set_modo_task,
    resumo_task,
)

log = logging.getLogger(__name__)

_NIGHT_API_BASE = "https://api.night-api.com/images/nsfw"
_NIGHT_API_KEY  = "t7nji2cKKD-5lcXosS5tADxdhGlZX97-Udm9bKQKQr"


# ══════════════════════════════════════════════════════════════════════════════
# Helpers de cor e modo (compartilhados)
# ══════════════════════════════════════════════════════════════════════════════

def _container_kwargs() -> dict:
    try:
        colors  = db.get_document("custom_colors") or {}
        hex_val = (colors.get("primary") or "").replace("#", "").strip()
        if hex_val:
            return {"accent_colour": disnake.Colour(int(hex_val, 16))}
    except Exception:
        pass
    return {}


def _embed_color() -> Optional[int]:
    try:
        colors  = db.get_document("custom_colors") or {}
        hex_val = (colors.get("primary") or "").replace("#", "").strip()
        if hex_val:
            return int(hex_val, 16)
    except Exception:
        pass
    return None


def _is_embed_mode() -> bool:
    return (db.get_document("custom_mode") or {}).get("mode") == "embed"


# ══════════════════════════════════════════════════════════════════════════════
# Detecção de dimensões de imagem (sem dependências externas)
# ══════════════════════════════════════════════════════════════════════════════

def _detectar_imagem(data: bytes) -> tuple[str, int, int]:
    """
    Retorna (formato, largura, altura).
    formato: 'gif' | 'png' | 'jpeg' | 'webp' | 'unknown'
    """
    try:
        # GIF
        if data[:6] in (b"GIF87a", b"GIF89a"):
            w, h = struct.unpack("<HH", data[6:10])
            return "gif", w, h

        # PNG
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w, h = struct.unpack(">II", data[16:24])
            return "png", w, h

        # JPEG
        if data[:2] == b"\xff\xd8":
            i = 2
            while i + 4 < len(data):
                if data[i] != 0xFF:
                    break
                marker = data[i + 1]
                if marker in (0xC0, 0xC1, 0xC2):
                    h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                    return "jpeg", w, h
                length = struct.unpack(">H", data[i + 2 : i + 4])[0]
                i += 2 + length

        # WebP
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            chunk = data[12:16]
            if chunk == b"VP8 " and len(data) >= 30:
                w = struct.unpack("<H", data[26:28])[0] & 0x3FFF
                h = struct.unpack("<H", data[28:30])[0] & 0x3FFF
                return "webp", w, h
            if chunk == b"VP8L" and len(data) >= 25:
                bits = struct.unpack("<I", data[21:25])[0]
                w = (bits & 0x3FFF) + 1
                h = ((bits >> 14) & 0x3FFF) + 1
                return "webp", w, h

    except Exception:
        pass
    return "unknown", 0, 0


def _rotear_tipo(fmt: str, w: int, h: int) -> str:
    """
    Decide para qual tipo NSFW a imagem vai:
      gif    → formato GIF (animado) ou dimensões desconhecidas (fallback)
      icone  → aproximadamente quadrada  (0.75 ≤ w/h ≤ 1.33)
      banner → paisagem larga            (w/h > 1.5)
    """
    if fmt == "gif":
        return "gif"
    if w > 0 and h > 0:
        ratio = w / h
        if ratio > 1.5:
            return "banner"
        if 0.75 <= ratio <= 1.33:
            return "icone"
    return "gif"  # fallback


# ══════════════════════════════════════════════════════════════════════════════
# RandomGifsCog — painel SFW + acesso ao NSFW
# ══════════════════════════════════════════════════════════════════════════════

class RandomGifsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Painel principal ──────────────────────────────────────────────────────

    @staticmethod
    def Painel() -> list:
        tasks = ler_tasks()
        ckw   = _container_kwargs()

        algum_ativo = any(t["ligado"] for t in tasks.values()) if tasks else False
        tog_label   = "Ligado"  if algum_ativo else "Desligado"
        tog_style   = disnake.ButtonStyle.success if algum_ativo else disnake.ButtonStyle.grey
        desativado  = not algum_ativo and bool(tasks)  # desabilita interações se toggle off

        children: list = [
            disnake.ui.TextDisplay(
                f"# {emoji.sparkles}  Random Gifs\n"
                "-# Painel > **Random Gifs**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label=tog_label,    style=tog_style,               custom_id="RG:toggle_global", emoji=emoji.power),
                disnake.ui.Button(label="Criar Task", style=disnake.ButtonStyle.grey, custom_id="RG:criar_task",    emoji=emoji.plus, disabled=desativado),
            ),
        ]

        if tasks:
            children.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Gerenciar task existente…",
                        custom_id="RG:select_task",
                        disabled=desativado,
                        options=[
                            disnake.SelectOption(
                                label=t["nome"][:50],
                                value=tid,
                                emoji=emoji.on if t["ligado"] else emoji.off,
                                description=(
                                    f"{'Pinterest: ' + t['pinterest_tema'] if t.get('pinterest_tema') else 'Membros'}"
                                    f" · {len(t['canais'])} canal(is)"
                                )[:100],
                            )
                            for tid, t in tasks.items()
                        ],
                    )
                )
            )

        return [
            disnake.ui.Container(*children, **ckw),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            ),
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        tasks = ler_tasks()

        algum_ativo = any(t["ligado"] for t in tasks.values()) if tasks else False
        tog_label   = "Ligado"  if algum_ativo else "Desligado"
        tog_style   = disnake.ButtonStyle.success if algum_ativo else disnake.ButtonStyle.grey
        desativado  = not algum_ativo and bool(tasks)

        n_ativas = sum(1 for t in tasks.values() if t["ligado"])
        embed = disnake.Embed(
            title="Random Gifs",
            description=(
                f"{emoji.on if algum_ativo else emoji.off} `{n_ativas}/{len(tasks)} task{'s' if len(tasks) != 1 else ''} ativa{'s' if n_ativas != 1 else ''}`"
                if tasks else "Nenhuma task criada ainda."
            ),
        )
        cor = _embed_color()
        if cor:
            embed.color = cor

        components: list = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label=tog_label,    style=tog_style,               custom_id="RG:toggle_global", emoji=emoji.power),
                disnake.ui.Button(label="Criar Task", style=disnake.ButtonStyle.grey, custom_id="RG:criar_task",    emoji=emoji.plus, disabled=desativado),
            ),
        ]
        if tasks:
            components.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Gerenciar task existente…",
                        custom_id="RG:select_task",
                        disabled=desativado,
                        options=[
                            disnake.SelectOption(
                                label=t["nome"][:50],
                                value=tid,
                                emoji=emoji.on if t["ligado"] else emoji.off,
                                description=(
                                    f"{'Pinterest: ' + t['pinterest_tema'] if t.get('pinterest_tema') else 'Membros'}"
                                    f" · {len(t['canais'])} canal(is)"
                                )[:100],
                            )
                            for tid, t in tasks.items()
                        ],
                    )
                )
            )
        components.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        )
        return embed, components

    # ── Painel de sistema SFW (gifs / avatar / banners) ───────────────────────

    @staticmethod
    def _painel_sistema(tipo: str) -> list:
        cfg     = ler_config()
        sistema = cfg["sistemas"][tipo]
        ligado  = sistema["ligado"]
        canais  = sistema["canais"]
        nome    = label_sistema(tipo)
        ckw     = _container_kwargs()

        toggle_label = "Ligado"    if ligado else "Desligado"
        toggle_style = disnake.ButtonStyle.success if ligado else disnake.ButtonStyle.grey

        children: list = [
            disnake.ui.TextDisplay(
                f"# {nome}\n"
                f"-# Painel > Random Gifs > **{nome}**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**Status:** `{toggle_label}`\n"
                f"**Intervalo:** `{sistema['tempo_segundos']}s`\n"
                f"**Canais ({len(canais)}/{MAX_CANAIS}):**\n"
                + (formatar_canais(canais) if canais else "`Nenhum canal configurado`")
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar Canal", style=disnake.ButtonStyle.grey,  custom_id=f"RG:add_canal:{tipo}",  emoji=emoji.plus),
                disnake.ui.Button(label="Intervalo",       style=disnake.ButtonStyle.grey,  custom_id=f"RG:tempo:{tipo}",      emoji=emoji.time),
                disnake.ui.Button(label=toggle_label,      style=toggle_style,              custom_id=f"RG:toggle:{tipo}",    emoji=emoji.power),
            ),
        ]

        # Select de remoção — só aparece se houver canais
        if canais:
            children.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Remover canal",
                        custom_id=f"RG:rm_canal:{tipo}",
                        options=[
                            disnake.SelectOption(label=f"#{cid}", value=cid, description=f"ID: {cid}")
                            for cid in canais
                        ],
                    )
                )
            )

        return [
            disnake.ui.Container(*children, **ckw),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RG:back:home"),
            ),
        ]

    @staticmethod
    def _painel_sistema_embed(tipo: str) -> tuple[disnake.Embed, list]:
        cfg     = ler_config()
        sistema = cfg["sistemas"][tipo]
        ligado  = sistema["ligado"]
        canais  = sistema["canais"]
        nome    = label_sistema(tipo)

        toggle_label = "Ligado"    if ligado else "Desligado"
        toggle_style = disnake.ButtonStyle.success if ligado else disnake.ButtonStyle.grey

        embed = disnake.Embed(
            title=nome,
            description=(
                f"**Status:** `{toggle_label}`\n"
                f"**Intervalo:** `{sistema['tempo_segundos']}s`\n"
                f"**Canais ({len(canais)}/{MAX_CANAIS}):**\n"
                + (formatar_canais(canais) if canais else "`Nenhum canal configurado`")
            ),
        )
        cor = _embed_color()
        if cor:
            embed.color = cor

        components: list = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar Canal", style=disnake.ButtonStyle.grey, custom_id=f"RG:add_canal:{tipo}", emoji=emoji.plus),
                disnake.ui.Button(label="Intervalo",       style=disnake.ButtonStyle.grey, custom_id=f"RG:tempo:{tipo}",     emoji=emoji.time),
                disnake.ui.Button(label=toggle_label,      style=toggle_style,             custom_id=f"RG:toggle:{tipo}",  emoji=emoji.power),
            ),
        ]
        if canais:
            components.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Remover canal",
                        custom_id=f"RG:rm_canal:{tipo}",
                        options=[
                            disnake.SelectOption(label=f"#{cid}", value=cid, description=f"ID: {cid}")
                            for cid in canais
                        ],
                    )
                )
            )
        components.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RG:back:home"),
            )
        )
        return embed, components

    # ── Painel de Task ────────────────────────────────────────────────────────

    @staticmethod
    def _painel_task(task_id: str) -> list:
        tasks = ler_tasks()
        task  = tasks.get(task_id)
        if not task:
            return RandomGifsCog.Painel()
        ckw    = _container_kwargs()
        ligado = task["ligado"]
        canais = task["canais"]
        tema   = task.get("pinterest_tema")

        tog_label = "Ligado"    if ligado else "Desligado"
        tog_style = disnake.ButtonStyle.success if ligado else disnake.ButtonStyle.grey

        fonte_str = f"Pinterest · `{tema}`" if tema else "Membros do servidor"
        nsfw_str  = "`🔞 NSFW`" if task.get("nsfw") else "`✅ SFW`"

        children: list = [
            disnake.ui.TextDisplay(
                f"# 📋 {task['nome']}\n"
                f"-# Painel > Random Gifs > **Task**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**Status:** `{tog_label}`\n"
                f"**Tipo:** {nsfw_str}\n"
                f"**Intervalo:** `{task['tempo_segundos']}s`\n"
                f"**Fonte:** {fonte_str}\n"
                f"**Modo:** `{task['modo']}`\n"
                f"**Canais ({len(canais)}/{MAX_CANAIS}):**\n"
                + (formatar_canais(canais) if canais else "`Nenhum canal configurado`")
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Add Canal",  style=disnake.ButtonStyle.grey,  custom_id=f"RGT:add_canal:{task_id}",  emoji=emoji.plus),
                disnake.ui.Button(label="Intervalo",  style=disnake.ButtonStyle.grey,  custom_id=f"RGT:tempo:{task_id}",      emoji=emoji.time),
                disnake.ui.Button(label=tog_label,    style=tog_style,                 custom_id=f"RGT:toggle:{task_id}",     emoji=emoji.power),
            ),
        ]

        if canais:
            children.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Remover canal…",
                        custom_id=f"RGT:rm_canal:{task_id}",
                        options=[
                            disnake.SelectOption(label=f"#{cid}", value=cid, description=f"ID: {cid}")
                            for cid in canais
                        ],
                    )
                )
            )

        # Select de tema Pinterest
        children.append(
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Escolher tema Pinterest…",
                    custom_id=f"RGT:select_tema:{task_id}",
                    options=[
                        disnake.SelectOption(
                            label="Membros do servidor",
                            value="__membros__",
                            description="Usa avatares/banners dos membros",
                            default=(tema is None),
                        ),
                        *[
                            disnake.SelectOption(label=nome, value=nome, description=query, default=(tema == nome))
                            for nome, query in PINTEREST_TEMAS.items()
                        ],
                    ],
                )
            )
        )

        return [
            disnake.ui.Container(*children, **ckw),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar",  style=disnake.ButtonStyle.grey,   emoji=emoji.back, custom_id="RG:back:home"),
                disnake.ui.Button(label="Deletar", style=disnake.ButtonStyle.danger,  custom_id=f"RGT:deletar:{task_id}", emoji="🗑️"),
            ),
        ]

    @staticmethod
    def _painel_task_embed(task_id: str) -> tuple[disnake.Embed, list]:
        tasks = ler_tasks()
        task  = tasks.get(task_id)
        if not task:
            return RandomGifsCog.PainelEmbed()
        ligado = task["ligado"]
        canais = task["canais"]
        tema   = task.get("pinterest_tema")

        tog_label = "Ligado"    if ligado else "Desligado"
        tog_style = disnake.ButtonStyle.success if ligado else disnake.ButtonStyle.grey
        fonte_str = f"Pinterest · `{tema}`" if tema else "Membros do servidor"
        nsfw_str  = "`🔞 NSFW`" if task.get("nsfw") else "`✅ SFW`"

        embed = disnake.Embed(
            title=f"📋 {task['nome']}",
            description=(
                f"**Status:** `{tog_label}`\n"
                f"**Tipo:** {nsfw_str}\n"
                f"**Intervalo:** `{task['tempo_segundos']}s`\n"
                f"**Fonte:** {fonte_str}\n"
                f"**Modo:** `{task['modo']}`\n"
                f"**Canais ({len(canais)}/{MAX_CANAIS}):**\n"
                + (formatar_canais(canais) if canais else "`Nenhum canal configurado`")
            ),
        )
        cor = _embed_color()
        if cor:
            embed.color = cor

        components: list = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Add Canal",  style=disnake.ButtonStyle.grey,  custom_id=f"RGT:add_canal:{task_id}",  emoji=emoji.plus),
                disnake.ui.Button(label="Intervalo",  style=disnake.ButtonStyle.grey,  custom_id=f"RGT:tempo:{task_id}",      emoji=emoji.time),
                disnake.ui.Button(label=tog_label,    style=tog_style,                 custom_id=f"RGT:toggle:{task_id}",     emoji=emoji.power),
            ),
        ]
        if canais:
            components.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Remover canal…",
                        custom_id=f"RGT:rm_canal:{task_id}",
                        options=[
                            disnake.SelectOption(label=f"#{cid}", value=cid, description=f"ID: {cid}")
                            for cid in canais
                        ],
                    )
                )
            )
        components.append(
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Escolher tema Pinterest…",
                    custom_id=f"RGT:select_tema:{task_id}",
                    options=[
                        disnake.SelectOption(
                            label="Membros do servidor",
                            value="__membros__",
                            description="Usa avatares/banners dos membros",
                            default=(tema is None),
                        ),
                        *[
                            disnake.SelectOption(label=nome, value=nome, description=query, default=(tema == nome))
                            for nome, query in PINTEREST_TEMAS.items()
                        ],
                    ],
                )
            )
        )
        components.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar",  style=disnake.ButtonStyle.grey,  emoji=emoji.back, custom_id="RG:back:home"),
                disnake.ui.Button(label="Deletar", style=disnake.ButtonStyle.danger, custom_id=f"RGT:deletar:{task_id}", emoji="🗑️"),
            )
        )
        return embed, components

    # ── Navegação ─────────────────────────────────────────────────────────────

    async def _editar(self, inter, **kwargs):
        """Edita a mensagem original independente do tipo de interaction."""
        if isinstance(inter, disnake.ModalInteraction):
            await inter.edit_original_response(**kwargs)
        else:
            await inter.edit_original_message(**kwargs)

    async def _ir_home(self, inter):
        if _is_embed_mode():
            e, c = RandomGifsCog.PainelEmbed()
            await self._editar(inter, content=None, embed=e, components=c)
        else:
            await self._editar(inter, content=None, components=RandomGifsCog.Painel())

    async def _ir_sistema(self, inter, tipo: str):
        if _is_embed_mode():
            e, c = RandomGifsCog._painel_sistema_embed(tipo)
            await self._editar(inter, content=None, embed=e, components=c)
        else:
            await self._editar(inter, content=None, components=RandomGifsCog._painel_sistema(tipo))

    async def _ir_task(self, inter, task_id: str):
        if _is_embed_mode():
            e, c = RandomGifsCog._painel_task_embed(task_id)
            await self._editar(inter, content=None, embed=e, components=c)
        else:
            await self._editar(inter, content=None, components=RandomGifsCog._painel_task(task_id))

    # ── Botões SFW ────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def rg_buttons(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RG:"):
            return

        if cid == "RG:back:home":
            await inter.response.defer()
            await self._ir_home(inter)
            return

        if cid == "RG:toggle_global":
            await inter.response.defer()
            tasks = ler_tasks()
            algum = any(t["ligado"] for t in tasks.values())
            for tid in tasks:
                atualizar_task(tid, lambda t: {**t, "ligado": not algum})
            await self._ir_home(inter)
            return

        if cid == "RG:criar_task":
            await inter.response.send_modal(
                title="Nova Task",
                custom_id="RG:modal_criar_task",
                components=[
                    disnake.ui.TextInput(
                        label="Nome da Task",
                        placeholder="Ex: Girl Icons, Wallpapers, etc.",
                        custom_id="nome_task",
                        style=disnake.TextInputStyle.short,
                        min_length=1,
                        max_length=50,
                        required=True,
                    ),
                    disnake.ui.Label(
                        text="Tipo de conteúdo",
                        component=disnake.ui.StringSelect(
                            custom_id="task_nsfw",
                            placeholder="A task será NSFW?",
                            options=[
                                disnake.SelectOption(label="SFW",  value="sfw",  description="Conteúdo seguro para todos os canais", emoji="✅"),
                                disnake.SelectOption(label="NSFW", value="nsfw", description="Apenas para canais marcados como NSFW",  emoji="🔞"),
                            ],
                        ),
                        description="Escolha se a task enviará conteúdo NSFW.",
                    ),
                ],
            )
            return

        if cid.startswith("RG:nav:"):
            tipo = cid.split(":", 2)[2]
            if tipo in SISTEMAS:
                await inter.response.defer()
                await self._ir_sistema(inter, tipo)
            return

        if cid.startswith("RG:toggle:"):
            tipo = cid.split(":", 2)[2]
            if tipo not in SISTEMAS:
                return
            await inter.response.defer()
            toggle_sistema(tipo)
            await self._ir_sistema(inter, tipo)
            return

        if cid.startswith("RG:add_canal:"):
            tipo = cid.split(":", 2)[2]
            if tipo not in SISTEMAS:
                return
            await inter.response.defer()
            if _is_embed_mode():
                embed = disnake.Embed(title=f"Adicionar Canal — {label_sistema(tipo)}", description="Selecione o canal de texto abaixo.")
                cor = _embed_color()
                if cor:
                    embed.color = cor
                await inter.edit_original_message(
                    content=None,
                    embed=embed,
                    components=[
                        disnake.ui.ActionRow(
                            disnake.ui.ChannelSelect(
                                custom_id=f"RG:select_add_canal:{tipo}",
                                placeholder="Escolha um canal de texto...",
                                channel_types=[disnake.ChannelType.text],
                                min_values=1,
                                max_values=1,
                            )
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"RG:nav:{tipo}"),
                        ),
                    ],
                )
            else:
                ckw = _container_kwargs()
                await inter.edit_original_message(
                    content=None,
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# Adicionar Canal — {label_sistema(tipo)}\nSelecione o canal de texto abaixo."),
                            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                            disnake.ui.ActionRow(
                                disnake.ui.ChannelSelect(
                                    custom_id=f"RG:select_add_canal:{tipo}",
                                    placeholder="Escolha um canal de texto...",
                                    channel_types=[disnake.ChannelType.text],
                                    min_values=1,
                                    max_values=1,
                                )
                            ),
                            **ckw,
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"RG:nav:{tipo}"),
                        ),
                    ],
                )
            return

        if cid.startswith("RG:tempo:"):
            tipo = cid.split(":", 2)[2]
            if tipo not in SISTEMAS:
                return
            await inter.response.send_modal(
                disnake.ui.Modal(
                    title=f"Intervalo — {label_sistema(tipo)}",
                    custom_id=f"RG:modal_tempo:{tipo}",
                    components=[
                        disnake.ui.TextInput(
                            label="Tempo em segundos (mínimo 1)",
                            placeholder="Ex: 30",
                            custom_id="tempo_segundos",
                            style=disnake.TextInputStyle.short,
                            min_length=1,
                            max_length=6,
                            required=True,
                        )
                    ],
                )
            )
            return

    # ── Select de remoção SFW ─────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def rg_selects(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RG:rm_canal:"):
            return

        tipo = cid.split(":", 2)[2]
        if tipo not in SISTEMAS:
            return
        await inter.response.defer()
        remover_canal(tipo, inter.values[0])
        await self._ir_sistema(inter, tipo)

    # ── ChannelSelect SFW ─────────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def rg_channel_select(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RG:select_add_canal:"):
            return
        tipo = cid.split(":", 2)[2]
        if tipo not in SISTEMAS:
            return
        await inter.response.defer()
        canal_id = str(inter.values[0].id) if hasattr(inter.values[0], "id") else str(inter.values[0])
        ok, msg = adicionar_canal(tipo, canal_id)
        if not ok:
            await inter.followup.send(f"❌ {msg}", ephemeral=True)
        await self._ir_sistema(inter, tipo)

    # ── Modais SFW (apenas intervalo) ─────────────────────────────────────────

    @commands.Cog.listener("on_modal_submit")
    async def rg_modais(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("RG:"):
            return

        if cid.startswith("RG:modal_tempo:"):
            tipo = cid.split(":", 2)[2]
            if tipo not in SISTEMAS:
                return
            valor = inter.text_values.get("tempo_segundos", "").strip()
            try:
                segundos = int(valor)
                if segundos < 1:
                    raise ValueError
            except ValueError:
                await inter.response.send_message("Informe um número válido (mínimo 1).", ephemeral=True)
                return
            await inter.response.defer()
            set_tempo(tipo, segundos)
            await self._ir_sistema(inter, tipo)
            return

        if cid == "RG:modal_criar_task":
            nome = inter.text_values.get("nome_task", "").strip()
            if not nome:
                await inter.response.send_message("Nome inválido.", ephemeral=True)
                return
            nsfw_val = (inter.values or {}).get("task_nsfw", ["sfw"])
            eh_nsfw = (nsfw_val[0] if isinstance(nsfw_val, list) else nsfw_val) == "nsfw"
            await inter.response.defer(ephemeral=True)
            tid, _ = criar_task(nome, nsfw=eh_nsfw)
            await self._ir_task(inter, tid)
            return

    # ── Botões de Task (RGT) ──────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def rgt_buttons(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RGT:"):
            return

        parts = cid.split(":", 2)
        acao  = parts[1] if len(parts) > 1 else ""
        tid   = parts[2] if len(parts) > 2 else ""

        if acao == "toggle":
            await inter.response.defer()
            toggle_task(tid)
            await self._ir_task(inter, tid)
            return

        if acao == "deletar":
            await inter.response.defer()
            deletar_task(tid)
            await self._ir_home(inter)
            return

        if acao == "tempo":
            await inter.response.send_modal(
                disnake.ui.Modal(
                    title="Intervalo da Task",
                    custom_id=f"RGT:modal_tempo:{tid}",
                    components=[
                        disnake.ui.TextInput(
                            label="Tempo em segundos (mínimo 1)",
                            placeholder="Ex: 60",
                            custom_id="tempo_segundos",
                            style=disnake.TextInputStyle.short,
                            min_length=1, max_length=6, required=True,
                        )
                    ],
                )
            )
            return

        if acao == "add_canal":
            await inter.response.defer()
            ckw = _container_kwargs()
            if _is_embed_mode():
                embed = disnake.Embed(title="Adicionar Canal — Task", description="Selecione o canal de texto abaixo.")
                cor = _embed_color()
                if cor: embed.color = cor
                await inter.edit_original_message(content=None, embed=embed, components=[
                    disnake.ui.ActionRow(
                        disnake.ui.ChannelSelect(custom_id=f"RGT:select_add_canal:{tid}", placeholder="Escolha um canal…",
                                                 channel_types=[disnake.ChannelType.text], min_values=1, max_values=1)
                    ),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"RGT:back:{tid}")),
                ])
            else:
                await inter.edit_original_message(content=None, components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay("# Adicionar Canal — Task\nSelecione o canal abaixo."),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        disnake.ui.ActionRow(
                            disnake.ui.ChannelSelect(custom_id=f"RGT:select_add_canal:{tid}", placeholder="Escolha um canal…",
                                                     channel_types=[disnake.ChannelType.text], min_values=1, max_values=1)
                        ),
                        **ckw,
                    ),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"RGT:back:{tid}")),
                ])
            return

        if acao == "back":
            await inter.response.defer()
            await self._ir_task(inter, tid)
            return

    # ── Selects de Task (RGT) ─────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def rgt_selects(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RGT:") and cid != "RG:select_task":
            return

        if cid == "RG:select_task":
            tid = inter.values[0]
            await inter.response.defer()
            await self._ir_task(inter, tid)
            return

        parts = cid.split(":", 2)
        acao  = parts[1] if len(parts) > 1 else ""
        tid   = parts[2] if len(parts) > 2 else ""

        if acao == "rm_canal":
            await inter.response.defer()
            remover_canal_task(tid, inter.values[0])
            await self._ir_task(inter, tid)
            return

        if acao == "select_add_canal":
            await inter.response.defer()
            canal_id = str(inter.values[0].id) if hasattr(inter.values[0], "id") else str(inter.values[0])
            ok, msg = adicionar_canal_task(tid, canal_id)
            if not ok:
                await inter.followup.send(f"{emoji.wrong} {msg}", ephemeral=True)
            await self._ir_task(inter, tid)
            return

        if acao == "select_tema":
            await inter.response.defer()
            valor = inter.values[0]
            set_tema_pinterest(tid, None if valor == "__membros__" else valor)
            await self._ir_task(inter, tid)
            return

    # ── Modais de Task (RGT) ──────────────────────────────────────────────────

    @commands.Cog.listener("on_modal_submit")
    async def rgt_modais(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("RGT:modal_tempo:"):
            return
        tid = cid.split(":", 3)[3] if cid.count(":") >= 3 else cid.split(":", 2)[2]
        valor = inter.text_values.get("tempo_segundos", "").strip()
        try:
            s = int(valor)
            if s < 1: raise ValueError
        except ValueError:
            await inter.response.send_message("Número inválido (mínimo 1).", ephemeral=True)
            return
        await inter.response.defer()
        set_tempo_task(tid, s)
        await self._ir_task(inter, tid)


# ══════════════════════════════════════════════════════════════════════════════
# NsfwGifsCog — busca na night-api a cada 30s e roteia por dimensão
# ══════════════════════════════════════════════════════════════════════════════

class NsfwGifsCog(commands.Cog):
    """
    Loop único que:
      1. Busca imagem aleatória da night-api a cada 30s.
      2. Detecta dimensões/formato da imagem.
      3. Roteia para o tipo correto (gif / icone / banner).
      4. Envia em todos os canais habilitados desse tipo (apenas se NSFW ativo).
      5. Se canal perder status NSFW → remove da lista e desativa o tipo se ficar vazio.
    """

    def __init__(self, bot: commands.Bot):
        self.bot     = bot
        self._task:   Optional[asyncio.Task] = None
        self._session: Optional[aiohttp.ClientSession] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def cog_load(self):
        self._session = aiohttp.ClientSession(
            headers={"authorization": _NIGHT_API_KEY},
            timeout=aiohttp.ClientTimeout(total=20),
        )
        if self._algum_ativo():
            self._iniciar_task()
        log.info("[NsfwGifs] Cog carregado.")

    async def cog_unload(self):
        if self._task and not self._task.done():
            self._task.cancel()
        if self._session and not self._session.closed:
            await self._session.close()
        log.info("[NsfwGifs] Cog descarregado.")

    # ── Task ──────────────────────────────────────────────────────────────────

    def _algum_ativo(self) -> bool:
        cfg = ler_config_nsfw()
        return any(
            cfg["sistemas"][t]["ligado"] and cfg["sistemas"][t]["canais"]
            for t in TIPOS_NSFW
        )

    def _iniciar_task(self):
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop(), name="nsfw_loop")
        log.debug("[NsfwGifs] Task iniciada.")

    def _parar_task(self):
        if self._task and not self._task.done():
            self._task.cancel()
            self._task = None
            log.debug("[NsfwGifs] Task encerrada.")

    # ── Loop principal ────────────────────────────────────────────────────────

    async def _loop(self):
        log.debug("[NsfwGifs] Loop iniciado.")
        while True:
            try:
                await asyncio.sleep(NSFW_INTERVALO_SEGUNDOS)

                cfg = ler_config_nsfw()

                # Verifica se ainda há algo ativo — encerra loop se não
                if not any(
                    cfg["sistemas"][t]["ligado"] and cfg["sistemas"][t]["canais"]
                    for t in TIPOS_NSFW
                ):
                    log.debug("[NsfwGifs] Nenhum tipo ativo. Encerrando loop.")
                    self._task = None
                    return

                # Busca imagem aleatória (endpoint fixo — a API roteia internamente)
                resultado = await self._fetch_imagem()
                if resultado is None:
                    continue

                url_img, dados_img = resultado

                # Detecta dimensões e decide o tipo
                fmt, w, h = _detectar_imagem(dados_img)
                tipo       = _rotear_tipo(fmt, w, h)
                log.debug("[NsfwGifs] %s → tipo=%s  (%dx%d)", endpoint, tipo, w, h)

                sistema = cfg["sistemas"][tipo]
                if not sistema["ligado"] or not sistema["canais"]:
                    log.debug("[NsfwGifs] Tipo %s inativo ou sem canais. Descartando.", tipo)
                    continue

                await self._enviar_para_canais(tipo, url_img, list(sistema["canais"]))

            except asyncio.CancelledError:
                log.debug("[NsfwGifs] Loop cancelado.")
                return
            except Exception:
                log.exception("[NsfwGifs] Erro inesperado no loop.")
                await asyncio.sleep(30)

    # ── Fetch da API ──────────────────────────────────────────────────────────

    async def _fetch_imagem(self) -> Optional[tuple[str, bytes]]:
        """
        GET _NIGHT_API_BASE → JSON com URL da imagem.
        GET na URL da imagem → bytes para detectar dimensões.
        Retorna (url, bytes) ou None se falhar.
        """
        try:
            async with self._session.get(_NIGHT_API_BASE) as resp:
                if resp.status != 200:
                    log.warning("[NsfwGifs] API status %s", resp.status)
                    return None
                data = await resp.json(content_type=None)

            url_img = (
                data.get("url")
                or data.get("image")
                or data.get("link")
                or (data.get("data") or {}).get("url")
                or (data.get("data") or {}).get("image")
            )
            if not url_img:
                log.warning("[NsfwGifs] Sem URL na resposta: %s", data)
                return None

            # Baixa os primeiros bytes para detectar dimensões (máx 64 KB)
            async with self._session.get(url_img) as resp_img:
                if resp_img.status != 200:
                    return None
                chunk = await resp_img.content.read(65536)

            return url_img, chunk

        except aiohttp.ClientError:
            log.exception("[NsfwGifs] Erro de rede ao buscar imagem.")
            return None

    # ── Envio nos canais ──────────────────────────────────────────────────────

    async def _enviar_para_canais(self, tipo: str, url: str, canais: list[str]):
        canais_invalidos: list[str] = []

        for canal_id in canais:
            canal = await self._resolver_canal(canal_id)

            if canal is None:
                log.warning("[NsfwGifs] Canal %s não encontrado. Removendo.", canal_id)
                canais_invalidos.append(canal_id)
                continue

            if not canal.nsfw:
                log.warning(
                    "[NsfwGifs] Canal %s perdeu status NSFW. Removendo e checando tipo %s.",
                    canal_id, tipo,
                )
                canais_invalidos.append(canal_id)
                continue

            try:
                await canal.send(url)
                log.debug("[NsfwGifs] Enviado em #%s (%s).", canal_id, tipo)
            except disnake.Forbidden:
                log.warning("[NsfwGifs] Sem permissão em %s. Removendo.", canal_id)
                canais_invalidos.append(canal_id)
            except Exception:
                log.exception("[NsfwGifs] Erro ao enviar em %s.", canal_id)

        # Remove canais inválidos/sem-nsfw e desativa o tipo se ficar sem canais
        if canais_invalidos:
            for cid in canais_invalidos:
                remover_canal_nsfw(tipo, cid)
            cfg_atualizada = ler_config_nsfw()
            if not cfg_atualizada["sistemas"][tipo]["canais"]:
                set_ligado_nsfw(tipo, False)
                log.info("[NsfwGifs] Tipo %s desativado (sem canais válidos).", tipo)

    async def _resolver_canal(self, canal_id: str) -> Optional[disnake.TextChannel]:
        try:
            canal = self.bot.get_channel(int(canal_id))
            if canal is None:
                canal = await self.bot.fetch_channel(int(canal_id))
            return canal if isinstance(canal, disnake.TextChannel) else None
        except Exception:
            return None

    # ══════════════════════════════════════════════════════════════════════════
    # Painéis NSFW
    # ══════════════════════════════════════════════════════════════════════════

    # ── Home NSFW ─────────────────────────────────────────────────────────────

    @staticmethod
    def Painel() -> list:
        cfg = ler_config_nsfw()
        ckw = _container_kwargs()

        select = disnake.ui.StringSelect(
            placeholder="Selecione um tipo para configurar…",
            custom_id="RGN:select:tipo",
            options=[
                disnake.SelectOption(
                    label=label_nsfw(t),
                    value=t,
                    emoji=emoji.on if cfg["sistemas"][t]["ligado"] else f"{emoji.off}",
                    description=(
                        f"{len(cfg['sistemas'][t]['canais'])} canal(is)"
                        f"  ·  {NSFW_INTERVALO_SEGUNDOS}s"
                    ),
                )
                for t in TIPOS_NSFW
            ],
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.more18} Random Gifs NSFW\n"
                    "-# Painel > Random Gifs > **NSFW**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    resumo_nsfw(cfg) + "\n\n"
                    "-# Canais precisam ter **NSFW** ativado no Discord.\n"
                    "-# A imagem buscada é roteada automaticamente pelo formato/dimensão.\n"
                    f"-# Intervalo fixo: `{NSFW_INTERVALO_SEGUNDOS}s`"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(select),
                **ckw,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RG:back:home"),
            ),
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        cfg = ler_config_nsfw()

        embed = disnake.Embed(
            title="Random Gifs NSFW",
            description=(
                f"{resumo_nsfw(cfg)}\n\n"
                f"Canais precisam ter **NSFW** ativado.\n"
                f"Intervalo fixo: `{NSFW_INTERVALO_SEGUNDOS}s`\n"
                "-# Imagens são roteadas automaticamente pelo formato/dimensão."
            ),
        )
        cor = _embed_color()
        if cor:
            embed.color = cor

        select = disnake.ui.StringSelect(
            placeholder="Selecione um tipo para configurar…",
            custom_id="RGN:select:tipo",
            options=[
                disnake.SelectOption(
                    label=label_nsfw(t),
                    value=t,
                    emoji=emoji.on if cfg["sistemas"][t]["ligado"] else f"{emoji.off}",
                    description=(
                        f"{len(cfg['sistemas'][t]['canais'])} canal(is)"
                        f"  ·  {NSFW_INTERVALO_SEGUNDOS}s"
                    ),
                )
                for t in TIPOS_NSFW
            ],
        )
        return embed, [
            disnake.ui.ActionRow(select),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RG:back:home"),
            ),
        ]

    # ── Painel por tipo NSFW ──────────────────────────────────────────────────

    @staticmethod
    def _painel_tipo(tipo: str) -> list:
        cfg     = ler_config_nsfw()
        sistema = cfg["sistemas"][tipo]
        ligado  = sistema["ligado"]
        canais  = sistema["canais"]
        nome    = label_nsfw(tipo)
        ckw     = _container_kwargs()

        toggle_label = "Ligado"    if ligado else "Desligado"
        toggle_style = disnake.ButtonStyle.success if ligado else disnake.ButtonStyle.grey

        # Descritivo do roteamento por tipo
        roteamento = {
            "gif":    "Recebe imagens em formato **GIF** (animadas).",
            "icone":  "Recebe imagens com proporção **quadrada** (~1:1).",
            "banner": "Recebe imagens com proporção **larga** (>1.5:1).",
        }

        children: list = [
            disnake.ui.TextDisplay(
                f"# {emoji.more18} {nome}\n"
                f"-# Painel > Random Gifs > NSFW > **{nome}**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**Status:** `{toggle_label}`\n"
                f"**Intervalo:** `{NSFW_INTERVALO_SEGUNDOS}s` (fixo)\n"
                f"**Roteamento:** {roteamento.get(tipo, '')}\n"
                f"**Canais ({len(canais)}/{MAX_CANAIS}):**\n"
                + (formatar_canais(canais) if canais else "`Nenhum canal configurado`")
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar Canal", style=disnake.ButtonStyle.grey, custom_id=f"RGN:add_canal:{tipo}", emoji="➕"),
                disnake.ui.Button(label=toggle_label,      style=toggle_style,             custom_id=f"RGN:toggle:{tipo}"),
            ),
        ]

        if canais:
            children.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Remover canal",
                        custom_id=f"RGN:rm_canal:{tipo}",
                        options=[
                            disnake.SelectOption(label=f"#{cid}", value=cid, description=f"ID: {cid}")
                            for cid in canais
                        ],
                    )
                )
            )

        return [
            disnake.ui.Container(*children, **ckw),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RGN:back:home"),
            ),
        ]

    @staticmethod
    def _painel_tipo_embed(tipo: str) -> tuple[disnake.Embed, list]:
        cfg     = ler_config_nsfw()
        sistema = cfg["sistemas"][tipo]
        ligado  = sistema["ligado"]
        canais  = sistema["canais"]
        nome    = label_nsfw(tipo)

        toggle_label = "Ligado"    if ligado else "Desligado"
        toggle_style = disnake.ButtonStyle.success if ligado else disnake.ButtonStyle.grey

        roteamento = {
            "gif":    "Recebe imagens em formato GIF (animadas).",
            "icone":  "Recebe imagens com proporção quadrada (~1:1).",
            "banner": "Recebe imagens com proporção larga (>1.5:1).",
        }

        embed = disnake.Embed(
            title=f"{emoji.more18} {nome}",
            description=(
                f"**Status:** `{toggle_label}`\n"
                f"**Intervalo:** `{NSFW_INTERVALO_SEGUNDOS}s` (fixo)\n"
                f"**Roteamento:** {roteamento.get(tipo, '')}\n"
                f"**Canais ({len(canais)}/{MAX_CANAIS}):**\n"
                + (formatar_canais(canais) if canais else "`Nenhum canal configurado`")
            ),
        )
        cor = _embed_color()
        if cor:
            embed.color = cor

        components: list = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Adicionar Canal", style=disnake.ButtonStyle.grey, custom_id=f"RGN:add_canal:{tipo}", emoji=emoji.plus),
                disnake.ui.Button(label=toggle_label,      style=toggle_style,             custom_id=f"RGN:toggle:{tipo}",   emoji=emoji.power),
            ),
        ]
        if canais:
            components.append(
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Remover canal…",
                        custom_id=f"RGN:rm_canal:{tipo}",
                        options=[
                            disnake.SelectOption(label=f"#{cid}", value=cid, description=f"ID: {cid}")
                            for cid in canais
                        ],
                    )
                )
            )
        components.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RGN:back:home"),
            )
        )
        return embed, components

    # ── Navegação NSFW ────────────────────────────────────────────────────────

    async def _ir_home_nsfw(self, inter: disnake.MessageInteraction):
        if _is_embed_mode():
            e, c = NsfwGifsCog.PainelEmbed()
            await inter.edit_original_message(content=None, embed=e, components=c)
        else:
            await inter.edit_original_message(content=None, components=NsfwGifsCog.Painel())

    async def _ir_tipo(self, inter: disnake.MessageInteraction, tipo: str):
        if _is_embed_mode():
            e, c = NsfwGifsCog._painel_tipo_embed(tipo)
            await inter.edit_original_message(content=None, embed=e, components=c)
        else:
            await inter.edit_original_message(content=None, components=NsfwGifsCog._painel_tipo(tipo))

    # ── Select de tipo NSFW ───────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def rgn_selects(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        if cid == "RGN:select:tipo":
            tipo = inter.values[0]
            if tipo not in TIPOS_NSFW:
                return
            await inter.response.defer()
            await self._ir_tipo(inter, tipo)
            return

        if cid.startswith("RGN:rm_canal:"):
            tipo = cid.split(":", 2)[2]
            if tipo not in TIPOS_NSFW:
                return
            await inter.response.defer()
            remover_canal_nsfw(tipo, inter.values[0])
            # Se ficar sem canais, desativa
            cfg_atual = ler_config_nsfw()
            if not cfg_atual["sistemas"][tipo]["canais"]:
                set_ligado_nsfw(tipo, False)
                self._parar_task_se_inativo()
            await self._ir_tipo(inter, tipo)
            return

    # ── Botões NSFW ───────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def rgn_buttons(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RGN:"):
            return

        # Home NSFW (vindo do painel principal ou do botão Voltar)
        if cid in ("RGN:nav:home", "RGN:back:home"):
            await inter.response.defer()
            await self._ir_home_nsfw(inter)
            return

        # Toggle
        if cid.startswith("RGN:toggle:"):
            tipo = cid.split(":", 2)[2]
            if tipo not in TIPOS_NSFW:
                return
            await inter.response.defer()

            cfg_antes   = ler_config_nsfw()
            canais_tipo = cfg_antes["sistemas"][tipo]["canais"]

            # Ligar: validar canais antes
            estava_ligado = cfg_antes["sistemas"][tipo]["ligado"]
            if not estava_ligado:
                if not canais_tipo:
                    await inter.followup.send(
                        f"{emoji.wrong} Adicione ao menos um canal antes de ligar o sistema.",
                        ephemeral=True,
                    )
                    await self._ir_tipo(inter, tipo)
                    return

                # Verificar se todos os canais são NSFW
                invalidos = await self._canais_sem_nsfw(canais_tipo)
                if invalidos:
                    mencoes = " ".join(f"<#{c}>" for c in invalidos)
                    await inter.followup.send(
                        f"{emoji.wrong} Os seguintes canais **não têm NSFW** ativado: {mencoes}\n"
                        "Ative o NSFW nesses canais ou remova-os da lista.",
                        ephemeral=True,
                    )
                    await self._ir_tipo(inter, tipo)
                    return

            novo_estado = toggle_nsfw(tipo)

            if novo_estado:
                self._iniciar_task()
            else:
                self._parar_task_se_inativo()

            await self._ir_tipo(inter, tipo)
            return

        # Adicionar canal
        if cid.startswith("RGN:add_canal:"):
            tipo = cid.split(":", 2)[2]
            if tipo not in TIPOS_NSFW:
                return
            await inter.response.defer()
            if _is_embed_mode():
                embed = disnake.Embed(title=f"Adicionar Canal NSFW — {label_nsfw(tipo)}", description="Selecione o canal abaixo.\n-# O canal precisa ter NSFW ativado.")
                cor = _embed_color()
                if cor:
                    embed.color = cor
                await inter.edit_original_message(
                    content=None,
                    embed=embed,
                    components=[
                        disnake.ui.ActionRow(
                            disnake.ui.ChannelSelect(
                                custom_id=f"RGN:select_add_canal:{tipo}",
                                placeholder="Escolha um canal NSFW...",
                                channel_types=[disnake.ChannelType.text],
                                min_values=1,
                                max_values=1,
                            )
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RGN:back:home"),
                        ),
                    ],
                )
            else:
                ckw = _container_kwargs()
                await inter.edit_original_message(
                    content=None,
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# Adicionar Canal NSFW — {label_nsfw(tipo)}\nSelecione o canal abaixo.\n-# O canal precisa ter **NSFW** ativado."),
                            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                            disnake.ui.ActionRow(
                                disnake.ui.ChannelSelect(
                                    custom_id=f"RGN:select_add_canal:{tipo}",
                                    placeholder="Escolha um canal NSFW...",
                                    channel_types=[disnake.ChannelType.text],
                                    min_values=1,
                                    max_values=1,
                                )
                            ),
                            **ckw,
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="RGN:back:home"),
                        ),
                    ],
                )
            return

    def _parar_task_se_inativo(self):
        if not self._algum_ativo():
            self._parar_task()

    async def _canais_sem_nsfw(self, canais: list[str]) -> list[str]:
        invalidos = []
        for cid in canais:
            canal = await self._resolver_canal(cid)
            if canal is None or not canal.nsfw:
                invalidos.append(cid)
        return invalidos

    # ── ChannelSelect NSFW ────────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def rgn_channel_select(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RGN:select_add_canal:"):
            return
        tipo = cid.split(":", 2)[2]
        if tipo not in TIPOS_NSFW:
            return
        await inter.response.defer()

        canal_id = str(inter.values[0].id) if hasattr(inter.values[0], "id") else str(inter.values[0])

        # Valida se o canal tem NSFW ativado
        canal = await self._resolver_canal(canal_id)
        if canal is None:
            await inter.followup.send(f"{emoji.wrong} Canal não encontrado ou inacessível.", ephemeral=True)
            await self._ir_tipo(inter, tipo)
            return

        if not canal.nsfw:
            await inter.followup.send(
                f"{emoji.wrong} {canal.mention} não tem **NSFW** ativado no Discord.\n"
                "Ative nas configurações do canal e tente novamente.",
                ephemeral=True,
            )
            await self._ir_tipo(inter, tipo)
            return

        ok, msg = adicionar_canal_nsfw(tipo, canal_id)
        if not ok:
            await inter.followup.send(f"{emoji.wrong} {msg}", ephemeral=True)
        await self._ir_tipo(inter, tipo)

    # ── Modais NSFW ───────────────────────────────────────────────────────────

    @commands.Cog.listener("on_modal_submit")
    async def rgn_modais(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("RGN:"):
            return
        # Nenhum modal NSFW definido por enquanto — placeholder para expansão futura.


# ══════════════════════════════════════════════════════════════════════════════
# Setup
# ══════════════════════════════════════════════════════════════════════════════

def setup(bot: commands.Bot):
    bot.add_cog(RandomGifsCog(bot))
    bot.add_cog(NsfwGifsCog(bot))