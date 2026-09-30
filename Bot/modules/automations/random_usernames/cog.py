"""
modules/automations/random_usernames/cog.py

Painel do módulo Random Usernames.

Toggles (todos OFF por padrão):
  🔤 3l     — habilita escaneamento de usernames com 3 letras
  🔤 4l     — habilita escaneamento de usernames com 4 letras
  🔁 Repeat — permite chars repetidos consecutivos (ex: aaaa, 7d7d, kkkk)

2l é sempre escaneado quando o sistema está ativo — não tem toggle.

Canal: um botão por comprimento (2l / 3l / 4l). Ao clicar, abre um
StringSelect com todos os canais de texto do servidor para o usuário escolher.
"""
from __future__ import annotations

import disnake
from disnake.ext import commands
from typing import Optional

from functions.emoji import emoji
from functions.database import database as db

from .helpers import (
    ler_config,
    toggle_campo,
    set_ativado,
    set_canal,
    resumo,
    tem_canal_minimo,
    _fmt_canal,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers internos
# ══════════════════════════════════════════════════════════════════════════════

def _ckw() -> dict:
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


def _is_embed() -> bool:
    return (db.get_document("custom_mode") or {}).get("mode") == "embed"


def _tem_token() -> bool:
    doc = db.get_document("tokens") or {}
    return bool(doc.get("list"))


def _canais_texto(guild: disnake.Guild) -> list[disnake.TextChannel]:
    """Retorna até 24 canais de texto ordenados por posição (reserva 1 slot pro remover)."""
    canais = [c for c in guild.channels if isinstance(c, disnake.TextChannel)]
    canais.sort(key=lambda c: c.position)
    return canais[:24]


# ══════════════════════════════════════════════════════════════════════════════
# Builder — painel principal (components v2)
# ══════════════════════════════════════════════════════════════════════════════

def _build_components(cfg: dict) -> list:
    ckw     = _ckw()
    ativado = cfg["ativado"]
    t3l     = cfg["toggle_3l"]
    t4l     = cfg["toggle_4l"]
    t_rep   = cfg["toggle_rep"]

    aviso = (
        f"\n\n{emoji.wrong} -# Nenhum token cadastrado. Vá em **Configurações > Tokens** para adicionar."
        if not _tem_token() else ""
    )

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.members} Random Usernames\n"
                "-# Painel > Automações > **Random Usernames**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(resumo(cfg) + aviso),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="3l",
                    style=disnake.ButtonStyle.success if t3l else disnake.ButtonStyle.grey,
                    custom_id="RU:toggle:toggle_3l",
                    emoji=emoji.power,
                ),
                disnake.ui.Button(
                    label="4l",
                    style=disnake.ButtonStyle.success if t4l else disnake.ButtonStyle.grey,
                    custom_id="RU:toggle:toggle_4l",
                    emoji=emoji.power,
                ),
                disnake.ui.Button(
                    label="Repeat",
                    style=disnake.ButtonStyle.success if t_rep else disnake.ButtonStyle.grey,
                    custom_id="RU:toggle:toggle_rep",
                    emoji=emoji.power,
                ),
            ),
         #   disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

            # ── Canais por comprimento ────────────────────────────────────────
       #     disnake.ui.TextDisplay("-# Canal de envio para cada comprimento:"),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Canal 2l",
                    style=disnake.ButtonStyle.blurple if cfg.get("canal_2l") else disnake.ButtonStyle.grey,
                    custom_id="RU:set_canal:2l",
                    emoji=emoji.textc,
                ),
                disnake.ui.Button(
                    label="Canal 3l",
                    style=disnake.ButtonStyle.blurple if cfg.get("canal_3l") else disnake.ButtonStyle.grey,
                    custom_id="RU:set_canal:3l",
                    emoji=emoji.textc,
                    disabled=not t3l,
                ),
                disnake.ui.Button(
                    label="Canal 4l",
                    style=disnake.ButtonStyle.blurple if cfg.get("canal_4l") else disnake.ButtonStyle.grey,
                    custom_id="RU:set_canal:4l",
                    emoji=emoji.textc,
                    disabled=not t4l,
                ),
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

            # ── Ativar / Desativar ────────────────────────────────────────────
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Sistema Ativo" if ativado else "Sistema Inativo",
                    style=disnake.ButtonStyle.success if ativado else disnake.ButtonStyle.danger,
                    emoji=emoji.power,
                    custom_id="RU:toggle_sistema",
                    disabled=(not _tem_token() and not ativado),
                ),
            ),
            **ckw,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="VoltarAutomações",
            ),
        ),
    ]


# ══════════════════════════════════════════════════════════════════════════════
# Builder — painel principal (embed)
# ══════════════════════════════════════════════════════════════════════════════

def _build_embed(cfg: dict) -> tuple[disnake.Embed, list]:
    ativado = cfg["ativado"]
    t3l     = cfg["toggle_3l"]
    t4l     = cfg["toggle_4l"]
    t_rep   = cfg["toggle_rep"]

    aviso = (
        f"\n{emoji.wrong} Nenhum token cadastrado. Vá em **Configurações > Tokens**."
        if not _tem_token() else ""
    )

    embed = disnake.Embed(title="Random Usernames", description=resumo(cfg) + aviso)
    cor   = _embed_color()
    if cor:
        embed.color = cor

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="3l",
                style=disnake.ButtonStyle.success if t3l else disnake.ButtonStyle.grey,
                custom_id="RU:toggle:toggle_3l",
                emoji=emoji.power,
            ),
            disnake.ui.Button(
                label="4l",
                style=disnake.ButtonStyle.success if t4l else disnake.ButtonStyle.grey,
                custom_id="RU:toggle:toggle_4l",
                emoji=emoji.power,
            ),
            disnake.ui.Button(
                label="Repeat",
                style=disnake.ButtonStyle.success if t_rep else disnake.ButtonStyle.grey,
                custom_id="RU:toggle:toggle_rep",
                emoji=emoji.power,
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Canal 2l",
                style=disnake.ButtonStyle.blurple if cfg.get("canal_2l") else disnake.ButtonStyle.grey,
                custom_id="RU:set_canal:2l",
                emoji=emoji.textc,
            ),
            disnake.ui.Button(
                label="Canal 3l",
                style=disnake.ButtonStyle.blurple if cfg.get("canal_3l") else disnake.ButtonStyle.grey,
                custom_id="RU:set_canal:3l",
                emoji=emoji.textc,
                disabled=not t3l,
            ),
            disnake.ui.Button(
                label="Canal 4l",
                style=disnake.ButtonStyle.blurple if cfg.get("canal_4l") else disnake.ButtonStyle.grey,
                custom_id="RU:set_canal:4l",
                emoji=emoji.textc,
                disabled=not t4l,
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Sistema Ativo" if ativado else "Sistema Inativo",
                style=disnake.ButtonStyle.success if ativado else disnake.ButtonStyle.danger,
                emoji=emoji.power,
                custom_id="RU:toggle_sistema",
                disabled=(not _tem_token() and not ativado),
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="VoltarAutomações",
            ),
        ),
    ]
    return embed, components


# ══════════════════════════════════════════════════════════════════════════════
# Builder — select de canal do servidor (components v2)
# ══════════════════════════════════════════════════════════════════════════════

_LABEL_COMP = {"2l": "2 Letras", "3l": "3 Letras", "4l": "4 Letras"}


def _build_canal_select(comp: str, guild: disnake.Guild, cfg: dict) -> list:
    ckw          = _ckw()
    canal_atual  = cfg.get(f"canal_{comp}")
    canais_texto = _canais_texto(guild)
    label        = _LABEL_COMP.get(comp, comp)

    options: list[disnake.SelectOption] = []

    if canal_atual:
        options.append(
            disnake.SelectOption(
                label="Remover canal configurado",
                value="__remover__",
                description=f"Limpa o canal de {label}",
            )
        )

    for canal in canais_texto:
        options.append(
            disnake.SelectOption(
                label=f"# {canal.name}",
                value=str(canal.id),
                description=f"ID: {canal.id}",
                default=(str(canal.id) == canal_atual),
                emoji=emoji.arrow if str(canal.id) == canal_atual else None,
            )
        )

    if not options:
        options.append(
            disnake.SelectOption(label="Nenhum canal de texto encontrado", value="__vazio__")
        )

    info = f"-# Atual: {_fmt_canal(canal_atual)}"

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.textc} Canal — {label}\n"
                f"-# Painel > Random Usernames > **Canal {comp}**"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"Selecione o canal onde os usernames de **{label}** disponíveis serão enviados.\n"
                f"{info}"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder=f"Selecione um canal para {label}…",
                    custom_id=f"RU:select_canal:{comp}",
                    options=options,
                )
            ),
            **ckw,
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="RU:back_home",
            ),
        ),
    ]


def _build_canal_select_embed(comp: str, guild: disnake.Guild, cfg: dict) -> tuple[disnake.Embed, list]:
    canal_atual  = cfg.get(f"canal_{comp}")
    canais_texto = _canais_texto(guild)
    label        = _LABEL_COMP.get(comp, comp)

    embed = disnake.Embed(
        title=f"{emoji.textc} Canal — {label}",
        description=(
            f"Selecione o canal onde os usernames de **{label}** disponíveis serão enviados.\n"
            f"Atual: {_fmt_canal(canal_atual)}"
        ),
    )
    cor = _embed_color()
    if cor:
        embed.color = cor

    options: list[disnake.SelectOption] = []
    if canal_atual:
        options.append(
            disnake.SelectOption(
                label="Remover canal configurado",
                value="__remover__",
                description=f"Limpa o canal de {label}",
            )
        )
    for canal in canais_texto:
        options.append(
            disnake.SelectOption(
                label=f"# {canal.name}",
                value=str(canal.id),
                description=f"ID: {canal.id}",
                default=(str(canal.id) == canal_atual),
                emoji=emoji.arrow if str(canal.id) == canal_atual else None,
            )
        )
    if not options:
        options.append(disnake.SelectOption(label="Nenhum canal encontrado", value="__vazio__"))

    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder=f"Selecione um canal para {label}…",
                custom_id=f"RU:select_canal:{comp}",
                options=options,
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Voltar",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.back,
                custom_id="RU:back_home",
            ),
        ),
    ]
    return embed, components


# ══════════════════════════════════════════════════════════════════════════════
# COG
# ══════════════════════════════════════════════════════════════════════════════

class RandomUsernamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def Painel() -> list:
        return _build_components(ler_config())

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        return _build_embed(ler_config())

    # ── Navegação ─────────────────────────────────────────────────────────────

    async def _ir_home(self, inter: disnake.MessageInteraction):
        cfg = ler_config()
        if _is_embed():
            embed, components = _build_embed(cfg)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(content=None, components=_build_components(cfg))

    async def _ir_select_canal(self, inter: disnake.MessageInteraction, comp: str):
        cfg = ler_config()
        if _is_embed():
            embed, components = _build_canal_select_embed(comp, inter.guild, cfg)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(
                content=None,
                components=_build_canal_select(comp, inter.guild, cfg),
            )

    # ══════════════════════════════════════════════════════════════════════════
    # Botões
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_button_click")
    async def ru_buttons(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RU:"):
            return

        # ── Toggles 3l / 4l / repeat ─────────────────────────────────────────
        if cid.startswith("RU:toggle:"):
            campo = cid.split(":", 2)[2]
            if campo not in ("toggle_3l", "toggle_4l", "toggle_rep"):
                return
            await inter.response.defer()
            toggle_campo(campo)
            await self._ir_home(inter)
            return

        # ── Botão de canal → vai para select de canais do servidor ────────────
        if cid.startswith("RU:set_canal:"):
            comp = cid.split(":", 2)[2]
            if comp not in ("2l", "3l", "4l"):
                return
            await inter.response.defer()
            await self._ir_select_canal(inter, comp)
            return

        # ── Voltar ao home ────────────────────────────────────────────────────
        if cid == "RU:back_home":
            await inter.response.defer()
            await self._ir_home(inter)
            return

        # ── Toggle sistema ────────────────────────────────────────────────────
        if cid == "RU:toggle_sistema":
            await inter.response.defer()
            cfg = ler_config()

            if not cfg["ativado"]:
                if not _tem_token():
                    await inter.followup.send(
                        f"{emoji.wrong} Nenhum **token de usuário** cadastrado.\n"
                        "Vá em **Configurações → Tokens** e adicione um token válido antes de ativar.",
                        ephemeral=True,
                    )
                    return
                if not tem_canal_minimo(cfg):
                    await inter.followup.send(
                        f"{emoji.wrong} Configure ao menos o **Canal 2l** antes de ativar o sistema.",
                        ephemeral=True,
                    )
                    return

            set_ativado(not cfg["ativado"])
            await self._ir_home(inter)
            return

    # ══════════════════════════════════════════════════════════════════════════
    # Select — escolha de canal do servidor
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_dropdown")
    async def ru_selects(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("RU:select_canal:"):
            return

        comp  = cid.split(":", 2)[2]
        valor = inter.values[0]

        await inter.response.defer()

        if valor == "__vazio__":
            await self._ir_home(inter)
            return

        set_canal(comp, None if valor == "__remover__" else valor)

        # Se removeu canal_2l e sistema estava ativo, desativa
        cfg = ler_config()
        if not tem_canal_minimo(cfg) and cfg["ativado"]:
            set_ativado(False)

        await self._ir_home(inter)


def setup(bot: commands.Bot):
    bot.add_cog(RandomUsernamesCog(bot))