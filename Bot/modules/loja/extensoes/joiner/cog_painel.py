"""
cog_painel.py — Painel principal da extensão "Entrar em Servidor" (Mass Join OAuth2)
"""
from __future__ import annotations

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

from .helpers import (
    load_config, save_config,
    count_members,
    get_gift_stats,
    count_account_tokens, list_account_tokens,
    add_account_token, delete_account_token,
    try_link_pending_oauth,
    get_api_base_url,
)


def _get_mode() -> str:
    return db.get_document("custom_mode").get("mode")


def _embed_color() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"color": int(hex_.replace("#", ""), 16)}
    return {}


def _accent() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


# ──────────────────────────────────────────────────────────
#  Builders de painel (embed e components_v2)
# ──────────────────────────────────────────────────────────

def build_main_panel(mode: str) -> dict:
    cfg = load_config()
    enabled = cfg.get("enabled", False)
    client_id = cfg.get("oauth_client_id", "")
    tok_stats = count_account_tokens()
    member_count = count_members()

    status_icon = emoji.on if enabled else emoji.off
    configured = bool(client_id)
    log_ch = cfg.get("log_channel_id", "")

    body = (
        f"{status_icon} **Status:** `{'Ativo' if enabled else 'Inativo'}`  ·  "
        f"{emoji.robot} **OAuth2:** {f'{emoji.correct}' if configured else f'{emoji.wrong}'}\n"
        f"{emoji.group} **Tokens:** `{tok_stats['linked']}` vinc. · `{tok_stats['pending']}` pend.\n"
        f"{emoji.textc} **Logs:** {'<#' + log_ch + '>' if log_ch else '`Não configurado`'}\n\n"
        f"{emoji.member} **Membros com token:** `{member_count}`"
    )

    row1 = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Desativar" if enabled else "Ativar",
            style=disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green,
            emoji=emoji.off if enabled else emoji.on,
            custom_id="Joiner_ToggleAtivo",
        ),
        disnake.ui.Button(label="Credenciais OAuth2", emoji=emoji.robot, style=disnake.ButtonStyle.blurple,
                          custom_id="Joiner_PainelCredenciais"),
    )
    row2 = disnake.ui.ActionRow(
        disnake.ui.Button(label="Tokens de Conta", emoji=emoji.group, style=disnake.ButtonStyle.grey,
                          custom_id="Joiner_PainelTokens"),
        disnake.ui.Button(label="Criar Gift", emoji=emoji.gift, style=disnake.ButtonStyle.green,
                          custom_id="JoinerGift_Criar"),
        disnake.ui.Button(label="Config. Painel Público", emoji=emoji.embed,
                          style=disnake.ButtonStyle.grey, custom_id="Joiner_PainelPublico"),
    )
    row3 = disnake.ui.ActionRow(
        disnake.ui.Button(label="Verificação OAuth2", emoji=emoji.textc, style=disnake.ButtonStyle.grey,
                          custom_id="Joiner_ConfigOAuthChannel"),
        disnake.ui.Button(label="Canal de Logs", emoji=emoji.double_speech, style=disnake.ButtonStyle.grey,
                          custom_id="Joiner_ConfigLogsChannel"),
    )
    row_boost = disnake.ui.ActionRow(
        disnake.ui.Button(
            label=f"Boost  —  {tok_stats['linked']} conta{'s' if tok_stats['linked'] != 1 else ''} vinculada{'s' if tok_stats['linked'] != 1 else ''}",
            style=disnake.ButtonStyle.blurple if tok_stats["linked"] > 0 else disnake.ButtonStyle.grey,
            custom_id="Boost_PainelPrincipal",
        ),
    )
    back_row = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                          custom_id="LojaExtensoes_Panel")
    )

    if mode == "embed":
        embed = disnake.Embed(
            description=(
                f"-# Painel > Loja > Extensões > **Impulso Automático**\n\n"
                f"{body}"
            ),
            **_embed_color(),
        )
        return {
            "embed": embed,
            "components": [row1, row2, row3, row_boost, back_row],
        }

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                                       f"-# Painel > Loja > Extensões > **Impulso Automático**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                row1, row2, row3, row_boost,
                **_accent(),
            ),
            back_row,
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_credentials_panel() -> dict:
    cfg = load_config()
    client_id = cfg.get("oauth_client_id", "")
    has_secret = bool(cfg.get("oauth_client_secret", ""))
    has_bot_token = bool(cfg.get("oauth_bot_token", ""))
    callback_path = cfg.get("callback_path", "/joiner/callback")

    from modules.cloud.cloud_config import get_cloud_url
    cloud_url = get_cloud_url()
    callback_url = f"{cloud_url}{callback_path}"

    body = (
        f"**Como configurar:**\n"
        f"1. Acesse o [Portal de Desenvolvedores do Discord](https://discord.com/developers/applications)\n"
        f"2. Selecione (ou crie) sua aplicação OAuth2\n"
        f"3. Em **OAuth2 → Redirects**, adicione:\n"
        f"```\n{callback_url}\n```\n"
        f"4. Copie o **Client ID**, **Client Secret** e o **Bot Token**\n"
        f"5. Use o botão **Definir Credenciais** abaixo\n\n"
        f"─────────────────────\n"
        f"{emoji.robot} **Client ID:** {client_id or f'{emoji.wrong}'}\n"
        f"{emoji.double_check} **Client Secret:** {f'{emoji.correct}' if has_secret else f'{emoji.wrong}'}\n"
        f"{emoji.robot} **Bot Token:** {f'{emoji.correct}' if has_bot_token else f'{emoji.wrong}'}"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Definir Credenciais", emoji=emoji.robot, style=disnake.ButtonStyle.green,
                              custom_id="Joiner_ModalCredenciais"),
            disnake.ui.Button(label="Copiar URL de Callback", emoji=emoji.web, style=disnake.ButtonStyle.grey,
                              custom_id="Joiner_CopiarCallback"),
        ),
    ]

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                                       f"-# Painel > Impulso Automático > **Credenciais OAuth2**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id="Joiner_PainelPrincipal")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_tokens_panel() -> dict:
    tok_stats = count_account_tokens()
    tokens = list_account_tokens()

    from .helpers import _load_oauth_cache
    cache_count = len(_load_oauth_cache().get("cache", {}))

    preview_lines = []
    for t in tokens[:10]:
        status_icon = {"linked": f"{emoji.correct}", "pending": f"{emoji.clock}", "cache": f"{emoji.reload}"}.get(t.get("status", "pending"), f"{emoji.clock}")
        label = t.get("label") or t["token_id"]
        linked_id = t.get("linked_oauth_user_id")
        link_str = f" → <@{linked_id}>" if linked_id else ""
        tok_masked = t["token"].replace(t["token"][10:-4], "…") if len(t.get("token", "")) > 14 else "***"
        preview_lines.append(f"{status_icon} `{label}` · `{tok_masked}`{link_str}")

    preview = "\n".join(preview_lines) if preview_lines else "-# Nenhum token adicionado ainda."
    if len(tokens) > 10:
        preview += f"\n-# ... e mais {len(tokens) - 10} tokens"

    body = (
        f"{emoji.group} **Tokens:** `{tok_stats['total']}` total · `{tok_stats['linked']}` vinculados · `{tok_stats['pending']}` pendentes\n"
        f"{emoji.clock} **OAuth2 em cache:** `{cache_count}` aguardando token\n\n"
        f"**Como funciona:**\n"
        f"-# Adicione tokens de conta abaixo. Quando uma conta autorizar via OAuth2, o token será vinculado automaticamente.\n"
        f"-# Se OAuth2 chegar antes do token → fica em cache até você adicionar um token.\n\n"
        f"**Tokens adicionados:**\n{preview}"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar Token", emoji=emoji.plus, style=disnake.ButtonStyle.green,
                              custom_id="Joiner_AdicionarToken"),
            disnake.ui.Button(label="Remover Token", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                              custom_id="Joiner_RemoverToken"),
        ),
    ]

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.group} Tokens de Conta\n"
                                       f"-# Painel > Impulso Automático > **Tokens de Conta**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id="Joiner_PainelPrincipal")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


def build_public_panel_config() -> dict:
    cfg = load_config()
    panel = cfg.get("panel", {})
    ch_id = panel.get("channel_id", "")
    msg_id = panel.get("message_id", "")

    body = (
        f"**Configuração do Painel Público:**\n\n"
        f"{emoji.textc} **Canal:** {'<#' + ch_id + '>' if ch_id else '`Não definido`'}\n"
        f"{emoji.message} **Mensagem postada:** `{'ID: ' + str(msg_id) if msg_id else 'Não postada'}`\n"
        f"{emoji.edit} **Título:** `{panel.get('title', 'Entrar no Servidor')}`\n"
        f"{emoji.member} **Botão:** `{panel.get('button_label', 'Entrar')}`\n"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Editar Conteúdo", emoji=emoji.edit, style=disnake.ButtonStyle.blurple,
                              custom_id="Joiner_ModalPainelPublico"),
            disnake.ui.Button(label="Postar Mensagem", emoji=emoji.arrow, style=disnake.ButtonStyle.green,
                              custom_id="Joiner_PostarPainel"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.ChannelSelect(
                placeholder="Canal do painel público",
                custom_id="Joiner_SelecaoCanal",
                channel_types=[disnake.ChannelType.text],
                min_values=1, max_values=1,
            )
        ),
    ]

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                                       f"-# Painel > Impulso Automático > **Painel Público**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id="Joiner_PainelPrincipal")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


# ──────────────────────────────────────────────────────────
#  Modais de tokens de conta
# ──────────────────────────────────────────────────────────

class ModalAdicionarToken(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Adicionar Token de Conta",
            custom_id="Joiner_AdicionarTokenForm",
            components=[
                disnake.ui.TextInput(
                    label="Token da Conta",
                    custom_id="token_value",
                    placeholder="Cole o token da conta aqui",
                    required=True,
                    max_length=200,
                ),
                disnake.ui.TextInput(
                    label="Label (opcional)",
                    custom_id="token_label",
                    placeholder="Ex: Conta Principal, Alt 1...",
                    required=False,
                    max_length=50,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        token_value = inter.text_values.get("token_value", "").strip()
        label = inter.text_values.get("token_label", "").strip()

        if not token_value:
            await inter.response.send_message(f"{emoji.wrong} Token inválido.", ephemeral=True)
            return

        token_id = add_account_token(token_value, label=label, added_by_id=inter.user.id)
        linked_user_id = try_link_pending_oauth(token_id)

        panel = build_tokens_panel()
        flags = panel.pop("flags", None)
        await inter.response.edit_message(**panel, flags=flags)

        if linked_user_id:
            await inter.followup.send(
                f"{emoji.correct} Token adicionado e **vinculado automaticamente** ao usuário `{linked_user_id}` que estava em cache!",
                ephemeral=True,
            )
        else:
            await inter.followup.send(
                f"{emoji.correct} Token adicionado com sucesso!\n"
                f"-# ID: `{token_id}` · Aguardando vinculação via OAuth2.",
                ephemeral=True,
            )


class ModalRemoverToken(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Remover Token de Conta",
            custom_id="Joiner_RemoverTokenForm",
            components=[
                disnake.ui.TextInput(
                    label="ID ou Label do Token",
                    custom_id="token_id",
                    placeholder="Cole o token_id ou label do token",
                    required=True,
                    max_length=100,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        val = inter.text_values.get("token_id", "").strip()

        tokens = list_account_tokens()
        target = next((t for t in tokens if t["token_id"] == val), None)
        if not target:
            target = next((t for t in tokens if t.get("label", "").lower() == val.lower()), None)

        if not target:
            await inter.response.send_message(f"{emoji.wrong} Token `{val}` não encontrado.", ephemeral=True)
            return

        ok = delete_account_token(target["token_id"])
        panel = build_tokens_panel()
        flags = panel.pop("flags", None)
        await inter.response.edit_message(**panel, flags=flags)
        result = f"{emoji.correct} Token removido!" if ok else f"{emoji.wrong} Falha ao remover."
        await inter.followup.send(result, ephemeral=True)


# ──────────────────────────────────────────────────────────
#  Modais de configuração
# ──────────────────────────────────────────────────────────

class ModalCredenciais(disnake.ui.Modal):
    def __init__(self):
        cfg = load_config()
        super().__init__(
            title="Credenciais OAuth2",
            custom_id="Joiner_ModalCredenciaisForm",
            components=[
                disnake.ui.TextInput(label="Bot Token", custom_id="bot_token",
                                     value=cfg.get("oauth_bot_token", ""), required=True, max_length=100,
                                     placeholder="Token do bot da aplicação OAuth2"),
                disnake.ui.TextInput(label="Client ID", custom_id="client_id",
                                     value=cfg.get("oauth_client_id", ""), required=True, max_length=30),
                disnake.ui.TextInput(label="Client Secret", custom_id="client_secret",
                                     value=cfg.get("oauth_client_secret", ""), required=True, max_length=100,
                                     placeholder="Mantido em segurança no servidor"),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        cfg = load_config()
        cfg["oauth_bot_token"] = inter.text_values.get("bot_token", "").strip()
        cfg["oauth_client_id"] = inter.text_values.get("client_id", "").strip()
        cfg["oauth_client_secret"] = inter.text_values.get("client_secret", "").strip()
        save_config(cfg)

        # Atualizar credenciais no WS (para o JS usar no boost sem precisar reconectar)
        try:
            from .websocket_manager import get_websocket_manager
            ws = get_websocket_manager()
            if ws and ws.is_connected():
                await ws.emit("register_oauth_credentials", {
                    "api_key": ws.api_key,
                    "oauth_client_id": cfg["oauth_client_id"],
                    "oauth_client_secret": cfg["oauth_client_secret"],
                    "oauth_bot_token": cfg["oauth_bot_token"],
                    "callback_path": cfg.get("callback_path", "/joiner/callback"),
                })
        except Exception:
            pass

        panel = build_credentials_panel()
        flags = panel.pop("flags", None)
        await inter.response.edit_message(**panel, flags=flags)


class ModalPainelPublico(disnake.ui.Modal):
    def __init__(self):
        cfg = load_config()
        panel = cfg.get("panel", {})
        super().__init__(
            title="Conteúdo do Painel Público",
            custom_id="Joiner_ModalPainelPublicoForm",
            components=[
                disnake.ui.TextInput(label="Título", custom_id="title",
                                     value=panel.get("title", "Entrar no Servidor"), required=True, max_length=256),
                disnake.ui.TextInput(label="Descrição", custom_id="description",
                                     value=panel.get("description", ""), required=False, max_length=2000,
                                     style=disnake.TextInputStyle.paragraph),
                disnake.ui.TextInput(label="Label do botão", custom_id="button_label",
                                     value=panel.get("button_label", "Entrar"), required=True, max_length=40),
                disnake.ui.TextInput(label="Emoji do botão", custom_id="button_emoji",
                                     value=panel.get("button_emoji", "🚀"), required=False, max_length=50),
                disnake.ui.TextInput(label="Estilo (green, blurple, grey, red)", custom_id="button_style",
                                     value=panel.get("button_style", "green"), required=True, max_length=10),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        cfg = load_config()
        cfg.setdefault("panel", {})
        cfg["panel"]["title"] = inter.text_values.get("title", "")
        cfg["panel"]["description"] = inter.text_values.get("description", "")
        cfg["panel"]["button_label"] = inter.text_values.get("button_label", "Resgatar Gift")
        cfg["panel"]["button_emoji"] = inter.text_values.get("button_emoji", "🚀")
        cfg["panel"]["button_style"] = inter.text_values.get("button_style", "green").lower()
        save_config(cfg)

        panel = build_public_panel_config()
        flags = panel.pop("flags", None)
        await inter.response.edit_message(**panel, flags=flags)


class ModalOAuthChannel(disnake.ui.Modal):
    def __init__(self):
        cfg = load_config()
        super().__init__(
            title="Canal de Verificação OAuth2",
            custom_id="Joiner_OAuthChannelForm",
            components=[
                disnake.ui.TextInput(
                    label="ID do Canal",
                    custom_id="channel_id",
                    value=cfg.get("oauth_panel_channel_id", ""),
                    placeholder="Cole o ID do canal aqui",
                    required=True,
                    max_length=25,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        channel_id = inter.text_values.get("channel_id", "").strip()
        cfg = load_config()
        cfg["oauth_panel_channel_id"] = channel_id
        save_config(cfg)

        ch = inter.guild.get_channel(int(channel_id)) if channel_id.isdigit() else None
        if not ch:
            await inter.response.send_message(f"{emoji.wrong} Canal não encontrado.", ephemeral=True)
            return

        colors = db.get_document("custom_colors") or {}
        primary_hex = colors.get("primary")
        kw = {}
        if primary_hex:
            kw["accent_colour"] = disnake.Colour(int(primary_hex.replace("#", ""), 16))

        container = disnake.ui.Container(
            disnake.ui.TextDisplay(
                "## 🔑 Verificação de Conta\n"
                "Clique no botão abaixo para **autorizar** sua conta e entrar nos servidores disponíveis.\n"
                "-# Permissão concedida: `guilds.join` (entrar em servidores em seu nome)."
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Verificar / Autorizar", style=disnake.ButtonStyle.green,
                                  emoji=emoji.correct, custom_id="Joiner_PublicEntrar")
            ),
            **kw,
        )
        await ch.send(components=[container], flags=disnake.MessageFlags(is_components_v2=True))
        await inter.response.send_message(
            f"{emoji.correct} Painel de verificação OAuth2 enviado em {ch.mention}!", ephemeral=True)


class ModalLogsChannel(disnake.ui.Modal):
    def __init__(self):
        cfg = load_config()
        super().__init__(
            title="Canal de Logs",
            custom_id="Joiner_LogsChannelForm",
            components=[
                disnake.ui.TextInput(
                    label="ID do Canal de Logs",
                    custom_id="channel_id",
                    value=cfg.get("log_channel_id", ""),
                    placeholder="Cole o ID do canal aqui",
                    required=False,
                    max_length=25,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        cfg = load_config()
        cfg["log_channel_id"] = inter.text_values.get("channel_id", "").strip()
        save_config(cfg)
        panel = build_main_panel(_get_mode())
        flags = panel.pop("flags", None)
        if "embed" in panel:
            await inter.response.edit_message(content=None, **panel)
        else:
            await inter.response.edit_message(**panel, flags=flags)
        await inter.followup.send(f"{emoji.correct} Canal de logs atualizado!", ephemeral=True)


# ──────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────

class JoinerPainelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _mode(self) -> str:
        return _get_mode()

    async def _reply(self, inter, panel: dict):
        if "embed" in panel:
            wait_fn = embed_message
        else:
            wait_fn = message
        if inter.response.is_done():
            if "embed" in panel:
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
                await inter.edit_original_message(**panel, flags=flags)
        else:
            await wait_fn.wait(inter, send=False)
            if "embed" in panel:
                await inter.edit_original_message(content=None, **panel)
            else:
                flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
                await inter.edit_original_message(**panel, flags=flags)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        if cid == "Joiner_PainelPrincipal":
            await self._reply(inter, build_main_panel(self._mode()))

        elif cid == "Joiner_ToggleAtivo":
            await (embed_message if self._mode() == "embed" else message).wait(inter, send=False)
            cfg = load_config()
            cfg["enabled"] = not cfg.get("enabled", False)
            save_config(cfg)
            await self._reply(inter, build_main_panel(self._mode()))

        elif cid == "Joiner_PainelCredenciais":
            await self._reply(inter, build_credentials_panel())

        elif cid == "Joiner_PainelGifts":
            from .cog_gifts import build_gifts_panel
            await self._reply(inter, await build_gifts_panel())

        elif cid == "Joiner_ModalCredenciais":
            await inter.response.send_modal(ModalCredenciais())

        elif cid == "Joiner_CopiarCallback":
            cfg = load_config()
            api_url = get_api_base_url()
            callback = f"{api_url}{cfg.get('callback_path', '/joiner/callback')}"
            await inter.response.send_message(f"**URL de Callback OAuth2:**\n```\n{callback}\n```", ephemeral=True)

        elif cid == "Joiner_PainelTokens":
            await self._reply(inter, build_tokens_panel())

        elif cid == "Joiner_AdicionarToken":
            await inter.response.send_modal(ModalAdicionarToken())

        elif cid == "Joiner_RemoverToken":
            await inter.response.send_modal(ModalRemoverToken())

        elif cid == "Joiner_ConfigOAuthChannel":
            await inter.response.send_modal(ModalOAuthChannel())

        elif cid == "Joiner_ConfigLogsChannel":
            await inter.response.send_modal(ModalLogsChannel())

        elif cid == "Joiner_PainelPublico":
            await self._reply(inter, build_public_panel_config())

        elif cid == "Joiner_ModalPainelPublico":
            await inter.response.send_modal(ModalPainelPublico())

        elif cid == "Joiner_PostarPainel":
            cfg = load_config()
            ch_id = cfg.get("panel", {}).get("channel_id", "")
            if not ch_id:
                await inter.response.send_message(
                    f"{emoji.wrong} Selecione um canal primeiro usando o menu abaixo.", ephemeral=True)
                return
            await self._post_public_panel(inter, int(ch_id))

    async def _post_public_panel(self, inter: disnake.MessageInteraction, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await inter.response.send_message(f"{emoji.wrong} Canal não encontrado.", ephemeral=True)
            return

        cfg = load_config()
        panel_cfg = cfg.get("panel", {})
        colors = db.get_document("custom_colors") or {}
        primary_hex = colors.get("primary")

        style_map = {
            "green": disnake.ButtonStyle.green,
            "blurple": disnake.ButtonStyle.blurple,
            "grey": disnake.ButtonStyle.grey,
            "red": disnake.ButtonStyle.red,
        }
        btn_style = style_map.get(panel_cfg.get("button_style", "green"), disnake.ButtonStyle.green)
        btn_emoji_raw = panel_cfg.get("button_emoji", "🚀")
        btn_label = panel_cfg.get("button_label", "Resgatar Gift")

        try:
            btn_emoji = disnake.PartialEmoji.from_str(btn_emoji_raw) if btn_emoji_raw.startswith("<") else btn_emoji_raw
        except Exception:
            btn_emoji = None

        action_row = disnake.ui.ActionRow(
            disnake.ui.Button(label=btn_label, style=btn_style, emoji=btn_emoji,
                              custom_id="JoinerGift_ResgatarPublico")
        )

        title = panel_cfg.get("title", "Entrar no Servidor")
        desc = panel_cfg.get("description", "Clique no botão abaixo para entrar!")

        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)

        kw = {}
        if primary_hex:
            kw["accent_colour"] = disnake.Colour(int(primary_hex.replace("#", ""), 16))
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"## {title}\n{desc}"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            action_row,
            **kw,
        )
        msg = await channel.send(components=[container], flags=disnake.MessageFlags(is_components_v2=True))

        cfg["panel"]["message_id"] = str(msg.id)
        save_config(cfg)

        await inter.followup.send(
            f"{emoji.correct} Painel postado em {channel.mention}!\n"
            f"-# ID da mensagem: `{msg.id}`",
            ephemeral=True,
        )

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        if cid == "Joiner_SelecaoCanal":
            await message.wait(inter, send=False)
            cfg = load_config()
            if inter.values:
                cfg.setdefault("panel", {})["channel_id"] = str(int(inter.values[0]))
            save_config(cfg)
            panel = build_public_panel_config()
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)