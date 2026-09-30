"""
Redeemer: processa o resgate de gifts nos 3 modos (painel, canal, /gift).

Lógica de entrega:
  - Gift com `reserved_item` → entrega o item guardado (estoque normal).
  - Gift com `dummy=True`    → código válido mas não entrega nada.
  - Gift de estoque infinito e `dummy=False` → lê o valor do infinite_stock e entrega.
"""
import time

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji


# ─── Modal ───────────────────────────────────────────────────────────────────

class ResgateGiftModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Resgatar Gift",
            custom_id="GiftRedeem_Modal",
            components=[disnake.ui.TextInput(
                label="Código do Gift",
                custom_id="codigo",
                style=disnake.TextInputStyle.short,
                placeholder="Ex: XXXX-XXXX-XXXX-XXXX",
                required=True, max_length=30,
            )],
        )


# ─── Lógica central de resgate ────────────────────────────────────────────────

async def _processar_resgate(user: disnake.User, code: str, bot: commands.Bot, respond) -> None:
    """
    `respond(ephemeral, **kwargs)` — coroutine para enviar a resposta ao usuário.
    """
    code  = code.strip().upper()
    gifts = db.get_document("gifts_data") or {}
    gift  = gifts.get(code)

    primary  = (db.get_document("custom_colors") or {}).get("primary")
    app_mode = db.get_document("custom_mode").get("mode")

    def _ekw():
        return {"color": int(primary.replace("#", ""), 16)} if primary else {}

    def _ckw():
        return {"accent_colour": disnake.Colour(int(primary.replace("#", ""), 16))} if primary else {}

    async def _err(msg: str):
        if app_mode == "embed":
            await respond(True, embed=disnake.Embed(description=f"{emoji.wrong} {msg}", **_ekw()))
        else:
            await respond(True,
                components=[disnake.ui.Container(disnake.ui.TextDisplay(f"{emoji.wrong} {msg}"), **_ckw())],
                flags=disnake.MessageFlags(is_components_v2=True),
            )

    # ── Validações ────────────────────────────────────────────────────────────
    if not gift:
        return await _err("Código inválido ou não encontrado.")
    if gift.get("redeemed"):
        return await _err("Este gift já foi resgatado anteriormente.")

    product_id = gift["product_id"]
    field_id   = gift["field_id"]
    dummy      = gift.get("dummy", False)

    products = db.get_document("loja_products") or {}
    product  = products.get(product_id) or {}
    campo    = (product.get("campos") or {}).get(field_id) or {}
    pname    = product.get("name") or product_id
    fname    = campo.get("name") or field_id
    is_inf   = (campo.get("infinite_stock") or {}).get("enabled", False)

    # ── Obter item a entregar ─────────────────────────────────────────────────
    item_text = None
    if dummy:
        item_text = None  # dummy: não entrega nada
    elif gift.get("reserved_item"):
        item_text = gift["reserved_item"]  # estoque normal: item já reservado
    elif is_inf:
        item_text = campo["infinite_stock"].get("value") or "—"  # infinito: valor configurado
    else:
        return await _err("Este gift não possui item configurado. Contate o suporte.")

    # ── Tentar enviar por DM ──────────────────────────────────────────────────
    dm_ok = False
    if not dummy:
        try:
            dm = await user.create_dm()
            if app_mode == "embed":
                embed = disnake.Embed(
                    title=f"{emoji.gift2} Gift Resgatado!",
                    description=(
                        f"**Produto:** `{pname}`\n"
                        f"**Campo:** `{fname}`\n\n"
                        f"**Seu item:**\n```{item_text}```"
                    ),
                    **_ekw(),
                )
                await dm.send(embed=embed)
            else:
                container = disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.gift2} Gift Resgatado!\n-# **{pname}** > **{fname}**"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(f"**Seu item:**\n```{item_text}```"),
                    **_ckw(),
                )
                await dm.send(components=[container], flags=disnake.MessageFlags(is_components_v2=True))
            dm_ok = True
        except disnake.Forbidden:
            # DM bloqueada — devolver item reservado ao estoque se aplicável
            if gift.get("reserved_item") and not is_inf:
                from modules.loja.cart.stock_manager import StockManager
                StockManager.add_stock_items(product_id, field_id, [gift["reserved_item"]])
            return await _err(
                "Não consegui enviar sua DM!\n"
                "Habilite mensagens diretas nas configurações de privacidade do servidor e tente novamente."
            )
    else:
        dm_ok = True  # dummy não precisa de DM

    # ── Marcar como resgatado ─────────────────────────────────────────────────
    gifts[code].update(
        redeemed=True,
        redeemed_by=str(user.id),
        redeemed_at=int(time.time()),
    )
    db.save_document("gifts_data", {}, gifts)

    # ── Resposta de sucesso ───────────────────────────────────────────────────
    if dummy:
        success_msg = f"{emoji.gift2} Gift `{code}` resgatado!\n-# Produto: **{pname}** > **{fname}**"
    else:
        success_msg = f"{emoji.gift2} Gift resgatado! Seu item foi enviado no privado.\n-# Produto: **{pname}** > **{fname}**"

    if app_mode == "embed":
        await respond(True, embed=disnake.Embed(description=success_msg, **_ekw()))
    else:
        await respond(True,
            components=[disnake.ui.Container(disnake.ui.TextDisplay(success_msg), **_ckw())],
            flags=disnake.MessageFlags(is_components_v2=True),
        )


# ─── Cog ─────────────────────────────────────────────────────────────────────

class GiftRedeemerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Botão "Gift_Resgatar" no painel ──────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "Gift_Resgatar":
            return
        cfg = db.get_document("gifts_config") or {}
        if cfg.get("redeem_mode", "painel") != "painel":
            return
        await inter.response.send_modal(ResgateGiftModal())

    # ── Modal de resgate ─────────────────────────────────────────────────────

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        if inter.custom_id != "GiftRedeem_Modal":
            return

        code = inter.text_values.get("codigo", "").strip()

        async def respond(ephemeral: bool, **kwargs):
            flags = kwargs.pop("flags", None)
            if not inter.response.is_done():
                if flags:
                    await inter.response.send_message(flags=flags, ephemeral=ephemeral, **kwargs)
                else:
                    await inter.response.send_message(ephemeral=ephemeral, **kwargs)
            else:
                if flags:
                    await inter.followup.send(flags=flags, ephemeral=ephemeral, **kwargs)
                else:
                    await inter.followup.send(ephemeral=ephemeral, **kwargs)

        await _processar_resgate(inter.user, code, self.bot, respond)

    # ── Modo Canal: escuta mensagem com código no canal configurado ───────────

    @commands.Cog.listener("on_message")
    async def on_canal_message(self, msg: disnake.Message):
        if msg.author.bot or isinstance(msg.channel, disnake.DMChannel):
            return

        cfg = db.get_document("gifts_config") or {}
        if cfg.get("redeem_mode") != "canal":
            return

        canal_id = cfg.get("canal_id")
        if not canal_id or str(msg.channel.id) != str(canal_id):
            return

        try:
            await msg.delete()
        except Exception:
            pass

        async def respond(ephemeral: bool, **kwargs):
            # No modo canal a resposta vai por DM (já tratado em _processar_resgate)
            # mas enviamos confirmação/erro também por DM aqui
            kwargs.pop("flags", None)
            try:
                await msg.author.send(**kwargs)
            except disnake.Forbidden:
                pass

        class _FakeUser:
            id   = msg.author.id
            create_dm = msg.author.create_dm

        await _processar_resgate(msg.author, msg.content.strip(), self.bot, respond)

    # ── Slash command /gift ───────────────────────────────────────────────────

    @commands.slash_command(name="gift", description="Resgate um gift com seu código.")
    async def gift_command(
        self,
        inter: disnake.ApplicationCommandInteraction,
        codigo: str = commands.Param(description="Código do gift (ex: XXXX-XXXX-XXXX-XXXX)"),
    ):
        cfg = db.get_document("gifts_config") or {}
        if cfg.get("redeem_mode", "painel") != "comando":
            await inter.response.send_message("O resgate por comando não está ativo no momento.", ephemeral=True)
            return

        async def respond(ephemeral: bool, **kwargs):
            flags = kwargs.pop("flags", None)
            if not inter.response.is_done():
                if flags:
                    await inter.response.send_message(flags=flags, ephemeral=ephemeral, **kwargs)
                else:
                    await inter.response.send_message(ephemeral=ephemeral, **kwargs)
            else:
                if flags:
                    await inter.followup.send(flags=flags, ephemeral=ephemeral, **kwargs)
                else:
                    await inter.followup.send(ephemeral=ephemeral, **kwargs)

        await _processar_resgate(inter.user, codigo, self.bot, respond)