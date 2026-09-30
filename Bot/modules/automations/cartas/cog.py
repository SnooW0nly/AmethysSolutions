"""
modules/automations/cartas/cog.py

Sistema de Cartas (Tellonym) — Amethys Bot
Painel de configuração + Task (reenvio a cada 1h) + Todos os listeners.
"""
from __future__ import annotations

import asyncio
import io
from datetime import datetime
from typing import Optional

import aiohttp
import disnake
from disnake.ext import commands, tasks

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from . import helpers
from .helpers import (
    CartaImageGenerator,
    accent, color,
    build_carta_buttons, build_moderacao_buttons,
    load_json, save_json, gerar_carta_id,
    PENDENTES_JSON, APROVADAS_JSON, COMENTARIOS_JSON,
)

_gen = CartaImageGenerator()


# ─── Download de bytes ────────────────────────────────────────────────────────

async def _fetch_bytes(url: str) -> bytes | None:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    return await r.read()
    except Exception:
        return None


# ─── Gerar e enviar imagem de carta ──────────────────────────────────────────

async def _gerar_imagem_carta(
    bot: commands.Bot,
    guild: disnake.Guild,
    autor_nome: str,
    autor_avatar_url: str | None,
    para_nome: str | None,
    mensagem: str,
    cor_hex: str,
    qtd_comentarios: int = 0,
) -> io.BytesIO:
    avatar_bytes = await _fetch_bytes(autor_avatar_url) if autor_avatar_url else None
    icon_bytes   = await _fetch_bytes(str(guild.icon.url)) if guild.icon else None
    return _gen.generate(
        mensagem        = mensagem,
        cor_hex         = cor_hex,
        para_nome       = para_nome,
        autor_nome      = autor_nome,
        autor_avatar_bytes = avatar_bytes,
        servidor_nome   = guild.name,
        servidor_icon_bytes = icon_bytes,
        qtd_comentarios = qtd_comentarios,
    )


# ─── Mensagem "Enviar Tellonym" (container ou embed) ─────────────────────────

def _build_enviar_components(mode: str, config: dict, primary_hex: str | None) -> list:
    cor_carta = config.get("cor", "#7289DA")
    btn = disnake.ui.Button(
        label="Enviar Tellonym",
        emoji=emoji.heart2,
        style=disnake.ButtonStyle.blurple,
        custom_id="Cartas_AbrirModal",
    )
    if mode == "embed":
        return [disnake.ui.ActionRow(btn)]
    else:
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    "# Sistema de Cartas\n"
                    "-# Envie uma carta anônima para alguém do servidor."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    "Clique no botão abaixo para enviar uma carta.\n"
                    "Você pode optar por se identificar ou permanecer anônimo."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(btn),
                **accent(cor_carta),
            )
        ]


def _build_enviar_embed(config: dict) -> disnake.Embed:
    cor_carta = config.get("cor", "#7289DA")
    embed = disnake.Embed(
        title="Sistema de Cartas",
        description=(
            "Envie uma carta anônima para alguém do servidor.\n"
            "Clique no botão abaixo para começar.\n"
            "Você pode optar por se identificar ou permanecer anônimo."
        ),
        color=color(cor_carta),
    )
    return embed


# ─── Cog principal ────────────────────────────────────────────────────────────

class CartasCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task_reenvio.start()

    def cog_unload(self):
        self._task_reenvio.cancel()

    # ── Painel Components ─────────────────────────────────────────────────────

    @staticmethod
    def Painel() -> list:
        config         = helpers.carregar_config()
        ativado        = config.get("ativado", False)
        canal_id       = config.get("canal_id")
        cargo_id       = config.get("cargo_id")
        staff_cargo_id = config.get("staff_cargo_id")
        canal_logs_id  = config.get("canal_logs_id")
        cor            = config.get("cor", "#7289DA")
        logs_on        = config.get("logs_ativados", False)
        primary_hex    = db.get_document("custom_colors").get("primary")

        canal_txt      = f"<#{canal_id}>"        if canal_id       else "`Não configurado`"
        cargo_txt      = f"<@&{cargo_id}>"       if cargo_id       else "`Qualquer um`"
        staff_txt      = f"<@&{staff_cargo_id}>" if staff_cargo_id else "`Não configurado`"
        canal_logs_txt = f"<#{canal_logs_id}>"   if canal_logs_id  else "`Não configurado`"

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_on else emoji.off} **Logs:** `{'Ativado' if logs_on else 'Desativado'}`\n"
            f"{emoji.textc} **Canal:** {canal_txt}\n"
            f"{emoji.textc} **Canal de logs:** {canal_logs_txt}\n"
            f"{emoji.role} **Cargo para enviar:** {cargo_txt}\n"
            f"{emoji.role} **Cargo de staff:** {staff_txt}\n"
            f"{emoji.colors}  **Cor da carta:** `{cor}`"
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    "-# Painel > Automações > **Sistema de Cartas**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Envie cartas anônimas estilo Tellonym dentro do servidor."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", emoji=emoji.power,
                                      style=disnake.ButtonStyle.grey,
                                      custom_id="Cartas_ToggleAtivo",
                                      disabled=not bool(canal_id and staff_cargo_id)),
                    disnake.ui.Button(label="Canal", emoji=emoji.textc,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="Cartas_ConfigCanal"),
                    disnake.ui.Button(label="Cargo envio", emoji=emoji.role,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="Cartas_ConfigCargo"),
                    disnake.ui.Button(label="Staff", emoji=emoji.shield,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="Cartas_ConfigStaff"),
                    disnake.ui.Button(label="Cor", emoji=emoji.colors,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="Cartas_ConfigCor"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Logs", emoji=emoji.power,
                                      style=disnake.ButtonStyle.grey,
                                      custom_id="Cartas_ToggleLogs"),
                    disnake.ui.Button(label="Canal Logs", emoji=emoji.textc,
                                      style=disnake.ButtonStyle.blurple,
                                      custom_id="Cartas_ConfigCanalLogs"),
                    disnake.ui.Button(label="Remover cargo envio", emoji=emoji.minus,
                                      style=disnake.ButtonStyle.red,
                                      custom_id="Cartas_RemoverCargo",
                                      disabled=not bool(cargo_id)),
                    disnake.ui.Button(label="Remover staff", emoji=emoji.minus,
                                      style=disnake.ButtonStyle.red,
                                      custom_id="Cartas_RemoverStaff",
                                      disabled=not bool(staff_cargo_id)),
                    disnake.ui.Button(label="Remover canal logs", emoji=emoji.minus,
                                      style=disnake.ButtonStyle.red,
                                      custom_id="Cartas_RemoverCanalLogs",
                                      disabled=not bool(canal_logs_id)),
                ),
                **accent(primary_hex),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="VoltarAutomações"),
            ),
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        config         = helpers.carregar_config()
        ativado        = config.get("ativado", False)
        canal_id       = config.get("canal_id")
        cargo_id       = config.get("cargo_id")
        staff_cargo_id = config.get("staff_cargo_id")
        canal_logs_id  = config.get("canal_logs_id")
        cor            = config.get("cor", "#7289DA")
        logs_on        = config.get("logs_ativados", False)
        primary_hex    = db.get_document("custom_colors").get("primary")

        canal_txt      = f"<#{canal_id}>"        if canal_id       else "`Não configurado`"
        cargo_txt      = f"<@&{cargo_id}>"       if cargo_id       else "`Qualquer um`"
        staff_txt      = f"<@&{staff_cargo_id}>" if staff_cargo_id else "`Não configurado`"
        canal_logs_txt = f"<#{canal_logs_id}>"   if canal_logs_id  else "`Não configurado`"

        embed = disnake.Embed(
            title="Sistema de Cartas",
            description="Envie cartas anônimas estilo Tellonym dentro do servidor.",
        )
        if primary_hex:
            embed.color = color(primary_hex)
        embed.add_field(name="Configurações", inline=False, value=(
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_on else emoji.off} **Logs:** `{'Ativado' if logs_on else 'Desativado'}`\n"
            f"{emoji.textc} **Canal:** {canal_txt}\n"
            f"{emoji.textc} **Canal de logs:** {canal_logs_txt}\n"
            f"{emoji.role} **Cargo para enviar:** {cargo_txt}\n"
            f"{emoji.role} **Cargo de staff:** {staff_txt}\n"
            f"{emoji.colors}  **Cor da carta:** `{cor}`"
        ))

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", emoji=emoji.power,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Cartas_ToggleAtivo",
                                  disabled=not bool(canal_id and staff_cargo_id)),
                disnake.ui.Button(label="Canal", emoji=emoji.textc,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Cartas_ConfigCanal"),
                disnake.ui.Button(label="Cargo envio", emoji=emoji.role,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Cartas_ConfigCargo"),
                disnake.ui.Button(label="Staff", emoji=emoji.shield,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Cartas_ConfigStaff"),
                disnake.ui.Button(label="Cor", emoji=emoji.colors,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Cartas_ConfigCor"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Logs", emoji=emoji.power,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Cartas_ToggleLogs"),
                disnake.ui.Button(label="Canal Logs", emoji=emoji.textc,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="Cartas_ConfigCanalLogs"),
                disnake.ui.Button(label="Remover cargo envio", emoji=emoji.minus,
                                  style=disnake.ButtonStyle.red,
                                  custom_id="Cartas_RemoverCargo",
                                  disabled=not bool(cargo_id)),
                disnake.ui.Button(label="Remover staff", emoji=emoji.minus,
                                  style=disnake.ButtonStyle.red,
                                  custom_id="Cartas_RemoverStaff",
                                  disabled=not bool(staff_cargo_id)),
                disnake.ui.Button(label="Remover canal logs", emoji=emoji.minus,
                                  style=disnake.ButtonStyle.red,
                                  custom_id="Cartas_RemoverCanalLogs",
                                  disabled=not bool(canal_logs_id)),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="VoltarAutomações"),
            ),
        ]
        return embed, components

    # ─────────────────────────────────────────────────────────────────────────
    # TASK — reenviar mensagem "Enviar Tellonym" a cada 1 hora
    # ─────────────────────────────────────────────────────────────────────────

    @tasks.loop(hours=1)
    async def _task_reenvio(self):
        config   = helpers.carregar_config()
        if not config.get("ativado"):
            return

        canal_id = config.get("canal_id")
        if not canal_id:
            return

        canal: disnake.TextChannel | None = self.bot.get_channel(int(canal_id))
        if not canal:
            return

        mode        = db.get_document("custom_mode").get("mode")
        primary_hex = db.get_document("custom_colors").get("primary")

        # Apagar mensagem antiga
        msg_id = config.get("mensagem_id")
        if msg_id:
            try:
                old_msg = await canal.fetch_message(int(msg_id))
                await old_msg.delete()
            except (disnake.NotFound, disnake.HTTPException):
                pass

        # Enviar nova
        try:
            if mode == "embed":
                embed = _build_enviar_embed(config)
                comps = _build_enviar_components("embed", config, primary_hex)
                new_msg = await canal.send(embed=embed, components=comps)
            else:
                comps = _build_enviar_components("container", config, primary_hex)
                new_msg = await canal.send(components=comps)

            config["mensagem_id"] = str(new_msg.id)
            helpers.salvar_config(config)
        except disnake.HTTPException:
            pass

    @_task_reenvio.before_loop
    async def _before_task(self):
        await self.bot.wait_until_ready()

    async def _forcar_reenvio(self):
        """Chama o reenvio imediatamente (ex: ao ativar o sistema)."""
        config   = helpers.carregar_config()
        canal_id = config.get("canal_id")
        if not canal_id:
            return

        canal: disnake.TextChannel | None = self.bot.get_channel(int(canal_id))
        if not canal:
            return

        mode        = db.get_document("custom_mode").get("mode")
        primary_hex = db.get_document("custom_colors").get("primary")

        msg_id = config.get("mensagem_id")
        if msg_id:
            try:
                old = await canal.fetch_message(int(msg_id))
                await old.delete()
            except Exception:
                pass

        try:
            if mode == "embed":
                embed = _build_enviar_embed(config)
                comps = _build_enviar_components("embed", config, primary_hex)
                new_msg = await canal.send(embed=embed, components=comps)
            else:
                comps = _build_enviar_components("container", config, primary_hex)
                new_msg = await canal.send(components=comps)

            config["mensagem_id"] = str(new_msg.id)
            helpers.salvar_config(config)
        except Exception:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # LISTENERS
    # ─────────────────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def _cartas_button_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Cartas_"):
            return

        # ── Botões que abrem modal — ANTES de qualquer wait ───────────────────
        if cid == "Cartas_AbrirModal":
            config   = helpers.carregar_config()
            cargo_id = config.get("cargo_id")
            if cargo_id:
                roles = [r.id for r in getattr(inter.author, "roles", [])]
                if int(cargo_id) not in roles:
                    await inter.response.send_message(
                        "Você não tem o cargo necessário para enviar uma carta.", ephemeral=True
                    )
                    return
            await inter.response.send_modal(EnviarCartaModal(self.bot))
            return

        if cid.startswith("Cartas_comentar_"):
            carta_id = cid.replace("Cartas_comentar_", "")
            await inter.response.send_modal(ComentarCartaModal(carta_id, self.bot))
            return

        if cid == "Cartas_ConfigCor":
            await inter.response.send_modal(CorModal())
            return

        # ── Botões de aprovação/recusa (staff) ────────────────────────────────
        if cid.startswith("Cartas_aprovar_") or cid.startswith("Cartas_recusar_"):
            await self._handle_moderacao(inter, cid)
            return

        # ── Botões de ver comentários (sem modal, mas sem wait também) ────────
        if cid.startswith("Cartas_vercomentarios_"):
            await self._handle_ver_comentarios(inter, cid)
            return

        # ── Botões do painel (com wait) ───────────────────────────────────────
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        primary_hex = db.get_document("custom_colors").get("primary")

        if cid == "Cartas_ToggleAtivo":
            config  = helpers.carregar_config()
            novo    = not config.get("ativado", False)
            config["ativado"] = novo
            helpers.salvar_config(config)
            if novo:
                asyncio.create_task(self._forcar_reenvio())
            await self._render_painel(inter, mode)
            return

        if cid == "Cartas_ToggleLogs":
            config = helpers.carregar_config()
            config["logs_ativados"] = not config.get("logs_ativados", False)
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "Cartas_RemoverCargo":
            config = helpers.carregar_config()
            config["cargo_id"] = None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "Cartas_RemoverStaff":
            config = helpers.carregar_config()
            config["staff_cargo_id"] = None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "Cartas_RemoverCanalLogs":
            config = helpers.carregar_config()
            config["canal_logs_id"] = None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "Cartas_VoltarPainel":
            await self._render_painel(inter, mode)
            return

        if cid == "Cartas_ConfigCanal":
            select_row = disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal das cartas...",
                    custom_id="Cartas_SelectCanal",
                    min_values=1, max_values=1,
                    channel_types=[disnake.ChannelType.text],
                )
            )
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Cartas_VoltarPainel"),
            )
            if mode == "embed":
                emb = disnake.Embed(title="Configurar Canal",
                                    description="Selecione o canal onde ficará o botão 'Enviar Tellonym'.")
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            "-# Painel > Automações > Cartas > **Canal**"
                        ),
                        disnake.ui.Separator(),
                        select_row,
                        **accent(primary_hex),
                    ),
                    voltar,
                ])
            return

        if cid == "Cartas_ConfigCanalLogs":
            select_row = disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal de logs das cartas...",
                    custom_id="Cartas_SelectCanalLogs",
                    min_values=1, max_values=1,
                    channel_types=[disnake.ChannelType.text],
                )
            )
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Cartas_VoltarPainel"),
            )
            if mode == "embed":
                emb = disnake.Embed(title="Canal de Logs",
                                    description="Selecione o canal onde serão enviadas as cartas pendentes para aprovação.")
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            "-# Painel > Automações > Cartas > **Canal de Logs**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay("Selecione o canal onde serão enviadas as cartas pendentes para aprovação."),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        select_row,
                        **accent(primary_hex),
                    ),
                    voltar,
                ])
            return

        if cid == "Cartas_ConfigCargo":
            select_row = disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Cargo necessário para enviar cartas...",
                    custom_id="Cartas_SelectCargo",
                    min_values=1, max_values=1,
                )
            )
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Cartas_VoltarPainel"),
            )
            desc = "Selecione o cargo necessário para enviar cartas.\nSe não configurar, qualquer membro pode enviar."
            if mode == "embed":
                emb = disnake.Embed(title="Cargo para Enviar", description=desc)
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            "-# Painel > Automações > Cartas > **Cargo para Enviar**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(desc),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        select_row,
                        **accent(primary_hex),
                    ),
                    voltar,
                ])
            return

        if cid == "Cartas_ConfigStaff":
            select_row = disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Cargo de staff para aprovar cartas...",
                    custom_id="Cartas_SelectStaff",
                    min_values=1, max_values=1,
                )
            )
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Cartas_VoltarPainel"),
            )
            desc = "Selecione o cargo de staff que pode aprovar ou recusar cartas nos logs."
            if mode == "embed":
                emb = disnake.Embed(title="Cargo de Staff", description=desc)
                if primary_hex:
                    emb.color = color(primary_hex)
                await inter.edit_original_message(content=None, embed=emb, components=[select_row, voltar])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            "-# Painel > Automações > Cartas > **Cargo de Staff**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(desc),
                        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                        select_row,
                        **accent(primary_hex),
                    ),
                    voltar,
                ])
            return

    # ── Moderação (aprovar/recusar) ───────────────────────────────────────────

    async def _handle_moderacao(self, inter: disnake.MessageInteraction, cid: str):
        config         = helpers.carregar_config()
        staff_cargo_id = config.get("staff_cargo_id")

        # Verificar cargo de staff
        if staff_cargo_id:
            roles = [r.id for r in getattr(inter.author, "roles", [])]
            if int(staff_cargo_id) not in roles:
                await inter.response.send_message("Você não tem permissão para moderar cartas.", ephemeral=True)
                return

        await inter.response.defer(ephemeral=True)

        if cid.startswith("Cartas_aprovar_"):
            carta_id = cid.replace("Cartas_aprovar_", "")
            await self._aprovar_carta(inter, carta_id, config)
        else:
            carta_id = cid.replace("Cartas_recusar_", "")
            await self._recusar_carta(inter, carta_id)

    async def _aprovar_carta(self, inter: disnake.MessageInteraction, carta_id: str, config: dict):
        pendentes = load_json(PENDENTES_JSON)
        carta     = pendentes.get(carta_id)
        if not carta:
            await inter.followup.send("Carta não encontrada (já processada?).", ephemeral=True)
            return

        canal_id = config.get("canal_id")
        canal: disnake.TextChannel | None = self.bot.get_channel(int(canal_id)) if canal_id else None
        if not canal:
            await inter.followup.send("Canal configurado não encontrado.", ephemeral=True)
            return

        mode = db.get_document("custom_mode").get("mode")
        cor  = config.get("cor", "#7289DA")

        try:
            buf = await _gerar_imagem_carta(
                bot           = self.bot,
                guild         = inter.guild,
                autor_nome    = carta.get("autor_nome", "Anônimo"),
                autor_avatar_url = carta.get("autor_avatar_url"),
                para_nome     = carta.get("para_nome"),
                mensagem      = carta.get("mensagem", ""),
                cor_hex       = cor,
                qtd_comentarios = 0,
            )

            file = disnake.File(buf, filename=f"carta_{carta_id}.png")
            comps = [build_carta_buttons(carta_id)]

            canal_msg = await canal.send(file=file, components=comps)

            # Salvar como aprovada
            aprovadas = load_json(APROVADAS_JSON)
            aprovadas[carta_id] = {
                **carta,
                "canal_msg_id": str(canal_msg.id),
                "aprovado_em":  datetime.now().isoformat(),
                "aprovado_por": inter.author.id,
            }
            save_json(APROVADAS_JSON, aprovadas)

            # Inicializar comentários
            comentarios = load_json(COMENTARIOS_JSON)
            comentarios.setdefault(carta_id, [])
            save_json(COMENTARIOS_JSON, comentarios)

        except Exception as e:
            await inter.followup.send(f"Erro ao enviar carta: {e}", ephemeral=True)
            return

        # Remover dos pendentes
        pendentes.pop(carta_id, None)
        save_json(PENDENTES_JSON, pendentes)

        # Desativar botões na mensagem de log
        try:
            await inter.message.edit(components=[
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Aprovada ✅", style=disnake.ButtonStyle.green,
                                      custom_id="noop", disabled=True),
                )
            ])
        except Exception:
            pass

        await inter.followup.send("Carta aprovada e enviada no canal.", ephemeral=True)

        # Log
        anonimo = carta.get("anonimo", True)
        desc_log = (
            f"**Carta #{carta_id[-6:]}** foi **aprovada** por {inter.author.mention}.\n"
            f"**Remetente:** {'Anônimo' if anonimo else carta.get('autor_nome', '?')}\n"
            f"**Para:** {carta.get('para_nome') or 'Nenhum'}"
        )
        await helpers.enviar_log(self.bot, "Carta Aprovada", desc_log)

    async def _recusar_carta(self, inter: disnake.MessageInteraction, carta_id: str):
        pendentes = load_json(PENDENTES_JSON)
        carta     = pendentes.pop(carta_id, None)
        if not carta:
            await inter.followup.send("Carta não encontrada (já processada?).", ephemeral=True)
            return

        save_json(PENDENTES_JSON, pendentes)

        try:
            await inter.message.edit(components=[
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Recusada ❌", style=disnake.ButtonStyle.red,
                                      custom_id="noop", disabled=True),
                )
            ])
        except Exception:
            pass

        await inter.followup.send("Carta recusada e removida.", ephemeral=True)

        anonimo = carta.get("anonimo", True)
        desc_log = (
            f"**Carta #{carta_id[-6:]}** foi **recusada** por {inter.author.mention}.\n"
            f"**Remetente:** {'Anônimo' if anonimo else carta.get('autor_nome', '?')}"
        )
        await helpers.enviar_log(self.bot, "Carta Recusada", desc_log)

    # ── Ver comentários ────────────────────────────────────────────────────────

    async def _handle_ver_comentarios(self, inter: disnake.MessageInteraction, cid: str):
        carta_id    = cid.replace("Cartas_vercomentarios_", "")
        comentarios = load_json(COMENTARIOS_JSON)
        lista       = comentarios.get(carta_id, [])
        mode        = db.get_document("custom_mode").get("mode")
        primary_hex = db.get_document("custom_colors").get("primary")

        if not lista:
            await inter.response.send_message("Nenhum comentário ainda.", ephemeral=True)
            return

        texto = "\n".join(
            f"**{c.get('autor_nome', '?')}:** {c.get('conteudo', '')}"
            for c in lista[-15:]
        )
        if len(lista) > 15:
            texto = f"*... e mais {len(lista) - 15} comentário(s) anteriores*\n" + texto

        if mode == "embed":
            config = helpers.carregar_config()
            emb = disnake.Embed(title=f"Comentários ({len(lista)})", description=texto)
            emb.color = color(config.get("cor", "#7289DA"))
            await inter.response.send_message(embed=emb, ephemeral=True)
        else:
            config = helpers.carregar_config()
            await inter.response.send_message(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# Comentários ({len(lista)})\n{texto}"),
                        **accent(config.get("cor", "#7289DA")),
                    )
                ],
                ephemeral=True,
            )

    # ── Helpers de render ─────────────────────────────────────────────────────

    async def _render_painel(self, inter: disnake.MessageInteraction, mode: str):
        if mode == "embed":
            emb, comps = self.PainelEmbed()
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(components=self.Painel())

    # ── Dropdowns ─────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_dropdown")
    async def _cartas_select_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Cartas_"):
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "Cartas_SelectCanal":
            config = helpers.carregar_config()
            config["canal_id"] = inter.values[0]
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "Cartas_SelectCargo":
            config = helpers.carregar_config()
            config["cargo_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "Cartas_SelectStaff":
            config = helpers.carregar_config()
            config["staff_cargo_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return

        if cid == "Cartas_SelectCanalLogs":
            config = helpers.carregar_config()
            config["canal_logs_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter, mode)
            return


# ─── Modais ──────────────────────────────────────────────────────────────────

class EnviarCartaModal(disnake.ui.Modal):
    """Modal com 3 campos para envio da carta."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__(
            title="Enviar Carta",
            custom_id="Cartas_EnviarModal",
            components=[
                disnake.ui.TextInput(
                    label="Seu ID (opcional — remove anonimato)",
                    placeholder="Cole seu ID do Discord aqui para se identificar",
                    custom_id="autor_id",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    min_length=0,
                    max_length=20,
                ),
                disnake.ui.TextInput(
                    label="Para quem? (opcional)",
                    placeholder="Ex: @fulano — aparecerá na carta",
                    custom_id="para_nome",
                    style=disnake.TextInputStyle.short,
                    required=False,
                    min_length=0,
                    max_length=50,
                ),
                disnake.ui.TextInput(
                    label="Sua mensagem",
                    placeholder="Escreva sua carta aqui...",
                    custom_id="mensagem",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    min_length=5,
                    max_length=800,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        autor_id_raw = inter.text_values.get("autor_id", "").strip()
        para_nome    = inter.text_values.get("para_nome", "").strip() or None
        mensagem     = inter.text_values.get("mensagem", "").strip()

        await inter.response.defer(ephemeral=True)

        config = helpers.carregar_config()
        cor    = config.get("cor", "#7289DA")

        # Resolver identidade do autor
        anonimo        = True
        autor_nome     = "Anônimo"
        autor_avatar_url: str | None = None

        if autor_id_raw:
            try:
                uid    = int(autor_id_raw)
                member = inter.guild.get_member(uid) or await inter.guild.fetch_member(uid)
                if member:
                    anonimo          = False
                    autor_nome       = member.display_name
                    autor_avatar_url = str(member.display_avatar.url)
            except Exception:
                pass  # ID inválido → continua anônimo

        carta_id       = gerar_carta_id()
        logs_ativados  = config.get("logs_ativados", False)
        staff_cargo_id = config.get("staff_cargo_id")
        mode           = db.get_document("custom_mode").get("mode")
        primary_hex    = db.get_document("custom_colors").get("primary")

        # Gerar imagem
        try:
            buf = await _gerar_imagem_carta(
                bot              = self.bot,
                guild            = inter.guild,
                autor_nome       = autor_nome,
                autor_avatar_url = autor_avatar_url,
                para_nome        = para_nome,
                mensagem         = mensagem,
                cor_hex          = cor,
            )
        except Exception as e:
            await inter.followup.send(f"Erro ao gerar a carta: {e}", ephemeral=True)
            return

        # ── Sem logs: aprovação automática ───────────────────────────────────
        if not logs_ativados:
            canal_id = config.get("canal_id")
            canal: disnake.TextChannel | None = self.bot.get_channel(int(canal_id)) if canal_id else None
            if not canal:
                await inter.followup.send("Canal de cartas não configurado.", ephemeral=True)
                return
            try:
                file  = disnake.File(buf, filename=f"carta_{carta_id}.png")
                comps = [build_carta_buttons(carta_id)]
                canal_msg = await canal.send(file=file, components=comps)

                aprovadas = load_json(APROVADAS_JSON)
                aprovadas[carta_id] = {
                    "autor_id":        inter.author.id if not anonimo else None,
                    "autor_nome":      autor_nome,
                    "autor_avatar_url": autor_avatar_url,
                    "para_nome":       para_nome,
                    "mensagem":        mensagem,
                    "anonimo":         anonimo,
                    "canal_msg_id":    str(canal_msg.id),
                    "aprovado_em":     datetime.now().isoformat(),
                    "aprovado_por":    None,
                }
                save_json(APROVADAS_JSON, aprovadas)

                comentarios = load_json(COMENTARIOS_JSON)
                comentarios.setdefault(carta_id, [])
                save_json(COMENTARIOS_JSON, comentarios)
            except Exception as e:
                await inter.followup.send(f"Erro ao enviar carta: {e}", ephemeral=True)
                return

            await inter.followup.send(
                f"{emoji.correct} Carta enviada com sucesso!",
                ephemeral=True,
            )
            return

        # ── Com logs: enviar para moderação ──────────────────────────────────
        canal_logs = await helpers.obter_canal_logs(self.bot)
        if not canal_logs:
            await inter.followup.send(
                "Canal de logs não configurado. Peça ao admin para configurar.", ephemeral=True
            )
            return

        # Montar conteúdo de revisão para os logs
        staff_mencao = f"<@&{staff_cargo_id}>" if staff_cargo_id else ""
        desc_log = (
            f"{staff_mencao}\n"
            f"**Remetente:** {'Anônimo' if anonimo else f'{autor_nome} (`{inter.author.id}`)'}\n"
            f"**Para:** {para_nome or 'Nenhum'}\n"
            f"**Carta #{carta_id[-6:]}** aguardando aprovação."
        )

        file = disnake.File(buf, filename=f"carta_{carta_id}.png")
        mod_comps = build_moderacao_buttons(carta_id)

        try:
            if mode == "embed":
                emb = disnake.Embed(
                    title="Nova Carta Pendente",
                    description=desc_log,
                    color=color(cor),
                )
                log_msg = await canal_logs.send(embed=emb, file=file, components=mod_comps)
            else:
                log_msg = await canal_logs.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"{staff_mencao + chr(10) if staff_mencao else ''}"
                                f"# 📬 Nova Carta Pendente\n{desc_log}"
                            ),
                            **accent(primary_hex),
                        ),
                        *mod_comps,
                    ],
                    file=file,
                )
        except Exception as e:
            await inter.followup.send(f"Erro ao enviar para revisão: {e}", ephemeral=True)
            return

        # Salvar pendente
        pendentes = load_json(PENDENTES_JSON)
        pendentes[carta_id] = {
            "autor_id":       inter.author.id if not anonimo else None,
            "autor_nome":     autor_nome,
            "autor_avatar_url": autor_avatar_url,
            "para_nome":      para_nome,
            "mensagem":       mensagem,
            "anonimo":        anonimo,
            "log_msg_id":     str(log_msg.id),
            "log_canal_id":   str(canal_logs.id),
            "enviado_em":     datetime.now().isoformat(),
        }
        save_json(PENDENTES_JSON, pendentes)

        await inter.followup.send(
            f"{emoji.correct} Carta enviada para revisão! Ela será publicada após aprovação do staff.",
            ephemeral=True,
        )


class ComentarCartaModal(disnake.ui.Modal):
    def __init__(self, carta_id: str, bot: commands.Bot):
        self.carta_id = carta_id
        self.bot      = bot
        super().__init__(
            title="Comentar Carta",
            custom_id=f"Cartas_ComentarModal_{carta_id}",
            components=[
                disnake.ui.TextInput(
                    label="Seu comentário",
                    placeholder="Escreva seu comentário...",
                    custom_id="comentario",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    min_length=1,
                    max_length=500,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        conteudo = inter.text_values.get("comentario", "").strip()

        comentarios = load_json(COMENTARIOS_JSON)
        lista       = comentarios.get(self.carta_id, [])
        lista.append({
            "autor_id":   inter.author.id,
            "autor_nome": inter.author.display_name,
            "conteudo":   conteudo,
            "criado_em":  datetime.now().isoformat(),
        })
        comentarios[self.carta_id] = lista
        save_json(COMENTARIOS_JSON, comentarios)

        await inter.response.send_message("Comentário adicionado! 💬", ephemeral=True)

        # Reatualizar imagem e botões da carta no canal
        config   = helpers.carregar_config()
        aprovadas = load_json(APROVADAS_JSON)
        carta     = aprovadas.get(self.carta_id)
        if not carta:
            return

        canal_id    = config.get("canal_id")
        canal_msg_id = carta.get("canal_msg_id")
        cor          = config.get("cor", "#7289DA")
        mode         = db.get_document("custom_mode").get("mode")

        if not canal_id or not canal_msg_id:
            return

        try:
            canal = self.bot.get_channel(int(canal_id))
            if not canal:
                return

            msg   = await canal.fetch_message(int(canal_msg_id))
            comps = [build_carta_buttons(self.carta_id)]
            # Apenas atualiza os botões (contador de comentários) sem recriar a imagem
            await msg.edit(components=comps)
        except Exception:
            pass


class CorModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Configurar Cor da Carta",
            custom_id="Cartas_CorModal",
            components=[
                disnake.ui.TextInput(
                    label="Cor em HEX",
                    placeholder="Ex: #FF5733 ou 7289DA",
                    custom_id="cor_hex",
                    style=disnake.TextInputStyle.short,
                    required=True,
                    min_length=3,
                    max_length=7,
                )
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        raw  = inter.text_values.get("cor_hex", "").strip().lstrip("#")
        mode = db.get_document("custom_mode").get("mode")

        # Validar hex
        try:
            if len(raw) not in (3, 6):
                raise ValueError
            int(raw, 16)
        except ValueError:
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)
            await inter.followup.send("Cor inválida. Use formato HEX como `#FF5733`.", ephemeral=True)
            return

        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        config = helpers.carregar_config()
        config["cor"] = f"#{raw.upper()}"
        helpers.salvar_config(config)

        cog: CartasCog | None = inter.bot.get_cog("CartasCog")
        if cog:
            await cog._render_painel(inter, mode)


def setup(bot: commands.Bot):
    bot.add_cog(CartasCog(bot))