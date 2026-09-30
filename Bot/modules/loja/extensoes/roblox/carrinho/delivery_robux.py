import disnake
import asyncio
from disnake.ext import commands
from typing import Optional

from functions.database import database as db
from functions.emoji import emoji
from .config import get_roblox_config, MESSAGES
from .roblox_orders import get_order, update_order
from .roblox_auto_delivery import tentar_entrega_automatica, is_auto_delivery_active


async def _try_send_transcript(bot, channel: disnake.TextChannel, order: dict):
    """
    Gera e envia o transcript do ticket para o canal de log configurado,
    se transcripts estiverem habilitados nas preferências da loja.
    """
    try:
        prefs = db.get_document("loja_preferences") or {}
        if not prefs.get("transcript_enabled", False):
            return
        transcript_channel_id = prefs.get("transcript_channel_id")
        if not transcript_channel_id:
            return

        from .generate_transcript import generate_cart_transcript, send_cart_transcript_to_channel
        transcript_file = await generate_cart_transcript(
            thread=channel,
            bot=bot,
            cart=order,
        )
        if transcript_file:
            await send_cart_transcript_to_channel(
                bot=bot,
                transcript_file=transcript_file,
                channel_id=int(transcript_channel_id),
                cart=order,
            )
    except Exception as e:
        print(f"[RobloxDelivery] Erro ao enviar transcript: {e}")


async def _notify_user_delivery(
    bot,
    order: dict,
    admin_user: disnake.Member,
    auto: bool = False,
):
    config = get_roblox_config()
    canais = config.get("canais", {})
    canal_entregas_id = canais.get("canal_entregas")

    mode = db.get_document("custom_mode").get("mode")
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    order_type = order.get("order_type", "robux")
    roblox_username = order.get("roblox_username", "?")
    roblox_user_id = order.get("roblox_user_id", 0)
    quantity = order.get("quantity", 0)
    total_price = order.get("total_price", 0)
    user_id = order.get("user_id")
    order_id = order.get("order_id", "?")
    extra = order.get("extra", {})
    gamepass_name = extra.get("gamepass_name", "")
    profile_url = f"https://www.roblox.com/users/{roblox_user_id}/profile"

    if canal_entregas_id:
        guild = bot.get_guild(order.get("guild_id"))
        if guild:
            canal_entregas = guild.get_channel(int(canal_entregas_id))
            if canal_entregas:
                try:
                    entregue_por = "⚡ Automático" if auto else admin_user.mention
                    if order_type == "robux":
                        delivery_body = (
                            f"## 🎉 Entrega Realizada!\n"
                            f"<@{user_id}>, sua entrega de Robux foi concluída!\n\n"
                            f"**Roblox:** [{roblox_username}]({profile_url})\n"
                            f"**Robux entregues:** `{quantity}`\n"
                            f"**Valor pago:** `R$ {total_price:.2f}`\n"
                            f"**Entregue por:** {entregue_por}\n\n"
                            f"-# Pedido: `{order_id}`"
                        )
                    else:
                        delivery_body = (
                            f"## 🎉 Entrega Realizada!\n"
                            f"<@{user_id}>, sua Gamepass foi entregue!\n\n"
                            f"**Roblox:** [{roblox_username}]({profile_url})\n"
                            f"**Gamepass:** `{gamepass_name}`\n"
                            f"**Robux:** `{quantity}`\n"
                            f"**Valor pago:** `R$ {total_price:.2f}`\n"
                            f"**Entregue por:** {entregue_por}\n\n"
                            f"-# Pedido: `{order_id}`"
                        )

                    if mode == "embed":
                        embed_color = None
                        if primary_color_hex:
                            embed_color = int(primary_color_hex.replace("#", ""), 16)
                        embed = disnake.Embed(description=delivery_body)
                        if embed_color:
                            embed.color = embed_color
                        await canal_entregas.send(content=f"<@{user_id}>", embed=embed)
                    else:
                        container_kwargs = {}
                        if primary_color_hex:
                            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                        components = [
                            disnake.ui.Container(
                                disnake.ui.TextDisplay(delivery_body),
                                **container_kwargs,
                            )
                        ]
                        await canal_entregas.send(
                            content=f"<@{user_id}>",
                            components=components,
                            flags=disnake.MessageFlags(is_components_v2=True),
                        )
                except Exception as e:
                    print(f"[RobloxDelivery] Erro ao enviar notificação de entrega: {e}")


class DeliveryRobux(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id or ""

        if custom_id.startswith("RobloxTicket_EntregaFeita:"):
            if not inter.user.guild_permissions.administrator:
                await inter.response.send_message(f"{emoji.wrong} Apenas administradores podem marcar a entrega como feita.", ephemeral=True)
                return

            order_id = custom_id.split(":", 1)[1]
            order = get_order(order_id)

            if not order:
                await inter.response.send_message(f"{emoji.wrong} Pedido não encontrado.", ephemeral=True)
                return

            if order.get("status") not in ("payment_approved", "pending_delivery"):
                await inter.response.send_message(f"{emoji.wrong} Este pedido não está aguardando entrega.", ephemeral=True)
                return

            await inter.response.defer(ephemeral=False)

            # ── Tentar entrega automática ──────────────────────────────────────
            entregue_auto = False
            auto_erro = ""
            if is_auto_delivery_active():
                entregue_auto, auto_erro = await tentar_entrega_automatica(order)
                if not entregue_auto:
                    print(f"[RobloxDelivery] Auto-entrega falhou para {order_id}: {auto_erro} — caindo no manual")

            update_order(order_id, {
                "status": "delivered",
                "delivered_by": inter.user.id if not entregue_auto else "auto",
                "delivered_at": int(disnake.utils.utcnow().timestamp()),
                "auto_delivered": entregue_auto,
            })

            await _notify_user_delivery(
                bot=self.bot,
                order=order,
                admin_user=inter.user,
                auto=entregue_auto,
            )

            mode = db.get_document("custom_mode").get("mode")
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")

            roblox_username = order.get("roblox_username", "?")
            quantity = order.get("quantity", 0)
            total_price = order.get("total_price", 0)
            user_id = order.get("user_id")
            order_type = order.get("order_type", "robux")
            extra = order.get("extra", {})
            gamepass_name = extra.get("gamepass_name", "")

            closed_text = (
                f"## {emoji.correct} Carrinho Encerrado\n"
                f"{'⚡ Entrega realizada automaticamente.' if entregue_auto else f'A entrega foi confirmada por {inter.user.mention}.'}\n\n"
                f"**Comprador:** <@{user_id}>\n"
                f"**Roblox:** `{roblox_username}`\n"
                f"{'**Gamepass:** `' + gamepass_name + '`' + chr(10) if gamepass_name else ''}"
                f"**Robux:** `{quantity}` | **Valor:** `R$ {total_price:.2f}`\n\n"
                f"-# Pedido: `{order_id}` | Fechando em 30 segundos..."
            )

            if mode == "embed":
                embed_color = None
                if primary_color_hex:
                    embed_color = int(primary_color_hex.replace("#", ""), 16)
                embed = disnake.Embed(description=closed_text)
                if embed_color:
                    embed.color = embed_color
                try:
                    await inter.message.edit(embeds=[], components=[])
                except Exception:
                    pass
                await inter.channel.send(embed=embed)
            else:
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                components = [
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(closed_text),
                        **container_kwargs,
                    )
                ]
                try:
                    await inter.message.edit(components=[])
                except Exception:
                    pass
                await inter.channel.send(
                    components=components,
                    flags=disnake.MessageFlags(is_components_v2=True),
                )

            # ── Enviar transcript antes de fechar ──
            await _try_send_transcript(self.bot, inter.channel, order)

            await asyncio.sleep(30)
            try:
                await inter.channel.delete()
            except Exception:
                pass


def setup(bot: commands.Bot):
    bot.add_cog(DeliveryRobux(bot))