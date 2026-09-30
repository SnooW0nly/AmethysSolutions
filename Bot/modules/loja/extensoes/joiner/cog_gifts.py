"""
cog_gifts.py — Gerenciamento de Gifts do sistema Joiner

Fluxo:
1. Admin cria um gift com N boosts via painel → armazenado na JS API (por tenant)
2. Cliente resgata via botão Discord → bot envia run_boost ao JS → JS executa
3. JS realiza: verificar servidor, adicionar membros, aplicar boost slots
4. Bot recebe resultado e atualiza a UI
"""
from __future__ import annotations

import asyncio
import logging
import io
import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message

from .helpers import (
    load_config,
    count_members,
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
#  Builders de painel (async — dados vêm da JS API via WS)
# ──────────────────────────────────────────────────────────

async def build_gifts_panel() -> dict:
    ws = _ws()
    gifts = []
    if ws and ws.is_connected():
        resp = await ws.get_gifts()
        if resp.get("success"):
            gifts = resp.get("data", {}).get("gifts", [])

    total = len(gifts)
    pending = len([g for g in gifts if not g.get("redeemed")])
    redeemed = len([g for g in gifts if g.get("redeemed")])
    member_count = count_members()

    preview_lines = []
    for g in gifts[:8]:
        icon = "✅" if g.get("redeemed") else "⏳"
        note = f" · `{g['note'][:20]}`" if g.get("note") else ""
        res = g.get("redeemed_data") or {}
        res_str = f" | boosts: `{res.get('boostsApplied', res.get('boosts_applied', 0))}`" if g.get("redeemed") else ""
        gid = str(g.get("id", "?"))
        preview_lines.append(
            f"{icon} `{gid[:8]}{'…' if len(gid) > 8 else ''}` — **{g.get('boost_count', '?')}** boosts{note}{res_str}"
        )

    preview = "\n".join(preview_lines) if preview_lines else "-# Nenhum gift criado ainda."
    if total > 8:
        preview += f"\n-# ... e mais {total - 8} gifts"

    body = (
        f"{emoji.members} **Membros com token:** `{member_count}`\n"
        f"{emoji.gift} **Total:** `{total}` · Pendentes: `{pending}` · Resgatados: `{redeemed}`\n\n"
        f"**Gifts recentes:**\n{preview}"
    )

    rows = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Criar Gift", emoji=emoji.plus, style=disnake.ButtonStyle.green,
                              custom_id="JoinerGift_Criar"),
            disnake.ui.Button(label="Exportar Gifts", emoji=emoji.folder, style=disnake.ButtonStyle.grey,
                              custom_id="JoinerGift_Exportar"),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Deletar Gift", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                              custom_id="JoinerGift_Deletar"),
        ),
    ]

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                                       f"-# Painel > Impulso Automático > **Gifts**"),
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


def build_public_redeem_message() -> dict:
    colors = db.get_document("custom_colors") or {}
    primary_hex = colors.get("primary")

    body = (
        "🎁 **Resgate seu Gift aqui!**\n\n"
        "-# Para resgatar, clique no botão abaixo e informe:\n"
        "-# • **Gift ID** — código fornecido pelo administrador\n"
        "-# • **Server ID** — ID do servidor onde os boosts serão aplicados\n\n"
        "-# ⚠️ Certifique-se de que o bot já foi adicionado ao servidor alvo antes de resgatar."
    )

    action_row = disnake.ui.ActionRow(
        disnake.ui.Button(
            label="Resgatar Gift",
            style=disnake.ButtonStyle.green,
            emoji="🎁",
            custom_id="JoinerGift_ResgatarPublico",
        )
    )

    kw = {}
    if primary_hex:
        kw["accent_colour"] = disnake.Colour(int(primary_hex.replace("#", ""), 16))

    return {
        "components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(body),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                action_row,
                **kw,
            )
        ],
        "flags": disnake.MessageFlags(is_components_v2=True),
    }


# ──────────────────────────────────────────────────────────
#  Log helper
# ──────────────────────────────────────────────────────────

async def _send_gift_log(bot, gift_id: str, guild_id: str, result: dict):
    """Envia log de gift resgatado no canal configurado."""
    cfg = load_config()
    log_channel_id = cfg.get("log_channel_id", "")
    if not log_channel_id:
        return
    try:
        ch = bot.get_channel(int(log_channel_id))
        if not ch:
            return
        colors = db.get_document("custom_colors") or {}
        primary_hex = colors.get("primary")
        kw = {}
        if primary_hex:
            kw["accent_colour"] = disnake.Colour(int(primary_hex.replace("#", ""), 16))
        text = (
            f"🎁 **Gift `{gift_id}` resgatado**\n"
            f"-# Servidor: `{guild_id}` · "
            f"Membros adicionados: `{result.get('members_added', 0)}` · "
            f"Boosts: `{result.get('boosts_applied', 0)}` · "
            f"Falhas: `{result.get('members_failed', 0)}`"
        )
        await ch.send(
            components=[disnake.ui.Container(disnake.ui.TextDisplay(text), **kw)],
            flags=disnake.MessageFlags(is_components_v2=True),
        )
    except Exception as e:
        logger.warning(f"[GiftsCog] Erro ao enviar log: {e}")


# ──────────────────────────────────────────────────────────
#  Modais
# ──────────────────────────────────────────────────────────

class ModalCriarGift(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Criar Gift",
            custom_id="JoinerGift_CriarModal",
            components=[
                disnake.ui.TextInput(
                    label="Quantidade de boosts (deve ser par)",
                    custom_id="boost_count",
                    placeholder="Ex: 14 (cada conta fornece 2 boosts)",
                    required=True,
                    max_length=6,
                ),
                disnake.ui.TextInput(
                    label="Nota (opcional)",
                    custom_id="note",
                    placeholder="Ex: Gift VIP Maio/25",
                    required=False,
                    max_length=100,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            boost_count = int(inter.text_values.get("boost_count", "0").strip())
            if boost_count <= 0 or boost_count % 2 != 0:
                raise ValueError
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Quantidade inválida. Use um número **par** maior que zero (ex: 2, 4, 6...).",
                ephemeral=True)
            return

        ws = _ws()
        if not (ws and ws.is_connected()):
            await inter.response.send_message(
                f"{emoji.wrong} WebSocket offline. Aguarde a reconexão e tente novamente.", ephemeral=True)
            return

        note = inter.text_values.get("note", "").strip()

        import uuid, hashlib
        gift_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8].upper()

        gift_data = {
            "id": gift_id,
            "boost_count": boost_count,
            "note": note,
            "created_by": {"id": str(inter.user.id), "name": inter.user.display_name},
        }

        resp = await ws.create_gift(gift_data)
        if not resp.get("success"):
            await inter.response.send_message(
                f"{emoji.wrong} Falha ao criar gift: {resp.get('message')}", ephemeral=True)
            return

        panel = await build_gifts_panel()
        flags = panel.pop("flags", None)
        await inter.response.edit_message(**panel, flags=flags)

        import math
        accounts_needed = math.ceil(boost_count / 2)
        await inter.followup.send(
            f"{emoji.correct} **Gift criado!**\n"
            f"**ID:** `{gift_id}` · **Boosts:** `{boost_count}` · **Contas necessárias:** `{accounts_needed}`"
            + (f" · `{note}`" if note else ""),
            ephemeral=True,
        )


class ModalResgatarGiftPublico(disnake.ui.Modal):
    """Modal do PAINEL PÚBLICO — cliente informa gift_id + guild_id."""
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            title="Resgatar Gift",
            custom_id="JoinerGift_ResgatarModal",
            components=[
                disnake.ui.TextInput(
                    label="ID do Gift",
                    custom_id="gift_id",
                    placeholder="Ex: A1B2C3D4",
                    required=True,
                    max_length=20,
                ),
                disnake.ui.TextInput(
                    label="ID do Servidor",
                    custom_id="guild_id",
                    placeholder="ID do servidor onde os boosts serão aplicados",
                    required=True,
                    max_length=25,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        gift_id = inter.text_values.get("gift_id", "").strip().upper()
        guild_id = inter.text_values.get("guild_id", "").strip()

        if not guild_id.isdigit():
            await inter.followup.send(f"{emoji.wrong} ID de servidor inválido.", ephemeral=True)
            return

        ws = _ws()
        if not (ws and ws.is_connected()):
            await inter.followup.send(
                f"{emoji.wrong} Sistema offline no momento. Tente novamente em instantes.", ephemeral=True)
            return

        await inter.followup.send(
            f"{emoji.loading} Processando gift `{gift_id}` → servidor `{guild_id}`...\n"
            f"-# Isso pode levar alguns segundos.",
            ephemeral=True,
        )

        result = await ws.run_boost(gift_id=gift_id, guild_id=guild_id)

        if result.get("success"):
            await inter.edit_original_message(
                content=(
                    f"{emoji.correct} **Gift resgatado com sucesso!**\n\n"
                    f"**Servidor:** `{guild_id}`\n"
                    f"**Membros adicionados:** `{result.get('members_added', 0)}`\n"
                    f"**Boosts aplicados:** `{result.get('boosts_applied', 0)}`\n"
                    f"**Falhas:** `{result.get('members_failed', 0)}`"
                )
            )
            asyncio.create_task(
                _send_gift_log(self.bot, gift_id, guild_id, result)
            )
        else:
            await inter.edit_original_message(
                content=f"{emoji.wrong} **Falha ao resgatar gift:**\n{result.get('message', 'Erro desconhecido')}"
            )


class ModalDeletarGift(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Deletar Gift",
            custom_id="JoinerGift_DeletarModal",
            components=[
                disnake.ui.TextInput(
                    label="ID do Gift",
                    custom_id="gift_id",
                    placeholder="Cole o ID do gift aqui",
                    required=True,
                    max_length=20,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        gift_id = inter.text_values.get("gift_id", "").strip().upper()

        ws = _ws()
        if not (ws and ws.is_connected()):
            await inter.response.send_message(f"{emoji.wrong} Sistema offline.", ephemeral=True)
            return

        ok = await ws.delete_gift(gift_id)

        panel = await build_gifts_panel()
        flags = panel.pop("flags", None)
        await inter.response.edit_message(**panel, flags=flags)

        if ok.get("success"):
            await inter.followup.send(f"{emoji.correct} Gift `{gift_id}` deletado!", ephemeral=True)
        else:
            await inter.followup.send(
                f"{emoji.wrong} {ok.get('message', 'Gift não encontrado.')}", ephemeral=True)


# ──────────────────────────────────────────────────────────
#  Cog
# ──────────────────────────────────────────────────────────

class JoinerGiftsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id or ""

        if cid == "Joiner_PainelGifts":
            panel = await build_gifts_panel()
            flags = panel.pop("flags", None)
            if inter.response.is_done():
                await inter.edit_original_message(**panel, flags=flags)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(**panel, flags=flags)

        elif cid == "JoinerGift_Criar":
            await inter.response.send_modal(ModalCriarGift())

        elif cid == "JoinerGift_ResgatarPublico":
            await inter.response.send_modal(ModalResgatarGiftPublico(self.bot))

        elif cid == "JoinerGift_Deletar":
            await inter.response.send_modal(ModalDeletarGift())

        elif cid == "JoinerGift_Exportar":
            ws = _ws()
            if not (ws and ws.is_connected()):
                await inter.response.send_message(
                    f"{emoji.wrong} Sistema offline.", ephemeral=True)
                return
            resp = await ws.get_gifts()
            gifts = resp.get("data", {}).get("gifts", []) if resp.get("success") else []
            if not gifts:
                await inter.response.send_message(
                    f"{emoji.wrong} Nenhum gift criado.", ephemeral=True)
                return
            import datetime
            lines = []
            for g in gifts:
                status = "RESGATADO" if g.get("redeemed") else "PENDENTE"
                res = g.get("redeemed_data") or {}
                guild = res.get("guild_id") or g.get("target_guild_id") or "-"
                created = g.get("created_at", "")
                try:
                    dt = datetime.datetime.fromisoformat(str(created)).strftime("%d/%m/%Y %H:%M")
                except Exception:
                    dt = str(created)[:10]
                lines.append(
                    f"{g.get('id', '?')} | {status} | {g.get('boost_count', 0)} boosts | "
                    f"Servidor: {guild} | Criado: {dt} | {g.get('note', '')}"
                )
            buf = io.BytesIO("\n".join(lines).encode("utf-8"))
            await inter.response.send_message(
                f"{emoji.correct} **{len(gifts)} gifts exportados:**",
                file=disnake.File(buf, filename=f"joiner_gifts_{len(gifts)}.txt"),
                ephemeral=True,
            )