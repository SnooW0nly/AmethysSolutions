"""
Sistema de Recompensa por Feedback
===================================
- Painel de preferências acessível via Loja > Preferências > Recompensa por Feedback
- Admin configura: ativar/desativar, mensagem do painel público, recompensas (nome + conteúdo + limite de resgates)
- Admin envia o painel público em qualquer canal
- Cliente clica em "Resgatar Recompensa" → bot verifica mensagem no canal de feedback → libera a recompensa na DM
- Suporte a múltiplas recompensas (enviadas na DM como itens distintos)
- Controle de quantas vezes cada usuário pode resgatar
- Funciona nos dois modos: embed e components (v2)
"""

import disnake
import uuid
from disnake.ext import commands
from datetime import datetime
from typing import Optional

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


# ---------------------------------------------------------------------------
# Chave de persistência
# ---------------------------------------------------------------------------
_DOC_KEY = "recompensa_feedback"


# ---------------------------------------------------------------------------
# Helpers de config
# ---------------------------------------------------------------------------

def _get_config() -> dict:
    return db.get_document(_DOC_KEY) or {}


def _save_config(data: dict) -> None:
    db.save_document(_DOC_KEY, data)


def _get_recompensas(cfg: dict) -> dict:
    """Retorna dict {id: {name, content, max_resgates}}"""
    return cfg.get("recompensas") or {}


def _get_resgates(cfg: dict) -> dict:
    """Retorna dict {user_id: {recompensa_id: count}}"""
    return cfg.get("resgates") or {}


# ---------------------------------------------------------------------------
# Painel de Preferências (chamado pelo cog.py de preferências)
# ---------------------------------------------------------------------------

class RecompensaFeedbackPreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ---- status text -------------------------------------------------------

    @staticmethod
    def _build_status_text(cfg: dict) -> str:
        enabled   = cfg.get("enabled", False)
        recomp    = _get_recompensas(cfg)
        canal_id  = cfg.get("feedback_channel_id")
        max_g     = cfg.get("max_resgates_global", 1)

        status_icon = emoji.on if enabled else emoji.off
        canal_str   = f"<#{canal_id}>" if canal_id else "`Não configurado`"
        n_recomp    = len(recomp)

        lines = [
            f"{status_icon} **Status:** `{'Ativado' if enabled else 'Desativado'}`",
            f"-# Canal de feedback: {canal_str}",
            f"-# Recompensas cadastradas: `{n_recomp}`",
            f"-# Limite de resgates por usuário: `{max_g}x`",
        ]
        if not enabled:
            lines.append("-# Configure o canal de feedback e ao menos uma recompensa para ativar.")
        return "\n".join(lines)

    # ---- panel (router) ----------------------------------------------------

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode", "components")
        return (
            RecompensaFeedbackPreferences._panel_embed(inter)
            if mode == "embed"
            else RecompensaFeedbackPreferences._panel_components(inter)
        )

    # ---- components (v2) ---------------------------------------------------

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        cfg     = _get_config()
        enabled = cfg.get("enabled", False)
        recomp  = _get_recompensas(cfg)
        can_enable = bool(cfg.get("feedback_channel_id") and recomp)

        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Painel > Loja > Preferências > **Recompensa por Feedback**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        "Recompense clientes que deixam feedback! "
                        "Configure as recompensas, o canal de feedback e envie o painel público no servidor."
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(RecompensaFeedbackPreferences._build_status_text(cfg)),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Desativar" if enabled else "Ativar",
                            style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
                            emoji=emoji.off if enabled else emoji.on,
                            custom_id="RecompFeedback_Toggle",
                            disabled=not can_enable and not enabled,
                        ),
                        disnake.ui.Button(
                            label="Gerenciar Recompensas",
                            style=disnake.ButtonStyle.blurple,
                            emoji=emoji.edit,
                            custom_id="RecompFeedback_GerenciarRecompensas",
                        ),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Configurar Canal de Feedback",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.settings2,
                            custom_id="RecompFeedback_SetCanal",
                        ),
                        disnake.ui.Button(
                            label="Editar Mensagem do Painel",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.receipt,
                            custom_id="RecompFeedback_EditMensagem",
                        ),
                        disnake.ui.Button(
                            label="Limite de Resgates",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.clock,
                            custom_id="RecompFeedback_SetLimite",
                        ),
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Enviar Painel Público",
                            style=disnake.ButtonStyle.blurple,
                            emoji=emoji.double_speech,
                            custom_id="RecompFeedback_EnviarPainel",
                            disabled=not enabled,
                        ),
                    ),
                    **container_kwargs,
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Loja_Preferencias",
                    )
                ),
            ]
        }

    # ---- embed mode --------------------------------------------------------

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        cfg     = _get_config()
        enabled = cfg.get("enabled", False)
        recomp  = _get_recompensas(cfg)
        can_enable = bool(cfg.get("feedback_channel_id") and recomp)

        embed = disnake.Embed(
            title="Recompensa por Feedback",
            description=(
                "-# Painel > Loja > Preferências > **Recompensa por Feedback**\n\n"
                "Recompense clientes que deixam feedback! Configure as recompensas, "
                "o canal de feedback e envie o painel público no servidor.\n\n"
                + RecompensaFeedbackPreferences._build_status_text(cfg)
            ),
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Desativar" if enabled else "Ativar",
                    style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
                    emoji=emoji.off if enabled else emoji.on,
                    custom_id="RecompFeedback_Toggle",
                    disabled=not can_enable and not enabled,
                ),
                disnake.ui.Button(
                    label="Gerenciar Recompensas",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="RecompFeedback_GerenciarRecompensas",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar Canal de Feedback",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.settings2,
                    custom_id="RecompFeedback_SetCanal",
                ),
                disnake.ui.Button(
                    label="Editar Mensagem do Painel",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.receipt,
                    custom_id="RecompFeedback_EditMensagem",
                ),
                disnake.ui.Button(
                    label="Limite de Resgates",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.clock,
                    custom_id="RecompFeedback_SetLimite",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Enviar Painel Público",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.double_speech,
                    custom_id="RecompFeedback_EnviarPainel",
                    disabled=not enabled,
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Preferencias",
                )
            ),
        ]
        return {"embed": embed, "components": components}

    # =========================================================================
    # Listeners — Preferências
    # =========================================================================

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id

        # ---- Toggle ativação ------------------------------------------------
        if cid == "RecompFeedback_Toggle":
            cfg = _get_config()
            recomp = _get_recompensas(cfg)
            if not cfg.get("enabled", False) and not (cfg.get("feedback_channel_id") and recomp):
                return await inter.response.send_message(
                    f"{emoji.wrong} Configure o canal de feedback e ao menos uma recompensa antes de ativar!",
                    ephemeral=True,
                )
            cfg["enabled"] = not cfg.get("enabled", False)
            _save_config(cfg)
            await self._refresh_pref_panel(inter)

        # ---- Gerenciar recompensas ------------------------------------------
        elif cid == "RecompFeedback_GerenciarRecompensas":
            await inter.response.defer()
            await self._show_gerenciar_recompensas(inter)

        # ---- Configurar canal de feedback -----------------------------------
        elif cid == "RecompFeedback_SetCanal":
            await inter.response.send_modal(SetCanalFeedbackModal())

        # ---- Editar mensagem do painel público ------------------------------
        elif cid == "RecompFeedback_EditMensagem":
            cfg = _get_config()
            current = cfg.get("panel_message", "")
            await inter.response.send_modal(EditMensagemPainelModal(current))

        # ---- Limite de resgates ---------------------------------------------
        elif cid == "RecompFeedback_SetLimite":
            cfg = _get_config()
            current = str(cfg.get("max_resgates_global", 1))
            await inter.response.send_modal(SetLimiteModal(current))

        # ---- Enviar painel público -------------------------------------------
        elif cid == "RecompFeedback_EnviarPainel":
            await inter.response.send_modal(EnviarPainelCanalModal())

        # ---- Botão Adicionar Recompensa (na tela de gerenciar) --------------
        elif cid == "RecompFeedback_AddRecompensa":
            await inter.response.send_modal(AddEditRecompensaModal())

        # ---- Botão Editar Recompensa (prefixo) ------------------------------
        elif cid.startswith("RecompFeedback_Edit:"):
            rid = cid.split(":", 1)[1]
            cfg = _get_config()
            recomp = _get_recompensas(cfg)
            r = recomp.get(rid)
            if not r:
                return await inter.response.send_message(f"{emoji.wrong} Recompensa não encontrada.", ephemeral=True)
            await inter.response.send_modal(AddEditRecompensaModal(rid=rid, existing=r))

        # ---- Botão Remover Recompensa (prefixo) -----------------------------
        elif cid.startswith("RecompFeedback_Del:"):
            rid = cid.split(":", 1)[1]
            cfg = _get_config()
            recomp = _get_recompensas(cfg)
            recomp.pop(rid, None)
            cfg["recompensas"] = recomp
            _save_config(cfg)
            await inter.response.defer()
            await self._show_gerenciar_recompensas(inter)

        # ---- Voltar para gerenciar (de detalhes de recompensa) --------------
        elif cid == "RecompFeedback_VoltarGerenciar":
            await inter.response.defer()
            await self._show_gerenciar_recompensas(inter)

        # ---- PAINEL PÚBLICO — Resgatar Recompensa ---------------------------
        elif cid == "RecompFeedback_Resgatar":
            await self._handle_resgatar(inter)

    # ---- Dropdown: selecionar recompensa para ver detalhes ------------------
    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "RecompFeedback_SelectRecompensa":
            rid = inter.values[0]
            await inter.response.defer()
            await self._show_detalhe_recompensa(inter, rid)

    # =========================================================================
    # Helpers de UI internos
    # =========================================================================

    async def _refresh_pref_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode", "components")
        await inter.response.defer()
        panel = RecompensaFeedbackPreferences.panel(inter)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

    async def _show_gerenciar_recompensas(self, inter: disnake.MessageInteraction):
        """Exibe a tela de listagem/gerenciamento de recompensas."""
        cfg    = _get_config()
        recomp = _get_recompensas(cfg)
        mode   = db.get_document("custom_mode").get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        if not recomp:
            lista_txt = "-# Nenhuma recompensa cadastrada ainda."
        else:
            linhas = []
            for rid, r in recomp.items():
                max_r = r.get("max_resgates", 1)
                linhas.append(f"{emoji.star} **{r['name']}** — limite: `{max_r}x`")
            lista_txt = "\n".join(linhas)

        # Select de recompensas (se houver)
        select_row = None
        if recomp:
            options = [
                disnake.SelectOption(
                    label=r["name"][:50],
                    value=rid,
                    description=f"Limite: {r.get('max_resgates', 1)}x | {r['content'][:40]}...",
                )
                for rid, r in list(recomp.items())[:25]
            ]
            select_row = disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="RecompFeedback_SelectRecompensa",
                    placeholder="Selecione uma recompensa para editar/remover",
                    options=options,
                )
            )

        if mode != "embed":
            children_list = [
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Loja > Preferências > Recompensa por Feedback > **Recompensas**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Gerencie as recompensas disponíveis para os clientes que enviarem feedback."
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(lista_txt),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar Recompensa",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.correct,
                        custom_id="RecompFeedback_AddRecompensa",
                        disabled=len(recomp) >= 25,
                    )
                ),
            ]
            if select_row:
                children_list.append(select_row)

            await inter.edit_original_message(
                components=[
                    disnake.ui.Container(*children_list, **container_kwargs),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Voltar",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.back,
                            custom_id="RecompFeedback_VoltarPref",
                        )
                    ),
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
        else:
            embed = disnake.Embed(
                title="Gerenciar Recompensas",
                description=(
                    "-# Painel > Loja > Preferências > Recompensa por Feedback > **Recompensas**\n\n"
                    "Gerencie as recompensas disponíveis para os clientes que enviarem feedback.\n\n"
                    + lista_txt
                ),
            )
            if primary_color_hex:
                embed.color = int(primary_color_hex.replace("#", ""), 16)

            comp_list = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar Recompensa",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.correct,
                        custom_id="RecompFeedback_AddRecompensa",
                        disabled=len(recomp) >= 25,
                    )
                ),
            ]
            if select_row:
                comp_list.append(select_row)
            comp_list.append(
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="RecompFeedback_VoltarPref",
                    )
                )
            )
            await inter.edit_original_message(content=None, embed=embed, components=comp_list)

    async def _show_detalhe_recompensa(self, inter: disnake.MessageInteraction, rid: str):
        """Exibe detalhes de uma recompensa com opções de editar/remover."""
        cfg    = _get_config()
        recomp = _get_recompensas(cfg)
        r      = recomp.get(rid)
        mode   = db.get_document("custom_mode").get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        if not r:
            return await inter.followup.send(f"{emoji.wrong} Recompensa não encontrada.", ephemeral=True)

        preview_content = r["content"][:200] + ("..." if len(r["content"]) > 200 else "")
        detalhe_txt = (
            f"**Nome:** `{r['name']}`\n"
            f"**Limite de resgates:** `{r.get('max_resgates', 1)}x`\n\n"
            f"**Conteúdo da Recompensa:**\n```\n{preview_content}\n```"
        )

        action_row = disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Editar",
                style=disnake.ButtonStyle.blurple,
                emoji=emoji.edit,
                custom_id=f"RecompFeedback_Edit:{rid}",
            ),
            disnake.ui.Button(
                label="Remover",
                style=disnake.ButtonStyle.red,
                emoji=emoji.delete,
                custom_id=f"RecompFeedback_Del:{rid}",
            ),
        )

        if mode != "embed":
            await inter.edit_original_message(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"# {emoji.star} Detalhes da Recompensa\n"
                            f"-# Painel > Loja > Preferências > Recompensa por Feedback > **{r['name']}**"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(detalhe_txt),
                        disnake.ui.Separator(),
                        action_row,
                        **container_kwargs,
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Voltar",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.back,
                            custom_id="RecompFeedback_VoltarGerenciar",
                        )
                    ),
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
        else:
            embed = disnake.Embed(
                title=f"Recompensa — {r['name']}",
                description=(
                    f"-# Painel > Loja > Preferências > Recompensa por Feedback > **{r['name']}**\n\n"
                    + detalhe_txt
                ),
            )
            if primary_color_hex:
                embed.color = int(primary_color_hex.replace("#", ""), 16)
            await inter.edit_original_message(
                content=None,
                embed=embed,
                components=[
                    action_row,
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Voltar",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.back,
                            custom_id="RecompFeedback_VoltarGerenciar",
                        )
                    ),
                ],
            )

    # ---- Botão "Voltar" do gerenciar para preferências ----------------------
    # Reutiliza listener on_button_click via cid == "RecompFeedback_VoltarPref"

    # =========================================================================
    # Lógica de resgate (painel público)
    # =========================================================================

    async def _handle_resgatar(self, inter: disnake.MessageInteraction):
        """Verifica feedback e entrega recompensa(s) na DM."""
        await inter.response.defer(ephemeral=True)

        cfg     = _get_config()
        if not cfg.get("enabled", False):
            return await inter.followup.send(
                f"{emoji.wrong} O sistema de recompensas está desativado no momento.",
                ephemeral=True,
            )

        recomp       = _get_recompensas(cfg)
        canal_fb_id  = cfg.get("feedback_channel_id")
        max_resgates = cfg.get("max_resgates_global", 1)

        if not recomp:
            return await inter.followup.send(
                f"{emoji.wrong} Nenhuma recompensa configurada no momento.",
                ephemeral=True,
            )

        if not canal_fb_id:
            return await inter.followup.send(
                f"{emoji.wrong} Canal de feedback não configurado. Avise um administrador.",
                ephemeral=True,
            )

        # ---- Verificar limite de resgates globais ---------------------------
        resgates    = _get_resgates(cfg)
        uid         = str(inter.user.id)
        user_resg   = resgates.get(uid, {})
        # Conta total de resgates (soma de todas as recompensas)
        total_resg  = sum(user_resg.values())

        if total_resg >= max_resgates:
            return await inter.followup.send(
                f"{emoji.wrong} Você já atingiu o limite de **{max_resgates}** resgate(s) de recompensa.",
                ephemeral=True,
            )

        # ---- Verificar mensagem no canal de feedback -----------------------
        canal_fb = inter.guild.get_channel(int(canal_fb_id)) if inter.guild else None
        if not canal_fb:
            return await inter.followup.send(
                f"{emoji.wrong} Canal de feedback não encontrado. Avise um administrador.",
                ephemeral=True,
            )

        encontrou_feedback = False
        try:
            async for msg in canal_fb.history(limit=500):
                if msg.author.id == inter.user.id:
                    encontrou_feedback = True
                    break
        except disnake.Forbidden:
            return await inter.followup.send(
                f"{emoji.wrong} Não consigo acessar o canal de feedback. Avise um administrador.",
                ephemeral=True,
            )

        if not encontrou_feedback:
            canal_mention = canal_fb.mention
            return await inter.followup.send(
                f"{emoji.wrong} Não encontrei nenhuma mensagem sua no canal de feedback ({canal_mention}).\n"
                f"-# Deixe seu feedback lá e volte para resgatar sua recompensa!",
                ephemeral=True,
            )

        # ---- Entregar recompensas na DM ------------------------------------
        mode   = db.get_document("custom_mode").get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        color  = None
        if primary_color_hex:
            try:
                color = int(primary_color_hex.replace("#", ""), 16)
            except Exception:
                pass

        try:
            dm = await inter.user.create_dm()

            if mode == "embed":
                embed_header = disnake.Embed(
                    title=f"{emoji.star} Recompensa por Feedback!",
                    description=(
                        f"Olá, {inter.user.mention}! Obrigado pelo seu feedback.\n"
                        f"Aqui estão suas recompensas:\n\n"
                    ),
                    color=color or disnake.Color.gold(),
                    timestamp=datetime.utcnow(),
                )
                await dm.send(embed=embed_header)
                for rid, r in recomp.items():
                    e = disnake.Embed(
                        title=f"{emoji.star} {r['name']}",
                        description=r["content"],
                        color=color or disnake.Color.gold(),
                    )
                    await dm.send(embed=e)
            else:
                container_kwargs = {}
                if color:
                    container_kwargs["accent_colour"] = disnake.Colour(color)

                # Cabeçalho
                await dm.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(
                                f"# {emoji.star} Recompensa por Feedback!\n"
                                f"-# Obrigado pelo feedback, {inter.user.mention}! Aqui estão suas recompensas:"
                            ),
                            **container_kwargs,
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True),
                )
                # Uma mensagem por recompensa (conteúdo pode ser código, link, etc.)
                for rid, r in recomp.items():
                    await dm.send(
                        components=[
                            disnake.ui.Container(
                                disnake.ui.TextDisplay(
                                    f"## {emoji.star} {r['name']}\n"
                                    f"{r['content']}"
                                ),
                                **container_kwargs,
                            )
                        ],
                        flags=disnake.MessageFlags(is_components_v2=True),
                    )

        except disnake.Forbidden:
            return await inter.followup.send(
                f"{emoji.wrong} Não consigo te enviar DM! Habilite as mensagens diretas do servidor e tente novamente.",
                ephemeral=True,
            )
        except Exception as e:
            print(f"[RECOMP FEEDBACK] Erro ao enviar DM: {e}")
            return await inter.followup.send(
                f"{emoji.wrong} Ocorreu um erro ao enviar sua recompensa. Tente novamente.",
                ephemeral=True,
            )

        # ---- Registrar resgate ---------------------------------------------
        resgates_up = _get_resgates(cfg)
        user_resg_up = resgates_up.get(uid, {})
        for rid in recomp:
            user_resg_up[rid] = user_resg_up.get(rid, 0) + 1
        resgates_up[uid] = user_resg_up
        cfg["resgates"] = resgates_up
        _save_config(cfg)

        await inter.followup.send(
            f"{emoji.correct} Recompensa(s) enviadas para sua DM! Verifique suas mensagens diretas.",
            ephemeral=True,
        )

    # ---- listener de voltar do gerenciar para pref panel -------------------
    # já coberto no on_button_click acima via "RecompFeedback_VoltarPref"
    # mas precisamos adicionar o handler explícito abaixo:

    async def _handle_voltar_pref(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode", "components")
        await inter.response.defer()
        panel = RecompensaFeedbackPreferences.panel(inter)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


# Patch no listener para cobrir "RecompFeedback_VoltarPref"
_orig_on_button = RecompensaFeedbackPreferences.on_button_click.__wrapped__ if hasattr(
    RecompensaFeedbackPreferences.on_button_click, "__wrapped__"
) else None


# ---------------------------------------------------------------------------
# Modais
# ---------------------------------------------------------------------------

class SetCanalFeedbackModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.Label(
                text="Canal de Feedback",
                component=disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal onde os clientes enviam feedbacks",
                    custom_id="recomp_fb_canal_select",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                ),
                description="O bot irá verificar se o usuário tem mensagem neste canal.",
            ),
        ]
        super().__init__(title="Canal de Feedback", components=components, custom_id="RecompFeedback_CanalModal")

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            valores  = inter.resolved_values
            selected = valores.get("recomp_fb_canal_select")

            if isinstance(selected, (list, tuple)):
                selected = selected[0] if selected else None
            if isinstance(selected, (str, int)):
                channel_id = int(selected)
            elif hasattr(selected, "id"):
                channel_id = int(selected.id)
            else:
                return await inter.response.send_message(f"{emoji.wrong} Canal inválido!", ephemeral=True)

            channel = inter.guild.get_channel(channel_id)
            if not channel:
                return await inter.response.send_message(f"{emoji.wrong} Canal não encontrado!", ephemeral=True)

            cfg = _get_config()
            cfg["feedback_channel_id"] = channel_id
            _save_config(cfg)

            mode = db.get_document("custom_mode").get("mode", "components")
            await inter.response.defer()
            panel = RecompensaFeedbackPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(f"{emoji.wrong} Erro: {str(e)}", ephemeral=True)


class EditMensagemPainelModal(disnake.ui.Modal):
    def __init__(self, current: str = ""):
        components = [
            disnake.ui.TextInput(
                label="Título do Painel",
                custom_id="titulo",
                value=current.split("\n")[0] if current else "",
                max_length=100,
                required=True,
                placeholder="🎁 Recompensa por Feedback",
            ),
            disnake.ui.TextInput(
                label="Descrição / Instruções",
                custom_id="descricao",
                value="\n".join(current.split("\n")[1:]) if current and "\n" in current else "",
                style=disnake.TextInputStyle.paragraph,
                max_length=1000,
                required=True,
                placeholder="Deixe seu feedback no canal #feedback e clique em Resgatar para receber sua recompensa!",
            ),
        ]
        super().__init__(title="Editar Mensagem do Painel Público", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        titulo    = inter.text_values.get("titulo", "").strip()
        descricao = inter.text_values.get("descricao", "").strip()

        cfg = _get_config()
        cfg["panel_message"] = f"{titulo}\n{descricao}"
        _save_config(cfg)

        mode = db.get_document("custom_mode").get("mode", "components")
        await inter.response.defer()
        panel = RecompensaFeedbackPreferences.panel(inter)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


class SetLimiteModal(disnake.ui.Modal):
    def __init__(self, current: str = "1"):
        components = [
            disnake.ui.TextInput(
                label="Limite de Resgates por Usuário",
                custom_id="limite",
                value=current,
                max_length=3,
                required=True,
                placeholder="1",
            ),
        ]
        super().__init__(title="Limite de Resgates", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        raw = inter.text_values.get("limite", "1").strip()
        try:
            limite = int(raw)
            if limite < 1:
                raise ValueError
        except ValueError:
            return await inter.response.send_message(
                f"{emoji.wrong} Insira um número válido maior que 0.", ephemeral=True
            )

        cfg = _get_config()
        cfg["max_resgates_global"] = limite
        _save_config(cfg)

        mode = db.get_document("custom_mode").get("mode", "components")
        await inter.response.defer()
        panel = RecompensaFeedbackPreferences.panel(inter)
        if mode == "embed":
            await inter.edit_original_message(content=None, **panel)
        else:
            await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


class AddEditRecompensaModal(disnake.ui.Modal):
    def __init__(self, rid: Optional[str] = None, existing: Optional[dict] = None):
        self.rid = rid
        components = [
            disnake.ui.TextInput(
                label="Nome da Recompensa",
                custom_id="nome",
                value=existing.get("name", "") if existing else "",
                max_length=50,
                required=True,
                placeholder="Ex: Cupom 10% OFF",
            ),
            disnake.ui.TextInput(
                label="Conteúdo (código, link, texto...)",
                custom_id="conteudo",
                value=existing.get("content", "") if existing else "",
                style=disnake.TextInputStyle.paragraph,
                max_length=1500,
                required=True,
                placeholder="CUPOM10\nhttps://exemplo.com/resgate",
            ),
            disnake.ui.TextInput(
                label="Limite de resgates desta recompensa",
                custom_id="max_resgates",
                value=str(existing.get("max_resgates", 1)) if existing else "1",
                max_length=3,
                required=True,
                placeholder="1",
            ),
        ]
        title = "Editar Recompensa" if rid else "Adicionar Recompensa"
        super().__init__(title=title, components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        nome      = inter.text_values.get("nome", "").strip()
        conteudo  = inter.text_values.get("conteudo", "").strip()
        max_raw   = inter.text_values.get("max_resgates", "1").strip()

        if not nome or not conteudo:
            return await inter.response.send_message(
                f"{emoji.wrong} Nome e conteúdo são obrigatórios.", ephemeral=True
            )
        try:
            max_r = int(max_raw)
            if max_r < 1:
                raise ValueError
        except ValueError:
            return await inter.response.send_message(
                f"{emoji.wrong} Limite de resgates deve ser um número maior que 0.", ephemeral=True
            )

        cfg    = _get_config()
        recomp = _get_recompensas(cfg)

        rid = self.rid or str(uuid.uuid4())[:8]
        recomp[rid] = {
            "name": nome,
            "content": conteudo,
            "max_resgates": max_r,
        }
        cfg["recompensas"] = recomp
        _save_config(cfg)

        # Voltar para tela de gerenciar
        mode   = db.get_document("custom_mode").get("mode", "components")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        lista_txt = "\n".join(
            f"{emoji.star} **{r['name']}** — limite: `{r.get('max_resgates', 1)}x`"
            for r in recomp.values()
        ) or "-# Nenhuma recompensa cadastrada."

        select_row = None
        if recomp:
            options = [
                disnake.SelectOption(
                    label=r["name"][:50],
                    value=k,
                    description=f"Limite: {r.get('max_resgates', 1)}x",
                )
                for k, r in list(recomp.items())[:25]
            ]
            select_row = disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="RecompFeedback_SelectRecompensa",
                    placeholder="Selecione uma recompensa para editar/remover",
                    options=options,
                )
            )

        if mode != "embed":
            children_list = [
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Loja > Preferências > Recompensa por Feedback > **Recompensas**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(lista_txt),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar Recompensa",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.correct,
                        custom_id="RecompFeedback_AddRecompensa",
                        disabled=len(recomp) >= 25,
                    )
                ),
            ]
            if select_row:
                children_list.append(select_row)

            await inter.response.edit_message(
                components=[
                    disnake.ui.Container(*children_list, **container_kwargs),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Voltar",
                            style=disnake.ButtonStyle.grey,
                            emoji=emoji.back,
                            custom_id="RecompFeedback_VoltarPref",
                        )
                    ),
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
        else:
            embed = disnake.Embed(
                title="Gerenciar Recompensas",
                description=(
                    "-# Painel > Loja > Preferências > Recompensa por Feedback > **Recompensas**\n\n"
                    + lista_txt
                ),
            )
            if primary_color_hex:
                embed.color = int(primary_color_hex.replace("#", ""), 16)
            comp_list = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Adicionar Recompensa",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.correct,
                        custom_id="RecompFeedback_AddRecompensa",
                        disabled=len(recomp) >= 25,
                    )
                ),
            ]
            if select_row:
                comp_list.append(select_row)
            comp_list.append(
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="RecompFeedback_VoltarPref",
                    )
                )
            )
            await inter.response.edit_message(content=None, embed=embed, components=comp_list)


class EnviarPainelCanalModal(disnake.ui.Modal):
    """Admin escolhe o canal onde o painel público será enviado."""

    def __init__(self):
        components = [
            disnake.ui.Label(
                text="Canal para o Painel Público",
                component=disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal para enviar o painel",
                    custom_id="recomp_fb_painel_canal",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                ),
                description="O painel com o botão de Resgatar será enviado neste canal.",
            ),
        ]
        super().__init__(title="Enviar Painel Público", components=components, custom_id="RecompFeedback_EnviarModal")

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            valores  = inter.resolved_values
            selected = valores.get("recomp_fb_painel_canal")

            if isinstance(selected, (list, tuple)):
                selected = selected[0] if selected else None
            if isinstance(selected, (str, int)):
                channel_id = int(selected)
            elif hasattr(selected, "id"):
                channel_id = int(selected.id)
            else:
                return await inter.response.send_message(f"{emoji.wrong} Canal inválido!", ephemeral=True)

            target_channel = inter.guild.get_channel(channel_id)
            if not target_channel:
                return await inter.response.send_message(f"{emoji.wrong} Canal não encontrado!", ephemeral=True)

            cfg    = _get_config()
            recomp = _get_recompensas(cfg)
            canal_fb_id = cfg.get("feedback_channel_id")

            if not recomp:
                return await inter.response.send_message(
                    f"{emoji.wrong} Nenhuma recompensa configurada!", ephemeral=True
                )

            mode   = db.get_document("custom_mode").get("mode", "components")
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")
            color  = None
            if primary_color_hex:
                try:
                    color = int(primary_color_hex.replace("#", ""), 16)
                except Exception:
                    pass

            # Montar texto do painel
            panel_msg = cfg.get("panel_message", "")
            if panel_msg and "\n" in panel_msg:
                parts    = panel_msg.split("\n", 1)
                titulo   = parts[0]
                descricao = parts[1]
            elif panel_msg:
                titulo   = panel_msg
                descricao = ""
            else:
                titulo   = f"{emoji.star} Recompensa por Feedback!"
                canal_fb_mention = f"<#{canal_fb_id}>" if canal_fb_id else "o canal de feedback"
                descricao = (
                    f"Deixou seu feedback em {canal_fb_mention}? "
                    f"Clique no botão abaixo para resgatar sua recompensa direto na DM!"
                )

            recompensas_lista = "\n".join(
                f"{emoji.chevron_arrow} **{r['name']}**"
                for r in recomp.values()
            )

            max_resgates = cfg.get("max_resgates_global", 1)

            resgatar_btn = disnake.ui.Button(
                label="Resgatar Recompensa",
                style=disnake.ButtonStyle.green,
                emoji=emoji.star,
                custom_id="RecompFeedback_Resgatar",
            )

            if mode == "embed":
                embed = disnake.Embed(
                    title=titulo,
                    description=descricao,
                    color=color or disnake.Color.gold(),
                )
                embed.add_field(
                    name="Recompensas disponíveis:",
                    value=recompensas_lista,
                    inline=False,
                )
                embed.set_footer(text=f"Limite: {max_resgates} resgate(s) por usuário")
                await target_channel.send(
                    embed=embed,
                    components=[disnake.ui.ActionRow(resgatar_btn)],
                )
            else:
                container_kwargs = {}
                if color:
                    container_kwargs["accent_colour"] = disnake.Colour(color)

                conteudo_txt = (
                    f"# {titulo}\n"
                    f"{descricao}\n\n"
                    f"**Recompensas disponíveis:**\n{recompensas_lista}\n\n"
                    f"-# Limite: {max_resgates} resgate(s) por usuário"
                )
                await target_channel.send(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(conteudo_txt),
                            disnake.ui.Separator(),
                            disnake.ui.ActionRow(resgatar_btn),
                            **container_kwargs,
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True),
                )

            await inter.response.send_message(
                f"{emoji.correct} Painel enviado em {target_channel.mention}!",
                ephemeral=True,
            )

        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(f"{emoji.wrong} Erro: {str(e)}", ephemeral=True)
            import traceback
            traceback.print_exc()


# ---------------------------------------------------------------------------
# Listener de "Voltar" do gerenciar → pref panel (não coberto pelo on_button_click
# porque o cog não reconhece "RecompFeedback_VoltarPref" sem o if abaixo)
# ---------------------------------------------------------------------------

# Injetado diretamente via monkey-patch no listener existente:
_ORIG_LISTENER = RecompensaFeedbackPreferences.on_button_click


async def _patched_listener(self, inter: disnake.MessageInteraction):
    if inter.component.custom_id == "RecompFeedback_VoltarPref":
        await self._handle_voltar_pref(inter)
    else:
        await _ORIG_LISTENER(self, inter)


RecompensaFeedbackPreferences.on_button_click = commands.Cog.listener("on_button_click")(
    _patched_listener
)


# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

def setup(bot: commands.Bot):
    bot.add_cog(RecompensaFeedbackPreferences(bot))
