"""
cog_boost.py — Painel de Boost integrado ao módulo Joiner
Gerencia estoque de tokens de conta e gifts de boost via WebSocket.

Fluxo:
  1. Admin adiciona tokens de conta (contas que vão dar boost)
  2. Usuário autoriza via OAuth2 pelo Joiner → token vinculado automaticamente
  3. Admin cria gift de boost com N boosts
  4. Gift é enviado via WebSocket para o servidor JS API
  5. JS API executa o boost no servidor alvo (add member + apply slots)
"""
from __future__ import annotations

import io
import logging
import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message

from .helpers import (
    load_config,
    count_account_tokens, list_account_tokens,
    add_account_token, delete_account_token,
    get_linked_tokens_for_boost,
    _load_oauth_cache,
)

logger = logging.getLogger(__name__)


def _accent() -> dict:
    colors = db.get_document("custom_colors") or {}
    hex_ = colors.get("primary")
    if hex_:
        return {"accent_colour": disnake.Colour(int(hex_.replace("#", ""), 16))}
    return {}


def _ws():
    try:
        from .websocket_manager import get_websocket_manager
        return get_websocket_manager()
    except Exception:
        return None


# ──────────────────────────────────────────────────────────
#  Builders de painel (apenas components_v2)
# ──────────────────────────────────────────────────────────

def build_boost_main_panel() -> dict:
    tok_stats = count_account_tokens()
    tokens = list_account_tokens()
    linked_tokens = get_linked_tokens_for_boost()
    cache_count = len(_load_oauth_cache().get("cache", {}))

    ws = _ws()
    ws_status = f"{emoji.correct}" if (ws and ws.is_connected()) else f"{emoji.wrong}"

    preview_lines = []
    for t in tokens[:6]:
        status_icon = {"linked": f"{emoji.correct}", "pending": f"{emoji.clock}", "cache": f"{emoji.reload}"}.get(t.get("status", "pending"), f"{emoji.clock}")
        label = t.get("label") or t["token_id"][:8]
        linked_id = t.get("linked_oauth_user_id")
        link_str = f" → <@{linked_id}>" if linked_id else ""
        tok_masked = (t["token"][:8] + "…" + t["token"][-4:]) if len(t.get("token", "")) > 14 else "***"
        preview_lines.append(f"{status_icon} `{label}` · `{tok_masked}`{link_str}")

    preview = "\n".join(preview_lines) if preview_lines else "-# Nenhum token adicionado ainda."
    if len(tokens) > 6:
        preview += f"\n-# ... e mais {len(tokens) - 6} tokens"

    body = (
        f"{emoji.web} **WebSocket:** {ws_status}\n"
        f"{emoji.group} **Tokens de conta:** `{tok_stats['total']}` total · "
        f"`{tok_stats['linked']}` vinculados · `{tok_stats['pending']}` pendentes\n"
        f"{emoji.members} **Contas prontas para boost:** `{len(linked_tokens)}`\n"
        f"{emoji.clock} **OAuth2 em cache:** `{cache_count}` aguardando token\n\n"
        f"**Como funciona:**\n"
        f"-# 1. Adicione tokens de conta abaixo\n"
        f"-# 2. O Joiner coleta OAuth2 dos usuários e vincula automaticamente\n"
        f"-# 3. Crie gifts de boost — o JS API executa o boost completo\n\n"
        f"**Tokens:**\n{preview}"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Adicionar Token", emoji=emoji.plus, style=disnake.ButtonStyle.green,
                              custom_id="Boost_AdicionarToken"),
            disnake.ui.Button(label="Remover Token", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                              custom_id="Boost_RemoverToken"),
            disnake.ui.Button(label="Exportar Tokens", emoji=emoji.folder, style=disnake.ButtonStyle.grey,
                              custom_id="Boost_ExportarTokens"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label=f"Gifts de Boost ({len(linked_tokens)} contas)",
                emoji=emoji.gift,
                style=disnake.ButtonStyle.blurple if linked_tokens else disnake.ButtonStyle.grey,
                custom_id="Boost_PainelGifts",
            ),
        ),
    ]

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.boost} Boost\n"
                    f"-# Painel > Impulso Automático > **Boost**"
                ),
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


def build_boost_gifts_panel() -> dict:
    ws = _ws()
    ws_connected = ws and ws.is_connected()
    linked_tokens = get_linked_tokens_for_boost()
    linked_count = len(linked_tokens)
    boosts_available = linked_count * 2

    ws_status = f"{emoji.correct}" if ws_connected else f"{emoji.wrong}"
    avail_str = (
        f"`{linked_count}` contas · `{boosts_available}` boosts disponíveis"
        if linked_count > 0
        else "`0` — adicione tokens e aguarde vinculação OAuth2"
    )

    body = (
        f"{emoji.web} **WebSocket:** {ws_status}\n"
        f"{emoji.members} **Contas prontas:** {avail_str}\n\n"
        f"**Como criar um gift:**\n"
        f"-# 1. Clique em **Criar Gift** e informe a quantidade de boosts (deve ser par)\n"
        f"-# 2. O sistema verifica se há contas suficientes\n"
        f"-# 3. Um link de gift é gerado para compartilhar\n"
        f"-# 4. Ao resgatar, o JS API executa: adiciona membros + aplica boosts\n"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Criar Gift",
                emoji=emoji.plus,
                style=disnake.ButtonStyle.green if ws_connected else disnake.ButtonStyle.grey,
                custom_id="Boost_CriarGift",
                disabled=not ws_connected,
            ),
            disnake.ui.Button(label="Ver Gifts", emoji=emoji.receipt, style=disnake.ButtonStyle.blurple,
                              custom_id="Boost_VerGifts",
                              disabled=not ws_connected),
            disnake.ui.Button(label="Limpar Todos", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                              custom_id="Boost_LimparGifts",
                              disabled=not ws_connected),
        ),
    ]

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.gift} Gifts de Boost\n"
                    f"-# Painel > Impulso Automático > Boost > **Gifts**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                                  custom_id="Boost_PainelPrincipal")
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


async def build_boost_view_gifts_panel() -> dict | None:
    ws = _ws()
    if not (ws and ws.is_connected()):
        return None

    response = await ws.get_gifts()
    if not response.get("success"):
        return None

    gifts = response.get("data", {}).get("gifts", [])
    total = len(gifts)
    active = len([g for g in gifts if not g.get("redeemed")])
    redeemed = len([g for g in gifts if g.get("redeemed")])

    lines = []
    for g in gifts[:8]:
        status_icon = f"{emoji.correct}" if not g.get("redeemed") else "🔒"
        redeemed_str = " *(resgatado)*" if g.get("redeemed") else ""
        gid = str(g.get("id", "?"))
        lines.append(
            f"{status_icon} `{gid[:8]}{'…' if len(gid) > 8 else ''}` — "
            f"`{g.get('boost_count', 0)}` boosts{redeemed_str}"
        )
    if total > 8:
        lines.append(f"-# ... e mais {total - 8} gifts")

    body = (
        f"{emoji.gift} **Total:** `{total}` · Ativos: `{active}` · Resgatados: `{redeemed}`\n\n"
        + ("\n".join(lines) if lines else "-# Nenhum gift criado ainda.")
    )

    rows = [disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", emoji=emoji.back, style=disnake.ButtonStyle.grey,
                          custom_id="Boost_PainelGifts")
    )]

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.receipt} Lista de Gifts\n"
                    f"-# Painel > Boost > **Ver Gifts**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                *rows,
                **_accent(),
            ),
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


# ──────────────────────────────────────────────────────────
#  Modais
# ──────────────────────────────────────────────────────────

class ModalAdicionarTokenBoost(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Adicionar Token de Conta",
            custom_id="Boost_AdicionarTokenForm",
            components=[
                disnake.ui.TextInput(
                    label="Token da Conta",
                    custom_id="token_value",
                    placeholder="Cole o token da conta aqui",
                    required=True,
                    max_length=200,
                    style=disnake.TextInputStyle.paragraph,
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

        from .helpers import try_link_pending_oauth
        token_id = add_account_token(token_value, label=label, added_by_id=inter.user.id)
        linked_user_id = try_link_pending_oauth(token_id)

        panel = build_boost_main_panel()
        flags = panel.pop("flags", None)
        await inter.response.edit_message(**panel, flags=flags)

        if linked_user_id:
            await inter.followup.send(
                f"{emoji.correct} Token adicionado e **vinculado automaticamente** ao usuário `{linked_user_id}` (estava em cache OAuth2)!",
                ephemeral=True,
            )
        else:
            await inter.followup.send(
                f"{emoji.correct} Token adicionado!\n"
                f"-# ID: `{token_id}` · Aguardando usuário autorizar via OAuth2.",
                ephemeral=True,
            )


class ModalRemoverTokenBoost(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Remover Token de Conta",
            custom_id="Boost_RemoverTokenForm",
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
        panel = build_boost_main_panel()
        flags = panel.pop("flags", None)
        await inter.response.edit_message(**panel, flags=flags)
        result = f"{emoji.correct} Token removido!" if ok else f"{emoji.wrong} Falha ao remover."
        await inter.followup.send(result, ephemeral=True)


class ModalCriarGiftBoost(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Gift de Boost",
            custom_id="Boost_CriarGiftForm",
            components=[
                disnake.ui.TextInput(
                    label="Quantidade de boosts (deve ser par)",
                    custom_id="boost_count",
                    placeholder="Ex: 2, 4, 6, 8... (cada conta = 2 boosts)",
                    required=True,
                    max_length=6,
                ),
                disnake.ui.TextInput(
                    label="Quantidade de gifts (padrão: 1)",
                    custom_id="quantity",
                    placeholder="Quantos links de gift criar",
                    required=False,
                    max_length=3,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            boost_count = int(inter.text_values.get("boost_count", "0").strip())
        except ValueError:
            await inter.response.send_message(f"{emoji.wrong} Informe um número válido de boosts.", ephemeral=True)
            return

        if boost_count <= 0 or boost_count % 2 != 0:
            await inter.response.send_message(
                f"{emoji.wrong} A quantidade de boosts deve ser um número **par** e maior que zero.\n"
                f"-# Ex: 2, 4, 6, 8, 10… (cada conta fornece 2 boosts)",
                ephemeral=True,
            )
            return

        try:
            quantity = max(1, int(inter.text_values.get("quantity", "1").strip() or "1"))
        except ValueError:
            quantity = 1

        linked = get_linked_tokens_for_boost()
        accounts_needed = (boost_count // 2) * quantity
        if len(linked) < accounts_needed:
            await inter.response.send_message(
                f"{emoji.wrong} **Contas insuficientes!**\n"
                f"Necessário: `{accounts_needed}` · Disponível: `{len(linked)}`\n"
                f"-# Adicione mais tokens de conta e aguarde a vinculação OAuth2.",
                ephemeral=True,
            )
            return

        await inter.response.defer(ephemeral=True)

        ws = _ws()
        if not (ws and ws.is_connected()):
            await inter.edit_original_response(
                content=f"{emoji.wrong} WebSocket desconectado. Aguarde a reconexão e tente novamente."
            )
            return

        import uuid, hashlib
        from datetime import datetime as _dt

        gift_urls = []
        gift_ids = []
        for _ in range(quantity):
            unique = f"{uuid.uuid4()}_{_dt.utcnow().timestamp()}"
            gift_id = hashlib.md5(unique.encode()).hexdigest()[:12]
            gift_data = {
                "id": gift_id,
                "boost_count": boost_count,
                "created_by": {"id": str(inter.user.id), "name": inter.user.display_name},
            }
            resp = await ws.create_gift(gift_data)
            if not resp.get("success"):
                await inter.edit_original_response(
                    content=f"{emoji.wrong} Falha ao criar gift #{len(gift_ids)+1}: {resp.get('message')}"
                )
                return
            gift_url = f"https://boost.syncapplications.com.br/gifts/{gift_id}"
            gift_urls.append(gift_url)
            gift_ids.append(gift_id)

        if quantity == 1:
            await inter.edit_original_response(
                content=(
                    f"{emoji.correct} **Gift criado!**\n\n"
                    f"**ID:** `{gift_ids[0]}`\n"
                    f"**Boosts:** `{boost_count}`\n"
                    f"**Contas usadas:** `{boost_count // 2}`\n"
                    f"**Link:** {gift_urls[0]}"
                )
            )
        else:
            lines = [f"{i+1}. {url}" for i, url in enumerate(gift_urls)]
            buf = io.BytesIO("\n".join(lines).encode())
            await inter.edit_original_response(
                content=(
                    f"{emoji.correct} **{quantity} gifts criados!**\n"
                    f"**Boosts por gift:** `{boost_count}` · **Total boosts:** `{boost_count * quantity}`"
                ),
                file=disnake.File(buf, filename=f"boost_gifts_{quantity}.txt"),
            )


# ──────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────

class JoinerBoostCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _reply(self, inter: disnake.MessageInteraction, panel: dict):
        flags = panel.pop("flags", disnake.MessageFlags(is_components_v2=True))
        if inter.response.is_done():
            await inter.edit_original_message(**panel, flags=flags)
        else:
            await message.wait(inter, send=False)
            await inter.edit_original_message(**panel, flags=flags)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""
        if not cid.startswith("Boost_"):
            return

        if cid == "Boost_PainelPrincipal":
            await self._reply(inter, build_boost_main_panel())

        elif cid == "Boost_PainelGifts":
            await self._reply(inter, build_boost_gifts_panel())

        elif cid == "Boost_AdicionarToken":
            await inter.response.send_modal(ModalAdicionarTokenBoost())

        elif cid == "Boost_RemoverToken":
            await inter.response.send_modal(ModalRemoverTokenBoost())

        elif cid == "Boost_ExportarTokens":
            tokens = list_account_tokens()
            if not tokens:
                await inter.response.send_message(f"{emoji.wrong} Nenhum token cadastrado.", ephemeral=True)
                return
            lines = []
            for t in tokens:
                status = t.get("status", "pending").upper()
                label = t.get("label") or "-"
                lines.append(f"{t['token_id']} | {status} | {label} | {t['token']}")
            buf = io.BytesIO("\n".join(lines).encode())
            await inter.response.send_message(
                f"{emoji.correct} **{len(tokens)} tokens exportados:**",
                file=disnake.File(buf, filename=f"boost_tokens_{len(tokens)}.txt"),
                ephemeral=True,
            )

        elif cid == "Boost_CriarGift":
            ws = _ws()
            if not (ws and ws.is_connected()):
                await inter.response.send_message(
                    f"{emoji.wrong} WebSocket desconectado. Aguarde a reconexão.", ephemeral=True)
                return
            await inter.response.send_modal(ModalCriarGiftBoost())

        elif cid == "Boost_VerGifts":
            await message.wait(inter, send=False)
            panel = await build_boost_view_gifts_panel()
            if panel is None:
                await inter.followup.send(
                    f"{emoji.wrong} WebSocket desconectado ou erro ao buscar gifts.", ephemeral=True)
                return
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)

        elif cid == "Boost_LimparGifts":
            ws = _ws()
            if not (ws and ws.is_connected()):
                await inter.response.send_message(
                    f"{emoji.wrong} WebSocket desconectado.", ephemeral=True)
                return
            await message.wait(inter, send=False)
            resp = await ws.delete_all_gifts()
            deleted = resp.get("data", {}).get("deleted_count", 0) if resp.get("success") else 0
            panel = build_boost_gifts_panel()
            flags = panel.pop("flags", None)
            await inter.edit_original_message(**panel, flags=flags)
            await inter.followup.send(
                f"{emoji.correct} `{deleted}` gifts removidos." if resp.get("success")
                else f"{emoji.wrong} Erro: {resp.get('message')}",
                ephemeral=True,
            )