"""
modules/utilitarios/comunidade/tagbio/cog.py

Sistema de Cargo por Tag/Bio — Painel de configuração + listener do botão público.
A task de verificação periódica está em tasks/utilitarios/tsk_tagbio.py
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

# Importa o builder de anúncio (igual MsgAuto — SEM a parte de botões)
from commands.admin.anunciar.builder import Builder
from commands.admin.anunciar.components.helper import Helper as AnunciarHelper

from . import helpers
from .helpers import (
    accent, color, _primary_hex, _mode,
    get_mensagem_data, set_mensagem_data, clear_mensagem_field,
)

DISCORD_API_BASE = "https://discord.com/api/v10"


# ─── Modais de edição de mensagem (igual MsgAuto, sem botão) ─────────────────

class DefinirMensagemModal(disnake.ui.Modal):
    def __init__(self):
        data = get_mensagem_data()
        super().__init__(
            title="Definir Mensagem",
            custom_id="TagBio_MsgModal_Mensagem",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem", custom_id="content",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Texto que aparecerá junto ao botão 'Receber Cargo'",
                    value=data.get("content", ""),
                    max_length=2000, required=True,
                )
            ],
        )


class DefinirEmbedModal(disnake.ui.Modal):
    def __init__(self):
        data = get_mensagem_data()
        emb = data.get("embed", {})
        super().__init__(
            title="Definir Embed",
            custom_id="TagBio_MsgModal_Embed",
            components=[
                disnake.ui.TextInput(label="Título", custom_id="embed_title",
                                     style=disnake.TextInputStyle.short, required=False,
                                     value=emb.get("title", "")),
                disnake.ui.TextInput(label="Descrição", custom_id="embed_description",
                                     style=disnake.TextInputStyle.paragraph,
                                     placeholder="Descrição do embed", required=True,
                                     value=emb.get("description", "")),
                disnake.ui.TextInput(label="Cor (Hex)", custom_id="embed_color",
                                     style=disnake.TextInputStyle.short, required=False,
                                     placeholder="#FFFFFF", value=emb.get("color", "")),
                disnake.ui.TextInput(label="Footer", custom_id="embed_footer",
                                     style=disnake.TextInputStyle.short, required=False,
                                     value=emb.get("footer", "")),
            ],
        )


class DefinirImagensModal(disnake.ui.Modal):
    def __init__(self):
        data = get_mensagem_data()
        emb = data.get("embed", {})
        has_embed = bool(emb.get("title") or emb.get("description"))
        comps = [
            disnake.ui.TextInput(label="URL da imagem externa", custom_id="externalImage",
                                 style=disnake.TextInputStyle.short, required=False,
                                 value=data.get("externalImage", "")),
        ]
        if has_embed:
            comps += [
                disnake.ui.TextInput(label="URL do Banner do Embed", custom_id="banner",
                                     style=disnake.TextInputStyle.short, required=False,
                                     value=emb.get("banner", "")),
                disnake.ui.TextInput(label="URL da Thumbnail do Embed", custom_id="thumbnail",
                                     style=disnake.TextInputStyle.short, required=False,
                                     value=emb.get("thumbnail", "")),
            ]
        super().__init__(title="Definir Imagens", custom_id="TagBio_MsgModal_Imagens", components=comps)


class DefinirContainerModal(disnake.ui.Modal):
    def __init__(self):
        data = get_mensagem_data()
        super().__init__(
            title="Definir Container",
            custom_id="TagBio_MsgModal_Container",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo do container", custom_id="container_content",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Use {{separator}}, {{color:#...}}, {{image url=...}}",
                    required=True, value=data.get("container", ""),
                )
            ],
        )


class DefinirTagModal(disnake.ui.Modal):
    def __init__(self):
        config = helpers.carregar_config()
        super().__init__(
            title="Definir Tag obrigatória",
            custom_id="TagBio_DefinirTag",
            components=[
                disnake.ui.TextInput(
                    label="Texto da tag",
                    custom_id="tag_texto",
                    style=disnake.TextInputStyle.short,
                    placeholder="Ex: .gg/meuservidor — deve estar no nome/tag do usuário",
                    value=config.get("tag_texto") or "",
                    required=True, max_length=64,
                )
            ],
        )


class DefinirBioModal(disnake.ui.Modal):
    def __init__(self):
        config = helpers.carregar_config()
        super().__init__(
            title="Definir Bio obrigatória",
            custom_id="TagBio_DefinirBio",
            components=[
                disnake.ui.TextInput(
                    label="Texto que deve estar na bio",
                    custom_id="bio_texto",
                    style=disnake.TextInputStyle.paragraph,
                    placeholder="Ex: discord.gg/meuservidor — deve estar na bio do usuário",
                    value=config.get("bio_texto") or "",
                    required=True, max_length=190,
                )
            ],
        )


class DefinirCooldownModal(disnake.ui.Modal):
    def __init__(self):
        config = helpers.carregar_config()
        super().__init__(
            title="Definir Cooldown de Verificação",
            custom_id="TagBio_DefinirCooldown",
            components=[
                disnake.ui.TextInput(
                    label="Intervalo em minutos (mínimo 1)",
                    custom_id="cooldown",
                    style=disnake.TextInputStyle.short,
                    placeholder="Ex: 60 (1 hora), 1440 (24h)",
                    value=str(config.get("cooldown_minutos", 60)),
                    required=True, min_length=1, max_length=6,
                )
            ],
        )


# ─── COG principal ────────────────────────────────────────────────────────────

class TagBioCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ══════════════════════════════════════════════════════════════════════════
    # PAINEL PRINCIPAL
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def Painel() -> list:
        config      = helpers.carregar_config()
        ph          = _primary_hex()
        ativado     = config.get("ativado", False)
        tag_ativo   = config.get("tag_ativo", False)
        bio_ativo   = config.get("bio_ativo", False)
        cargo_id    = config.get("cargo_id")
        cooldown    = config.get("cooldown_minutos", 60)
        logs_pub_id = config.get("canal_logs_publico_id")
        logs_prv_id = config.get("canal_logs_privado_id")
        tag_texto   = config.get("tag_texto")
        bio_texto   = config.get("bio_texto")

        cargo_txt    = f"<@&{cargo_id}>"  if cargo_id    else "`Não configurado`"
        logs_pub_txt = f"<#{logs_pub_id}>" if logs_pub_id else "`Não configurado`"
        logs_prv_txt = f"<#{logs_prv_id}>" if logs_prv_id else "`Não configurado`"
        tag_txt      = f"`{tag_texto}`"   if tag_texto   else "`Não configurado`"
        bio_txt      = f"`{bio_texto[:30]}…`" if bio_texto and len(bio_texto) > 30 else (f"`{bio_texto}`" if bio_texto else "`Não configurado`")

        # Só pode ativar se tiver cargo configurado E (tag ou bio ativada com texto)
        pode_ativar = bool(
            cargo_id and (
                (tag_ativo and tag_texto) or
                (bio_ativo and bio_texto)
            )
        )

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if tag_ativo else emoji.off} **Verificação de Tag:** `{'Ativada' if tag_ativo else 'Desativada'}`\n"
            f"{emoji.on if bio_ativo else emoji.off} **Verificação de Bio:** `{'Ativada' if bio_ativo else 'Desativada'}`\n"
            f"{emoji.role} **Cargo:** {cargo_txt}\n"
            f"{emoji.time} **Cooldown task:** `{cooldown} min`\n"
            f"{emoji.textc} **Tag obrigatória:** {tag_txt}\n"
            f"{emoji.textc} **Bio obrigatória:** {bio_txt}\n"
            f"{emoji.textc} **Logs públicos:** {logs_pub_txt}\n"
            f"{emoji.textc} **Logs privados:** {logs_prv_txt}"
        )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Comunidade > **Cargo por Tag/Bio**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Dê cargos automaticamente a membros com a tag/bio configurada."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                # Linha 1: toggles + cargo
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="", emoji=emoji.power,
                        style=disnake.ButtonStyle.grey,
                        custom_id="TagBio_ToggleAtivo",
                        disabled=not pode_ativar and not ativado,
                    ),
                    disnake.ui.Button(
                        label="Tag", emoji=emoji.on if tag_ativo else emoji.off,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="TagBio_ToggleTag",
                    ),
                    disnake.ui.Button(
                        label="Bio", emoji=emoji.on if bio_ativo else emoji.off,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="TagBio_ToggleBio",
                    ),
                    disnake.ui.Button(
                        label="Cargo", emoji=emoji.role,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="TagBio_ConfigCargo",
                    ),
                ),
                # Linha 2: configurações de texto e mensagem
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Definir Tag", emoji=emoji.edit,
                        style=disnake.ButtonStyle.grey,
                        custom_id="TagBio_DefinirTagBtn",
                        disabled=not tag_ativo,
                    ),
                    disnake.ui.Button(
                        label="Definir Bio", emoji=emoji.edit,
                        style=disnake.ButtonStyle.grey,
                        custom_id="TagBio_DefinirBioBtn",
                        disabled=not bio_ativo,
                    ),
                    disnake.ui.Button(
                        label="Cooldown", emoji=emoji.time,
                        style=disnake.ButtonStyle.grey,
                        custom_id="TagBio_DefinirCooldownBtn",
                    ),
                    disnake.ui.Button(
                        label="Editar Mensagem", emoji=emoji.message,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="TagBio_EditarMensagem",
                    ),
                ),
                # Linha 3: canais de log
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Logs Públicos", emoji=emoji.textc,
                        style=disnake.ButtonStyle.grey,
                        custom_id="TagBio_ConfigLogsPublico",
                    ),
                    disnake.ui.Button(
                        label="Logs Privados", emoji=emoji.textc,
                        style=disnake.ButtonStyle.grey,
                        custom_id="TagBio_ConfigLogsPrivado",
                    ),
                    disnake.ui.Button(
                        label="Remover Cargo", emoji=emoji.minus,
                        style=disnake.ButtonStyle.red,
                        custom_id="TagBio_RemoverCargo",
                        disabled=not cargo_id,
                    ),
                ),
                **accent(ph),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar", emoji=emoji.back,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Comunidade_VoltarFeature",
                ),
            ),
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list]:
        config      = helpers.carregar_config()
        ph          = _primary_hex()
        ativado     = config.get("ativado", False)
        tag_ativo   = config.get("tag_ativo", False)
        bio_ativo   = config.get("bio_ativo", False)
        cargo_id    = config.get("cargo_id")
        cooldown    = config.get("cooldown_minutos", 60)
        logs_pub_id = config.get("canal_logs_publico_id")
        logs_prv_id = config.get("canal_logs_privado_id")
        tag_texto   = config.get("tag_texto")
        bio_texto   = config.get("bio_texto")

        cargo_txt    = f"<@&{cargo_id}>"   if cargo_id    else "`Não configurado`"
        logs_pub_txt = f"<#{logs_pub_id}>" if logs_pub_id else "`Não configurado`"
        logs_prv_txt = f"<#{logs_prv_id}>" if logs_prv_id else "`Não configurado`"
        tag_txt      = f"`{tag_texto}`"    if tag_texto   else "`Não configurado`"
        bio_txt      = f"`{bio_texto[:30]}…`" if bio_texto and len(bio_texto) > 30 else (f"`{bio_texto}`" if bio_texto else "`Não configurado`")

        pode_ativar = bool(
            cargo_id and (
                (tag_ativo and tag_texto) or
                (bio_ativo and bio_texto)
            )
        )

        embed = disnake.Embed(
            title="Cargo por Tag/Bio",
            description="Dê cargos automaticamente a membros com a tag/bio configurada.",
        )
        if ph:
            embed.color = color(ph)
        embed.add_field(name="Configurações", inline=False, value=(
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if tag_ativo else emoji.off} **Tag:** `{'Ativada' if tag_ativo else 'Desativada'}`\n"
            f"{emoji.on if bio_ativo else emoji.off} **Bio:** `{'Ativada' if bio_ativo else 'Desativada'}`\n"
            f"{emoji.role} **Cargo:** {cargo_txt}\n"
            f"{emoji.time} **Cooldown:** `{cooldown} min`\n"
            f"{emoji.textc} **Tag:** {tag_txt} | **Bio:** {bio_txt}\n"
            f"{emoji.textc} **Logs públicos:** {logs_pub_txt}\n"
            f"{emoji.textc} **Logs privados:** {logs_prv_txt}"
        ))

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", emoji=emoji.power,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TagBio_ToggleAtivo",
                                  disabled=not pode_ativar and not ativado),
                disnake.ui.Button(label="Tag", emoji=emoji.on if tag_ativo else emoji.off,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="TagBio_ToggleTag"),
                disnake.ui.Button(label="Bio", emoji=emoji.on if bio_ativo else emoji.off,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="TagBio_ToggleBio"),
                disnake.ui.Button(label="Cargo", emoji=emoji.role,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="TagBio_ConfigCargo"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Definir Tag", emoji=emoji.edit,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TagBio_DefinirTagBtn",
                                  disabled=not tag_ativo),
                disnake.ui.Button(label="Definir Bio", emoji=emoji.edit,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TagBio_DefinirBioBtn",
                                  disabled=not bio_ativo),
                disnake.ui.Button(label="Cooldown", emoji=emoji.time,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TagBio_DefinirCooldownBtn"),
                disnake.ui.Button(label="Editar Mensagem", emoji=emoji.message,
                                  style=disnake.ButtonStyle.blurple,
                                  custom_id="TagBio_EditarMensagem"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Logs Públicos", emoji=emoji.textc,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TagBio_ConfigLogsPublico"),
                disnake.ui.Button(label="Logs Privados", emoji=emoji.textc,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TagBio_ConfigLogsPrivado"),
                disnake.ui.Button(label="Remover Cargo", emoji=emoji.minus,
                                  style=disnake.ButtonStyle.red,
                                  custom_id="TagBio_RemoverCargo",
                                  disabled=not cargo_id),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="Comunidade_VoltarFeature"),
            ),
        ]
        return embed, components

    # ══════════════════════════════════════════════════════════════════════════
    # PAINEL DO EDITOR DE MENSAGEM
    # ══════════════════════════════════════════════════════════════════════════

    @staticmethod
    def PainelEditorMensagem() -> list:
        ph   = _primary_hex()
        data = get_mensagem_data()

        has_content   = bool(data.get("content"))
        emb           = data.get("embed", {})
        has_embed     = any(emb.get(k) for k in ("title", "description", "footer"))
        has_image     = bool(data.get("externalImage") or emb.get("banner") or emb.get("thumbnail"))
        has_container = bool(data.get("container"))
        other_disabled = has_container

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Comunidade > Cargo por Tag/Bio > **Editor de Mensagem**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure a mensagem que será enviada no canal com o botão **Receber Cargo**.\n"
                    "-# O botão de receber cargo é adicionado automaticamente."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", emoji=emoji.delete,
                                      style=disnake.ButtonStyle.red,
                                      custom_id="TagBio_Msg_ApagarContent",
                                      disabled=not has_content or other_disabled),
                    disnake.ui.Button(label="Definir Mensagem", emoji=emoji.message,
                                      style=disnake.ButtonStyle.grey,
                                      custom_id="TagBio_Msg_DefinirMensagem",
                                      disabled=other_disabled),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", emoji=emoji.delete,
                                      style=disnake.ButtonStyle.red,
                                      custom_id="TagBio_Msg_ApagarEmbed",
                                      disabled=not has_embed or other_disabled),
                    disnake.ui.Button(label="Definir Embed", emoji=emoji.embed,
                                      style=disnake.ButtonStyle.grey,
                                      custom_id="TagBio_Msg_DefinirEmbed",
                                      disabled=other_disabled),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", emoji=emoji.delete,
                                      style=disnake.ButtonStyle.red,
                                      custom_id="TagBio_Msg_ApagarImagens",
                                      disabled=not has_image),
                    disnake.ui.Button(label="Definir Imagens", emoji=emoji.image,
                                      style=disnake.ButtonStyle.grey,
                                      custom_id="TagBio_Msg_DefinirImagens"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", emoji=emoji.delete,
                                      style=disnake.ButtonStyle.red,
                                      custom_id="TagBio_Msg_ApagarContainer",
                                      disabled=not has_container),
                    disnake.ui.Button(label="Definir Container", emoji=emoji.commands,
                                      style=disnake.ButtonStyle.grey,
                                      custom_id="TagBio_Msg_DefinirContainer",
                                      disabled=(has_content or has_embed) and not has_container),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Visualizar", emoji=emoji.search,
                                      style=disnake.ButtonStyle.grey,
                                      custom_id="TagBio_Msg_Visualizar",
                                      disabled=not (has_content or has_embed or has_container or has_image)),
                    disnake.ui.Button(label="Publicar no Canal", emoji=emoji.textc,
                                      style=disnake.ButtonStyle.green,
                                      custom_id="TagBio_Msg_Publicar",
                                      disabled=not (has_content or has_embed or has_container)),
                ),
                **accent(ph),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TagBio_VoltarPainel"),
            ),
        ]

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS DE RENDER
    # ══════════════════════════════════════════════════════════════════════════

    async def _render_painel(self, inter: disnake.MessageInteraction):
        mode = _mode()
        if mode == "embed":
            emb, comps = self.PainelEmbed()
            await inter.edit_original_message(content=None, embed=emb, components=comps)
        else:
            await inter.edit_original_message(components=self.Painel())

    async def _render_editor(self, inter: disnake.MessageInteraction):
        await inter.edit_original_message(components=self.PainelEditorMensagem())

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENER — BOTÕES DO PAINEL
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_button_click")
    async def _tagbio_button_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ── Botões que abrem modal — ANTES de qualquer defer/wait ─────────────
        if cid == "TagBio_DefinirTagBtn":
            await inter.response.send_modal(DefinirTagModal())
            return

        if cid == "TagBio_DefinirBioBtn":
            await inter.response.send_modal(DefinirBioModal())
            return

        if cid == "TagBio_DefinirCooldownBtn":
            await inter.response.send_modal(DefinirCooldownModal())
            return

        if cid == "TagBio_Msg_DefinirMensagem":
            await inter.response.send_modal(DefinirMensagemModal())
            return

        if cid == "TagBio_Msg_DefinirEmbed":
            await inter.response.send_modal(DefinirEmbedModal())
            return

        if cid == "TagBio_Msg_DefinirImagens":
            await inter.response.send_modal(DefinirImagensModal())
            return

        if cid == "TagBio_Msg_DefinirContainer":
            await inter.response.send_modal(DefinirContainerModal())
            return

        # ── Botão público: "Receber Cargo" ────────────────────────────────────
        if cid == "TagBio_ReceberCargo":
            await self._handle_receber_cargo(inter)
            return

        # ── Botões do painel que precisam de wait ─────────────────────────────
        if not cid.startswith("TagBio_"):
            return

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        ph = _primary_hex()

        # ── Toggle ativo ──────────────────────────────────────────────────────
        if cid == "TagBio_ToggleAtivo":
            config = helpers.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

        if cid == "TagBio_ToggleTag":
            config = helpers.carregar_config()
            config["tag_ativo"] = not config.get("tag_ativo", False)
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

        if cid == "TagBio_ToggleBio":
            config = helpers.carregar_config()
            bio_novo = not config.get("bio_ativo", False)
            # Só pode ativar bio se houver pelo menos um token de usuário cadastrado
            if bio_novo and not helpers.get_any_token():
                await inter.edit_original_message(
                    components=self.Painel() if mode != "embed" else None,
                    embed=self.PainelEmbed()[0] if mode == "embed" else None,
                )
                await inter.followup.send(
                    f"{emoji.warn} **Não é possível ativar verificação de Bio sem um token de usuário cadastrado.**\n"
                    "-# Acesse Painel > Configurações > Tokens e adicione um token de conta.",
                    ephemeral=True,
                )
                return
            config["bio_ativo"] = bio_novo
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

        # ── Cargo ─────────────────────────────────────────────────────────────
        if cid == "TagBio_ConfigCargo":
            voltar = disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back,
                                  style=disnake.ButtonStyle.grey,
                                  custom_id="TagBio_VoltarPainel"),
            )
            select_row = disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Selecione o cargo a ser concedido...",
                    custom_id="TagBio_SelectCargo",
                    min_values=1, max_values=1,
                )
            )
            if mode == "embed":
                emb = disnake.Embed(title="Configurar Cargo",
                                    description="Selecione o cargo que será dado/removido conforme a tag/bio.")
                if ph: emb.color = color(ph)
                await inter.edit_original_message(content=None, embed=emb,
                                                   components=[select_row, voltar])
            else:
                await inter.edit_original_message(components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                            f"-# Painel > Comunidade > Cargo por Tag/Bio > **Cargo**"
                        ),
                        disnake.ui.Separator(),
                        select_row,
                        **accent(ph),
                    ),
                    voltar,
                ])
            return

        if cid == "TagBio_RemoverCargo":
            config = helpers.carregar_config()
            config["cargo_id"] = None
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

        # ── Logs públicos ─────────────────────────────────────────────────────
        if cid == "TagBio_ConfigLogsPublico":
            await self._render_canal_select(inter, mode, ph,
                                             "TagBio_SelectLogsPublico",
                                             "Logs Públicos",
                                             "Selecione o canal de logs públicos (botão clicado, cargo ganho/perdido).")
            return

        # ── Logs privados ─────────────────────────────────────────────────────
        if cid == "TagBio_ConfigLogsPrivado":
            await self._render_canal_select(inter, mode, ph,
                                             "TagBio_SelectLogsPrivado",
                                             "Logs Privados",
                                             "Selecione o canal de logs privados (todos os eventos detalhados).")
            return

        # ── Editor de mensagem ────────────────────────────────────────────────
        if cid == "TagBio_EditarMensagem":
            await self._render_editor(inter)
            return

        # ── Voltar ao painel ──────────────────────────────────────────────────
        if cid == "TagBio_VoltarPainel":
            await self._render_painel(inter)
            return

        # ── Apagar campos da mensagem ─────────────────────────────────────────
        if cid == "TagBio_Msg_ApagarContent":
            clear_mensagem_field("content")
            await self._render_editor(inter)
            return

        if cid == "TagBio_Msg_ApagarEmbed":
            clear_mensagem_field("embed")
            await self._render_editor(inter)
            return

        if cid == "TagBio_Msg_ApagarImagens":
            clear_mensagem_field("externalImage")
            await self._render_editor(inter)
            return

        if cid == "TagBio_Msg_ApagarContainer":
            clear_mensagem_field("container")
            await self._render_editor(inter)
            return

        # ── Visualizar mensagem ───────────────────────────────────────────────
        if cid == "TagBio_Msg_Visualizar":
            data = get_mensagem_data()
            data_build = data.copy()
            # Adiciona o botão "Receber Cargo" na visualização
            data_build["buttons"] = [{
                "id": "tagbio_receber_preview",
                "label": "Receber Cargo",
                "button": {
                    "type": "disabled",
                    "style": "blue",
                    "disabled": True,
                }
            }]
            built = await self.bot.loop.run_in_executor(
                None, Builder.build_from_cfg, {"message": data_build}
            )
            await self._send_built_message(inter, built, ephemeral=True)
            return

        # ── Publicar mensagem no canal ────────────────────────────────────────
        if cid == "TagBio_Msg_Publicar":
            await self._publicar_mensagem(inter, mode, ph)
            return

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENER — DROPDOWNS
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_dropdown")
    async def _tagbio_dropdown_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("TagBio_"):
            return

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "TagBio_SelectCargo":
            config = helpers.carregar_config()
            config["cargo_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

        if cid == "TagBio_SelectLogsPublico":
            config = helpers.carregar_config()
            config["canal_logs_publico_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

        if cid == "TagBio_SelectLogsPrivado":
            config = helpers.carregar_config()
            config["canal_logs_privado_id"] = inter.values[0] if inter.values else None
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

    # ══════════════════════════════════════════════════════════════════════════
    # LISTENER — MODAIS
    # ══════════════════════════════════════════════════════════════════════════

    @commands.Cog.listener("on_modal_submit")
    async def _tagbio_modal_listener(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("TagBio_"):
            return

        # ── Ajuda container ───────────────────────────────────────────────────
        if cid == "TagBio_MsgModal_Container":
            if inter.text_values.get("container_content", "").strip() == "/ajuda":
                await inter.response.send_message(
                    components=AnunciarHelper.helper("example"),
                    ephemeral=True,
                    flags=disnake.MessageFlags(is_components_v2=True),
                )
                return

        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        if cid == "TagBio_DefinirTag":
            config = helpers.carregar_config()
            config["tag_texto"] = inter.text_values.get("tag_texto", "").strip()
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

        if cid == "TagBio_DefinirBio":
            config = helpers.carregar_config()
            config["bio_texto"] = inter.text_values.get("bio_texto", "").strip()
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

        if cid == "TagBio_DefinirCooldown":
            try:
                val = int(inter.text_values.get("cooldown", "60").strip())
                if val < 1:
                    raise ValueError
            except ValueError:
                await inter.followup.send(f"{emoji.wrong} Valor inválido. Use um número inteiro maior que 0.", ephemeral=True)
                return
            config = helpers.carregar_config()
            config["cooldown_minutos"] = val
            helpers.salvar_config(config)
            await self._render_painel(inter)
            return

        # ── Modais de mensagem ────────────────────────────────────────────────
        if cid == "TagBio_MsgModal_Mensagem":
            data = get_mensagem_data()
            data["content"] = inter.text_values.get("content", "").strip()
            data.pop("container", None)
            set_mensagem_data(data)
            await self._render_editor(inter)
            return

        if cid == "TagBio_MsgModal_Embed":
            def _hex(v):
                if not v:
                    return None
                v = v.strip().lstrip("#")
                if len(v) not in (3, 6):
                    return None
                try:
                    int(v, 16)
                    return f"#{v.upper()}"
                except ValueError:
                    return None

            data = get_mensagem_data()
            data["embed"] = {
                "title":       inter.text_values.get("embed_title"),
                "description": inter.text_values.get("embed_description"),
                "color":       _hex(inter.text_values.get("embed_color")),
                "footer":      inter.text_values.get("embed_footer"),
            }
            data.pop("container", None)
            set_mensagem_data(data)
            await self._render_editor(inter)
            return

        if cid == "TagBio_MsgModal_Imagens":
            data = get_mensagem_data()
            data["externalImage"] = inter.text_values.get("externalImage") or None
            if "banner" in inter.text_values:
                data.setdefault("embed", {})["banner"] = inter.text_values.get("banner") or None
            if "thumbnail" in inter.text_values:
                data.setdefault("embed", {})["thumbnail"] = inter.text_values.get("thumbnail") or None
            set_mensagem_data(data)
            await self._render_editor(inter)
            return

        if cid == "TagBio_MsgModal_Container":
            data = get_mensagem_data()
            data["container"] = inter.text_values.get("container_content", "").strip()
            data.pop("content", None)
            data.pop("embed", None)
            set_mensagem_data(data)
            await self._render_editor(inter)
            return

    # ══════════════════════════════════════════════════════════════════════════
    # HANDLER: Botão público "Receber Cargo"
    # ══════════════════════════════════════════════════════════════════════════

    async def _handle_receber_cargo(self, inter: disnake.MessageInteraction):
        """Verifica tag/bio do usuário e concede ou não o cargo."""
        await inter.response.defer(ephemeral=True)

        config    = helpers.carregar_config()
        cargo_id  = config.get("cargo_id")
        tag_ativo = config.get("tag_ativo", False)
        bio_ativo = config.get("bio_ativo", False)
        tag_texto = config.get("tag_texto")
        bio_texto = config.get("bio_texto")

        if not config.get("ativado", False):
            await inter.followup.send(f"{emoji.wrong} Este sistema está desativado no momento.", ephemeral=True)
            return

        if not cargo_id:
            await inter.followup.send(f"{emoji.wrong} Nenhum cargo configurado.", ephemeral=True)
            return

        member: disnake.Member = inter.author
        role   = inter.guild.get_role(int(cargo_id))
        if not role:
            await inter.followup.send(f"{emoji.wrong} O cargo configurado não foi encontrado no servidor.", ephemeral=True)
            return

        # Log privado: clicou no botão
        await helpers.enviar_log_privado(
            self.bot,
            "Botão clicado",
            f"{member.mention} (`{member.id}`) clicou em **Receber Cargo**.",
        )

        # ── Verificação de tag ────────────────────────────────────────────────
        tag_ok = True
        if tag_ativo and tag_texto:
            display = member.display_name or ""
            name    = member.name or ""
            tag_ok  = (tag_texto.lower() in display.lower() or
                       tag_texto.lower() in name.lower())

        # ── Verificação de bio ────────────────────────────────────────────────
        bio_ok = True
        if bio_ativo and bio_texto:
            bio_ok = await self._verificar_bio(inter, member, bio_texto)

        # ── Resultado ─────────────────────────────────────────────────────────
        if tag_ativo and not tag_ok:
            # Log privado
            await helpers.enviar_log_privado(
                self.bot,
                "Tag não encontrada",
                f"{member.mention} não possui a tag `{tag_texto}` no nome.",
                erro=True,
            )
            await inter.followup.send(
                f"{emoji.wrong} Seu nome/tag não contém **{tag_texto}**.\nAdicione e tente novamente.",
                ephemeral=True,
            )
            return

        if bio_ativo and not bio_ok:
            # Log privado
            await helpers.enviar_log_privado(
                self.bot,
                "Bio não encontrada",
                f"{member.mention} não possui o texto `{bio_texto}` na bio.",
                erro=True,
            )
            await inter.followup.send(
                f"{emoji.wrong} Sua bio não contém o texto exigido.\nAdicione e tente novamente.",
                ephemeral=True,
            )
            return

        # ── Conceder/confirmar cargo ───────────────────────────────────────────
        if role in member.roles:
            await inter.followup.send(
                f"{emoji.correct} Você já possui o cargo {role.mention}!",
                ephemeral=True,
            )
            return

        try:
            await member.add_roles(role, reason="TagBio: verificação aprovada")
        except disnake.Forbidden:
            await inter.followup.send(f"{emoji.wrong} Sem permissão para adicionar o cargo.", ephemeral=True)
            return

        # Logs
        await helpers.enviar_log_privado(
            self.bot,
            "Cargo concedido",
            f"{member.mention} recebeu o cargo {role.mention} após verificação aprovada.",
        )
        await helpers.enviar_log_publico(
            self.bot,
            f"{emoji.correct} Cargo concedido a {member.display_name}",
            f"{member.mention} clicou no botão e recebeu o cargo {role.mention}.",
        )
        await inter.followup.send(
            f"{emoji.correct} Tudo certo! Você recebeu o cargo {role.mention}.",
            ephemeral=True,
        )

    async def _verificar_bio(
        self,
        inter: disnake.MessageInteraction,
        member: disnake.Member,
        bio_texto: str,
    ) -> bool:
        """Busca a bio do usuário via token de usuário cadastrado na database."""
        import aiohttp

        # Tenta token do próprio usuário primeiro, depois qualquer token disponível
        token = helpers.get_user_token(member.id) or helpers.get_any_token()
        if not token:
            await helpers.enviar_log_privado(
                self.bot,
                "Token ausente",
                f"Não foi possível verificar bio de {member.mention}: nenhum token disponível.",
                erro=True,
            )
            return False

        headers = {"Authorization": token}
        url = f"https://discord.com/api/v10/users/{member.id}/profile?with_mutual_guilds=false"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        return False
                    data = await resp.json()
                    bio = (data.get("user_profile") or {}).get("bio") or ""
                    return bio_texto.lower() in bio.lower()
        except Exception:
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    async def _render_canal_select(
        self,
        inter: disnake.MessageInteraction,
        mode: str,
        ph: str | None,
        select_cid: str,
        titulo: str,
        descricao: str,
    ):
        """Renderiza tela de seleção de canal (todos os canais de texto do servidor)."""
        text_channels = [
            ch for ch in inter.guild.channels
            if isinstance(ch, disnake.TextChannel)
        ]
        # Discord limita select a 25 opções — pegar os 25 primeiros
        options = [
            disnake.SelectOption(label=f"#{ch.name}", value=str(ch.id),
                                 description=str(ch.id))
            for ch in text_channels[:25]
        ]
        if not options:
            options = [disnake.SelectOption(label="Nenhum canal encontrado", value="__none__")]

        select_row = disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder="Selecione um canal...",
                custom_id=select_cid,
                options=options,
                min_values=1, max_values=1,
            )
        )
        voltar = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey,
                              custom_id="TagBio_VoltarPainel"),
        )

        if mode == "embed":
            emb = disnake.Embed(title=f"Configurar {titulo}", description=descricao)
            if ph:
                emb.color = color(ph)
            await inter.edit_original_message(content=None, embed=emb,
                                               components=[select_row, voltar])
        else:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Painel > Comunidade > Cargo por Tag/Bio > **{titulo}**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(descricao),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    select_row,
                    **accent(ph),
                ),
                voltar,
            ])

    async def _publicar_mensagem(
        self,
        inter: disnake.MessageInteraction,
        mode: str,
        ph: str | None,
    ):
        """Publica a mensagem configurada em um canal selecionado."""
        text_channels = [
            ch for ch in inter.guild.channels
            if isinstance(ch, disnake.TextChannel)
        ]
        options = [
            disnake.SelectOption(label=f"#{ch.name}", value=str(ch.id))
            for ch in text_channels[:25]
        ]
        if not options:
            await inter.followup.send(f"{emoji.wrong} Nenhum canal de texto encontrado.", ephemeral=True)
            return

        select_row = disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                placeholder="Escolha o canal para publicar...",
                custom_id="TagBio_SelectPublicar",
                options=options,
            )
        )
        voltar = disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", emoji=emoji.back,
                              style=disnake.ButtonStyle.grey,
                              custom_id="TagBio_Msg_VoltarEditor"),
        )

        if mode == "embed":
            emb = disnake.Embed(title="Publicar Mensagem",
                                description="Selecione o canal onde a mensagem com o botão **Receber Cargo** será enviada.")
            if ph:
                emb.color = color(ph)
            await inter.edit_original_message(content=None, embed=emb,
                                               components=[select_row, voltar])
        else:
            await inter.edit_original_message(components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Painel > Comunidade > Cargo por Tag/Bio > **Publicar Mensagem**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay("Selecione o canal onde a mensagem com o botão **Receber Cargo** será enviada."),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    select_row,
                    **accent(ph),
                ),
                voltar,
            ])

    @commands.Cog.listener("on_dropdown")
    async def _tagbio_publicar_listener(self, inter: disnake.MessageInteraction):
        """Listener separado para o select de publicação e voltar do editor."""
        cid = inter.component.custom_id

        if cid == "TagBio_SelectPublicar":
            mode = _mode()
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)

            canal_id = inter.values[0]
            canal    = inter.guild.get_channel(int(canal_id))
            if not canal:
                await inter.followup.send(f"{emoji.wrong} Canal não encontrado.", ephemeral=True)
                return

            data      = get_mensagem_data()
            data_build = data.copy()
            # Botão "Receber Cargo" fixo
            data_build["buttons"] = [{
                "id":    "tagbio_receber",
                "label": "Receber Cargo",
                "button": {
                    "type":  "action",
                    "style": "blue",
                    "action": {"type": "custom", "custom_id": "TagBio_ReceberCargo"},
                }
            }]

            built = await self.bot.loop.run_in_executor(
                None, Builder.build_from_cfg, {"message": data_build}
            )

            # Sobrescreve components com o botão real
            btn_row = disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Receber Cargo",
                    style=disnake.ButtonStyle.blurple,
                    custom_id="TagBio_ReceberCargo",
                    emoji=emoji.role,
                )
            )

            try:
                kwargs: dict = {"allowed_mentions": disnake.AllowedMentions.none()}
                if built.get("mode") == "v2":
                    comps = built.get("components", [])
                    comps.append(btn_row)
                    kwargs["components"] = comps
                    kwargs["flags"]      = built.get("flags")
                    await canal.send(**kwargs)
                else:
                    if built.get("content"):
                        kwargs["content"] = built["content"]
                    if built.get("embed"):
                        kwargs["embed"] = built["embed"]
                    kwargs["components"] = [btn_row]
                    await canal.send(**kwargs)
            except Exception as e:
                await inter.followup.send(f"{emoji.wrong} Erro ao publicar: {e}", ephemeral=True)
                return

            await inter.followup.send(f"{emoji.correct} Mensagem publicada em {canal.mention}!", ephemeral=True)
            await self._render_editor(inter)
            return

        if cid == "TagBio_Msg_VoltarEditor":
            # é botão, não dropdown — ignorar
            pass

    @commands.Cog.listener("on_button_click")
    async def _tagbio_voltar_editor(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "TagBio_Msg_VoltarEditor":
            return
        mode = _mode()
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        await self._render_editor(inter)

    @staticmethod
    async def _send_built_message(target, built: dict, ephemeral: bool = False):
        from functions.utils import utils
        kwargs = {"allowed_mentions": disnake.AllowedMentions.none()}
        if ephemeral:
            kwargs["ephemeral"] = True

        if built.get("mode") == "v2":
            kwargs["components"] = built.get("components")
            kwargs["flags"]      = built.get("flags")
        else:
            if built.get("content"):
                kwargs["content"] = built["content"]
            if built.get("embed"):
                emb_data = built["embed"]
                if isinstance(emb_data, disnake.Embed):
                    kwargs["embed"] = emb_data
                else:
                    kwargs["embed"] = disnake.Embed.from_dict(
                        utils.normalize_embed_data(emb_data)
                    )
            if built.get("components"):
                kwargs["components"] = built["components"]
            if built.get("files"):
                kwargs["files"] = built["files"]

        if isinstance(target, disnake.Interaction):
            await target.followup.send(**kwargs)
        elif isinstance(target, disnake.TextChannel):
            await target.send(**kwargs)


def setup(bot: commands.Bot):
    bot.add_cog(TagBioCog(bot))