import disnake
from typing import Optional

from functions.database import database as db
from functions.emoji import emoji
from .config import get_roblox_config, calcular_preco_robux, MESSAGES
from .roblox_orders import get_order, update_order


def _get_admin_role_id() -> Optional[int]:
    cargos = db.get_document("cargos") or {}
    return cargos.get("cargo_admin")


def _get_suporte_role_id() -> Optional[int]:
    cargos = db.get_document("cargos") or {}
    return cargos.get("cargo_suporte")


async def _build_ticket_initial_message(
    guild: disnake.Guild,
    order: dict,
    mode: str,
) -> tuple:
    order_type = order.get("order_type", "robux")
    roblox_username = order.get("roblox_username", "?")
    roblox_user_id = order.get("roblox_user_id", 0)
    quantity = order.get("quantity", 0)
    robux_bruto = order.get("robux_bruto", 0)
    total_price = order.get("total_price", 0)
    user_id = order.get("user_id")
    order_id = order.get("order_id", "?")
    extra = order.get("extra", {})
    gamepass_name = extra.get("gamepass_name", "")
    avatar_url = extra.get("avatar_url")
    cobrir_taxa = extra.get("cobrir_taxa", True)
    taxa_label = "Loja cobre" if cobrir_taxa else "Você paga no Roblox"
    profile_url = f"https://www.roblox.com/users/{roblox_user_id}/profile"

    # ── Método de entrega ──
    config = get_roblox_config()
    delivery_method = config.get("delivery_method", "gamepass")
    group_id = config.get("group_id", None)
    group_link = config.get("group_link", "")

    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    action_row = disnake.ui.ActionRow(
        disnake.ui.Button(label="Continuar para Pagamento", style=disnake.ButtonStyle.green, emoji=emoji.arrow, custom_id=f"RobloxTicket_ContinuarPagamento:{order_id}"),
        disnake.ui.Button(label="Cancelar", style=disnake.ButtonStyle.red, emoji=emoji.wrong, custom_id=f"RobloxTicket_Cancelar:{order_id}"),
    )

    # ── Montar bloco de instrução conforme método ──
    if delivery_method == "group":
        if group_link:
            group_ref = f"[Clique aqui para entrar no grupo]({group_link})"
        elif group_id:
            group_ref = f"[Clique aqui para entrar no grupo](https://www.roblox.com/groups/{group_id})"
        else:
            group_ref = "⚠️ Link do grupo não configurado — contate um administrador."

        instrucao_entrega = (
            f"**📌 Método de entrega: Group Funds**\n"
            f"Entre no grupo Roblox da loja antes de efetuar o pagamento.\n"
            f"{group_ref}\n"
            f"-# Após entrar no grupo, clique em **Continuar para Pagamento**."
        )
    else:
        instrucao_entrega = (
            f"**📌 Método de entrega: Gamepass**\n"
            f"Crie uma gamepass de `{robux_bruto} R$` no seu jogo e informe o link ao suporte após o pagamento."
        )

    if order_type == "robux":
        body_core = (
            f"Olá, <@{user_id}>! Nossa equipe já está ciente do seu pedido.\n\n"
            f"**Perfil:** [{roblox_username}]({profile_url})\n"
            f"**Robux solicitados:** `{quantity} R$`\n"
            f"**Robux brutos:** `{robux_bruto} R$`\n"
            f"**Taxa Roblox (30%):** {taxa_label}\n"
            f"**Valor a pagar:** `R$ {total_price:.2f}`\n\n"
            f"{instrucao_entrega}\n\n"
            f"-# Pedido: `{order_id}` | Status: `Aguardando Pagamento`"
        )
    else:
        body_core = (
            f"Olá, <@{user_id}>! Nossa equipe já está ciente do seu pedido.\n\n"
            f"**Perfil:** [{roblox_username}]({profile_url})\n"
            f"**Gamepass:** `{gamepass_name}`\n"
            f"**Robux da gamepass:** `{quantity} R$`\n"
            f"**Robux brutos:** `{robux_bruto} R$`\n"
            f"**Valor a pagar:** `R$ {total_price:.2f}`\n\n"
            f"{instrucao_entrega}\n\n"
            f"-# Pedido: `{order_id}` | Status: `Aguardando Pagamento`"
        )

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)
        embed = disnake.Embed(description=body_core)
        if embed_color:
            embed.color = embed_color
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        return embed, [action_row], None

    # — Modo container —
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    # Avatar via Section + Thumbnail (componente v2)
    if avatar_url:
        main_content = disnake.ui.Section(
            disnake.ui.TextDisplay(body_core),
            accessory=disnake.ui.Thumbnail(media=avatar_url),
        )
    else:
        main_content = disnake.ui.TextDisplay(body_core)

    components = [
        disnake.ui.Container(
            main_content,
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            action_row,
            **container_kwargs,
        )
    ]
    return None, components, disnake.MessageFlags(is_components_v2=True)


async def _build_payment_approved_message(order: dict, mode: str) -> tuple:
    order_type = order.get("order_type", "robux")
    roblox_username = order.get("roblox_username", "?")
    roblox_user_id = order.get("roblox_user_id", 0)
    quantity = order.get("quantity", 0)
    robux_bruto = order.get("robux_bruto", 0)
    total_price = order.get("total_price", 0)
    user_id = order.get("user_id")
    order_id = order.get("order_id", "?")
    extra = order.get("extra", {})
    gamepass_name = extra.get("gamepass_name", "")
    avatar_url = extra.get("avatar_url")
    profile_url = f"https://www.roblox.com/users/{roblox_user_id}/profile"

    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    admin_action_row = disnake.ui.ActionRow(
        disnake.ui.Button(
            label=f"{emoji.correct} Entrega Feita — Fechar Carrinho",
            style=disnake.ButtonStyle.green,
            custom_id=f"RobloxTicket_EntregaFeita:{order_id}",
        ),
    )

    if mode == "embed":
        embed_color = None
        if primary_color_hex:
            embed_color = int(primary_color_hex.replace("#", ""), 16)

        if order_type == "robux":
            description = (
                f"{emoji.correct} **Pagamento aprovado!** Aguardando entrega dos Robux.\n\n"
                f"**Perfil:** [{roblox_username}]({profile_url})\n"
                f"**Robux a receber:** `{quantity} R$`\n"
                f"**Robux brutos:** `{robux_bruto} R$`\n"
                f"**Valor pago:** `R$ {total_price:.2f}`\n\n"
                f"Nossa equipe irá realizar a entrega em breve!\n\n"
                f"-# Pedido: `{order_id}` | Status: `Aguardando Entrega`"
            )
        else:
            description = (
                f"{emoji.correct} **Pagamento aprovado!** Aguardando entrega da Gamepass.\n\n"
                f"**Perfil:** [{roblox_username}]({profile_url})\n"
                f"**Gamepass:** `{gamepass_name}`\n"
                f"**Robux:** `{quantity} R$`\n"
                f"**Valor pago:** `R$ {total_price:.2f}`\n\n"
                f"Nossa equipe irá realizar a compra em breve!\n\n"
                f"-# Pedido: `{order_id}` | Status: `Aguardando Entrega`"
            )

        embed = disnake.Embed(description=description)
        if embed_color:
            embed.color = embed_color
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

        return embed, [admin_action_row], None

    # — Modo container —
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    if order_type == "robux":
        body_text = (
            f"# {emoji.correct} Pagamento Aprovado!\n"
            f"Aguardando entrega dos Robux.\n\n"
            f"**Perfil:** [{roblox_username}]({profile_url})\n"
            f"**Robux a receber:** `{quantity} R$`\n"
            f"**Robux brutos:** `{robux_bruto} R$`\n"
            f"**Valor pago:** `R$ {total_price:.2f}`\n\n"
            f"Nossa equipe irá realizar a entrega em breve!\n\n"
            f"-# Pedido: `{order_id}` | Status: `Aguardando Entrega`"
        )
    else:
        body_text = (
            f"# {emoji.correct} Pagamento Aprovado!\n"
            f"Aguardando entrega da Gamepass.\n\n"
            f"**Perfil:** [{roblox_username}]({profile_url})\n"
            f"**Gamepass:** `{gamepass_name}`\n"
            f"**Robux:** `{quantity} R$`\n"
            f"**Valor pago:** `R$ {total_price:.2f}`\n\n"
            f"Nossa equipe irá realizar a compra em breve!\n\n"
            f"-# Pedido: `{order_id}` | Status: `Aguardando Entrega`"
        )

    if avatar_url:
        main_content = disnake.ui.Section(
            disnake.ui.TextDisplay(body_text),
            accessory=disnake.ui.Thumbnail(media=avatar_url),
        )
    else:
        main_content = disnake.ui.TextDisplay(body_text)

    components = [
        disnake.ui.Container(
            main_content,
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            admin_action_row,
            **container_kwargs,
        )
    ]
    return None, components, disnake.MessageFlags(is_components_v2=True)


class RobloxTicketManager:
    @staticmethod
    async def create_ticket(
        bot,
        inter: disnake.MessageInteraction,
        order_id: str,
        order_type: str,
    ):
        order = get_order(order_id)
        if not order:
            try:
                await inter.edit_original_message(content=f"{emoji.wrong} Erro interno: pedido não encontrado.", embeds=[], components=[])
            except Exception:
                pass
            return

        guild = inter.guild
        admin_role_id = _get_admin_role_id()
        suporte_role_id = _get_suporte_role_id()

        # ── Criar tópico (thread) no próprio canal da interação ──
        parent_channel = inter.channel
        if not isinstance(parent_channel, (disnake.TextChannel, disnake.NewsChannel)):
            try:
                await inter.edit_original_message(
                    content=f"{emoji.wrong} Carrinho só podem ser criados em canais de texto.", embeds=[], components=[]
                )
            except Exception:
                pass
            return

        thread_name = f"🛒│{inter.user.name}"

        try:
            ticket_channel = await parent_channel.create_thread(
                name=thread_name,
                type=disnake.ChannelType.private_thread,
                invitable=False,
                reason=f"[🛒] Pedido: {order_id} | User: {inter.user.id}",
            )
        except disnake.Forbidden:
            # Sem boost suficiente para tópicos privados → usa tópico público
            try:
                ticket_channel = await parent_channel.create_thread(
                    name=thread_name,
                    type=disnake.ChannelType.public_thread,
                    reason=f"[🛒] Pedido: {order_id} | User: {inter.user.id}",
                )
            except Exception as e:
                try:
                    await inter.edit_original_message(content=f"{emoji.wrong} Erro ao criar carrinho: {e}", embeds=[], components=[])
                except Exception:
                    pass
                return
        except Exception as e:
            try:
                await inter.edit_original_message(content=f"{emoji.wrong} Erro ao criar carrinho: {e}", embeds=[], components=[])
            except Exception:
                pass
            return

        # Adicionar o comprador ao tópico
        try:
            await ticket_channel.add_user(inter.user)
        except Exception:
            pass

        # Adicionar membros dos cargos admin e suporte ao tópico
        if admin_role_id:
            role = guild.get_role(int(admin_role_id))
            if role:
                for member in role.members:
                    try:
                        await ticket_channel.add_user(member)
                    except Exception:
                        pass
        if suporte_role_id and suporte_role_id != admin_role_id:
            role = guild.get_role(int(suporte_role_id))
            if role:
                for member in role.members:
                    try:
                        await ticket_channel.add_user(member)
                    except Exception:
                        pass

        update_order(order_id, {"thread_channel_id": ticket_channel.id})

        mode = db.get_document("custom_mode").get("mode")
        embed, components, flags = await _build_ticket_initial_message(guild, order, mode)

        mention_text = f"<@{inter.user.id}>"
        if admin_role_id:
            mention_text += f" <@&{admin_role_id}>"

        try:
            if mode == "embed":
                await ticket_channel.send(content=mention_text, embed=embed, components=components)
            else:
                # v2: content não pode ser enviado junto com IS_COMPONENTS_V2
                # Envia a menção primeiro como mensagem normal, depois o container
                await ticket_channel.send(content=mention_text)
                await ticket_channel.send(components=components, flags=flags)
        except Exception as e:
            print(f"[RobloxTicket] Erro ao enviar mensagem do ticket: {e}")

        redirect_url = f"https://discord.com/channels/{guild.id}/{ticket_channel.id}"
        try:
            await inter.edit_original_message(
                content=None,
                embeds=[],
                components=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Carrinho criado! Ir para o ticket",
                            emoji=emoji.arrow,
                            style=disnake.ButtonStyle.link,
                            url=redirect_url,
                        )
                    )
                ],
            )
        except Exception:
            pass