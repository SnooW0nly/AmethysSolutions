import asyncio
import io
import time
import disnake
from functions.database import database as db
from functions.emoji import emoji
from ..config_giveaways import get_giveaways
from tasks.giveaways.logger_giveaways import log_giveaway_event


class RifaConfigModal(disnake.ui.Modal):
    def __init__(self, inter, giveaway_id: str, current: dict):
        self.inter = inter
        self.giveaway_id = giveaway_id
        components = [
            disnake.ui.TextInput(label="Preço por Bilhete (R$)", custom_id="ticket_price",
                value=str(current.get("ticket_price", "5.00")), placeholder="Ex: 5.00", max_length=10),
            disnake.ui.TextInput(label="Máximo de Bilhetes (0 = ilimitado)", custom_id="max_tickets",
                value=str(current.get("max_tickets", "100")), placeholder="Ex: 100", max_length=6),
            disnake.ui.TextInput(label="Bilhetes por Usuário", custom_id="tickets_per_user",
                value=str(current.get("tickets_per_user", "1")), placeholder="Ex: 1", max_length=3),
        ]
        super().__init__(title="Configurar Rifa", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            price = float(inter.text_values["ticket_price"].replace(",", "."))
            max_t = int(inter.text_values["max_tickets"])
            per_user = int(inter.text_values["tickets_per_user"])
            if price <= 0 or per_user <= 0:
                raise ValueError
        except ValueError:
            return await inter.response.send_message(f"{emoji.wrong} Valores inválidos. Use números positivos.", ephemeral=True)

        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id, {})
        rifa = giveaway.setdefault("rifa", {})
        rifa.update({"ticket_price": price, "max_tickets": max_t, "tickets_per_user": per_user})
        db.salvar("database/giveaways/giveaways_data.json", config)

        await inter.response.send_message(f"{emoji.correct} Rifa configurada com sucesso!", ephemeral=True)
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await self.inter.edit_original_message(components=RifaView_components(self.inter, self.giveaway_id))
        else:
            embed, components = RifaView_embed(self.inter, self.giveaway_id)
            await self.inter.edit_original_message(embed=embed, components=components)


def RifaView_components(inter, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    rifa = giveaway_data.get("rifa", {})
    enabled = rifa.get("enabled", False)
    price = rifa.get("ticket_price", 0.0)
    max_t = rifa.get("max_tickets", 0)
    per_user = rifa.get("tickets_per_user", 1)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    status_text = (
        f"{emoji.on if enabled else emoji.off} **Rifa:** `{'Ativada' if enabled else 'Desativada'}`\n"
        f"{emoji.dollar} **Preço por Bilhete:** `R$ {price:.2f}`\n"
        f"{emoji.members} **Máx. Bilhetes:** `{max_t if max_t else 'Ilimitado'}`\n"
        f"{emoji.member} **Bilhetes por Usuário:** `{per_user}`"
    )

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > **Configurar Rifa**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Desativar Rifa" if enabled else "Ativar Rifa",
                style=disnake.ButtonStyle.danger if enabled else disnake.ButtonStyle.green,
                custom_id=f"GiveawayRifa_Toggle_{giveaway_id}"
            ),
            disnake.ui.Button(
                label="Configurar", style=disnake.ButtonStyle.blurple,
                emoji=emoji.settings, custom_id=f"GiveawayRifa_Config_{giveaway_id}"
            ),
        ),
        **container_kwargs
    )
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back,
            custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}")
    )
    return [container, buttons]


def RifaView_embed(inter, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    rifa = giveaway_data.get("rifa", {})
    enabled = rifa.get("enabled", False)
    price = rifa.get("ticket_price", 0.0)
    max_t = rifa.get("max_tickets", 0)
    per_user = rifa.get("tickets_per_user", 1)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Configurar Rifa: {giveaway_name}",
        description=(
            f"{emoji.on if enabled else emoji.off} **Rifa:** `{'Ativada' if enabled else 'Desativada'}`\n"
            f"{emoji.dollar} **Preço por Bilhete:** `R$ {price:.2f}`\n"
            f"{emoji.members} **Máx. Bilhetes:** `{max_t if max_t else 'Ilimitado'}`\n"
            f"{emoji.member} **Bilhetes por Usuário:** `{per_user}`"
        ),
        **embed_kwargs
    )
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(
                label="Desativar Rifa" if enabled else "Ativar Rifa",
                style=disnake.ButtonStyle.danger if enabled else disnake.ButtonStyle.green,
                custom_id=f"GiveawayRifa_Toggle_{giveaway_id}"
            ),
            disnake.ui.Button(
                label="Configurar", style=disnake.ButtonStyle.blurple,
                emoji=emoji.settings, custom_id=f"GiveawayRifa_Config_{giveaway_id}"
            ),
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back,
                custom_id=f"GiveawayEdit_BackToPanel_{giveaway_id}")
        )
    ]
    return embed, components


async def process_rifa_ticket_purchase(inter: disnake.MessageInteraction, giveaway_id: str, task_id: str, bot):
    """Inicia compra de bilhete via sistema de pagamento existente."""
    await inter.response.defer(ephemeral=True)

    config = db.obter("database/giveaways/giveaways_data.json")
    giveaway = config.get(giveaway_id, {})
    rifa = giveaway.get("rifa", {})
    task = next((t for t in giveaway.get("tasks", []) if t.get("id") == task_id), None)

    if not task or task.get("rolled"):
        return await inter.followup.send(f"{emoji.wrong} Este sorteio não está mais disponível.", ephemeral=True)

    price = rifa.get("ticket_price", 0)
    per_user = rifa.get("tickets_per_user", 1)
    max_t = rifa.get("max_tickets", 0)

    if price <= 0:
        return await inter.followup.send(f"{emoji.wrong} A rifa não está configurada corretamente.", ephemeral=True)

    user_id = inter.author.id
    participants = task.get("participants", [])
    user_tickets = participants.count(user_id)

    if user_tickets >= per_user:
        return await inter.followup.send(
            f"{emoji.wrong} Você já comprou o máximo de **{per_user}** bilhete(s) nesta rifa.", ephemeral=True)

    if max_t and len(participants) >= max_t:
        return await inter.followup.send(f"{emoji.wrong} Todos os bilhetes já foram vendidos!", ephemeral=True)

    # Criar pagamento via sistema existente
    try:
        from modules.loja.cart.checkout import _create_payment
        payment_data = await _create_payment(
            payment_method="pix",
            amount=price,
            user=inter.author,
            description=f"Bilhete Rifa - {giveaway.get('name')}"
        )
    except Exception as e:
        return await inter.followup.send(f"{emoji.wrong} Erro ao criar pagamento: {e}", ephemeral=True)

    provider = payment_data.get("_provider", "")

    from modules.loja.cart.checkout import _extract_urls, _extract_payment_ids, _extract_qr_image, _http_get_bytes
    checkout_url, copy_code = _extract_urls(payment_data)
    payment_ids = _extract_payment_ids(payment_data)
    qr_bytes, qr_url = _extract_qr_image(payment_data)

    if qr_url and not qr_bytes:
        qr_bytes = await _http_get_bytes(qr_url)

    content = (
        f"**{emoji.giveaway} Bilhete de Rifa**\n"
        f"Sorteio: **{giveaway.get('name')}**\n"
        f"Valor: **R$ {price:.2f}**\n\n"
    )
    if copy_code:
        content += f"**PIX Copia e Cola:**\n```{copy_code}```\n"
    if checkout_url:
        content += f"[Pagar agora]({checkout_url})\n"

    send_kwargs = {"content": content, "ephemeral": True}
    if qr_bytes:
        send_kwargs["file"] = disnake.File(io.BytesIO(qr_bytes), filename="qrcode.png")

    await inter.followup.send(**send_kwargs)

    # Monitorar em background
    asyncio.create_task(
        _monitor_rifa_payment(bot, inter, giveaway_id, task_id, payment_ids, provider, price)
    )


async def _monitor_rifa_payment(bot, inter, giveaway_id: str, task_id: str,
                                 payment_ids: dict, provider: str, price: float):
    """Monitora status do pagamento e confirma bilhete quando aprovado."""
    from modules.loja.cart.checkout import _get_provider_checkers, _find_first

    checkers = _get_provider_checkers()
    checker = checkers.get(provider)
    if not checker:
        return

    payment_id = (
        payment_ids.get("txid") or payment_ids.get("payment_id") or
        payment_ids.get("id") or payment_ids.get("correlationID")
    )
    if not payment_id:
        return

    approved_statuses = {
        "approved", "paid", "completed", "completo", "succeeded",
        "accredited", "concluida", "pago", "aprovado"
    }
    failed_statuses = {
        "canceled", "cancelled", "expired", "failed", "falha",
        "removida", "cancelado", "expirado"
    }

    start = time.time()
    # Intervalo progressivo: igual ao _monitor_payment do checkout
    intervals = [(120, 10), (300, 15), (600, 20), (3600, 60)]

    while time.time() - start < 3600:
        elapsed = time.time() - start
        interval = 60
        for limit, ivl in intervals:
            if elapsed < limit:
                interval = ivl
                break
        await asyncio.sleep(interval)

        try:
            chk = await checker(payment_id)
        except Exception:
            continue

        status = str(_find_first(chk, ["status", "payment_status", "state"]) or "").lower()
        # Fallback para raw (Efí / MisticPay)
        if not status and isinstance(chk, dict):
            raw = chk.get("raw", {})
            if isinstance(raw, dict):
                status = str(raw.get("status") or "").lower()
        is_paid = chk.get("paid", False) if isinstance(chk, dict) else False

        if status in approved_statuses or is_paid:
            # Recarregar config e adicionar participante
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            task = next((t for t in giveaway.get("tasks", []) if t.get("id") == task_id), None)

            if not task or task.get("rolled"):
                break

            rifa = giveaway.get("rifa", {})
            per_user = rifa.get("tickets_per_user", 1)
            max_t = rifa.get("max_tickets", 0)
            participants = task.setdefault("participants", [])
            user_id = inter.author.id
            user_tickets = participants.count(user_id)

            if user_tickets < per_user and (not max_t or len(participants) < max_t):
                participants.append(user_id)
                db.salvar("database/giveaways/giveaways_data.json", config)

                # Atualizar botão na mensagem do sorteio
                try:
                    channel = bot.get_channel(task["channel_id"])
                    if channel and task.get("message_id"):
                        msg = await channel.fetch_message(task["message_id"])
                        button_data = giveaway.get("button", {})
                        base_label = button_data.get("label", "Participar")
                        participant_count = len(participants)
                        style_map = {
                            "green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey,
                            "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary
                        }
                        btn = disnake.ui.Button(
                            label=f"{base_label} ({participant_count})",
                            style=style_map.get(button_data.get("style", "green")),
                            custom_id=f"Giveaway_Participate_{giveaway_id}_{task_id}"
                        )
                        if button_data.get("emoji"):
                            btn = disnake.ui.Button(
                                label=f"{base_label} ({participant_count})",
                                style=style_map.get(button_data.get("style", "green")),
                                emoji=button_data.get("emoji"),
                                custom_id=f"Giveaway_Participate_{giveaway_id}_{task_id}"
                            )
                        info_btn = disnake.ui.Button(
                            label="", emoji=emoji.information,
                            style=disnake.ButtonStyle.grey,
                            custom_id=f"Giveaway_Info_{giveaway_id}_{task_id}"
                        )
                        from modules.giveaways.container_utils import ContainerUtils
                        style = giveaway.get("message_style", "embed")
                        if style == "container":
                            data = giveaway.get("container", {})
                            container = ContainerUtils.montar_container(
                                conteudo=data.get("content"), imagem_url=data.get("image_url"),
                                cor_hex=data.get("color"), thumbnail_url=data.get("thumbnail_url")
                            )
                            await msg.edit(components=[container, disnake.ui.ActionRow(btn, info_btn)])
                        else:
                            view = disnake.ui.View(timeout=None)
                            view.add_item(btn)
                            view.add_item(info_btn)
                            await msg.edit(view=view)
                except Exception:
                    pass

                await log_giveaway_event(
                    bot=bot, giveaway_id=giveaway_id,
                    title="Sorteios - Bilhete de Rifa Comprado",
                    lines=[
                        f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                        f"{emoji.member} **Membro:** {inter.author.mention} (`{inter.author.id}`)",
                        f"{emoji.dollar} **Valor Pago:** `R$ {price:.2f}`",
                        f"{emoji.correct} **Bilhetes deste usuário:** `{user_tickets + 1}/{per_user}`"
                    ]
                )

                try:
                    await inter.author.send(
                        f"{emoji.correct} Seu bilhete foi confirmado no sorteio "
                        f"**{giveaway.get('name')}**! Boa sorte! 🍀"
                    )
                except Exception:
                    pass
            break

        if status in failed_statuses:
            try:
                await inter.author.send(
                    f"{emoji.wrong} Seu pagamento para o bilhete da rifa "
                    f"**{giveaway.get('name', '')}** não foi aprovado."
                )
            except Exception:
                pass
            break