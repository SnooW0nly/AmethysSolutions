"""
Módulo de Suporte a Produto no Ticket
--------------------------------------
Quando a preferência "Suporte a Produto" está ativada em um painel, ao abrir
um ticket é enviado um StringSelect com os produtos que o usuário já comprou.
O cliente escolhe qual produto quer suporte; o select é então editado para
mostrar somente o nome do produto selecionado (sem exibir o que foi entregue).
"""

import disnake
from functions.database import database as db
from functions.emoji import emoji


# ── Chave do select ──────────────────────────────────────────────────────────
# Formato: ticket_product_support_select:{panel_id}:{user_id}
SELECT_CUSTOM_ID_PREFIX = "ticket_product_support_select"


def _get_user_purchases(user_id: int) -> list[dict]:
    """
    Retorna lista de compras do usuário.
    Cada item: {"product_id": str, "product_name": str}
    Produtos duplicados são exibidos uma única vez.
    """
    purchases_doc = db.get_document("loja_purchases") or {}
    user_purchases = purchases_doc.get(str(user_id), [])

    seen = set()
    result = []
    for purchase in user_purchases:
        pid = str(purchase.get("product_id", ""))
        if not pid or pid in seen:
            continue
        seen.add(pid)

        # Tenta buscar o nome atualizado do produto na loja
        products_doc = db.get_document("loja_products") or {}
        product_data = products_doc.get(pid, {})
        name = product_data.get("name") or purchase.get("product_name") or "Produto"

        result.append({"product_id": pid, "product_name": name})

    return result


def _build_select(panel_id: str, user_id: int, purchases: list[dict]) -> disnake.ui.StringSelect:
    """Monta o StringSelect com as compras do usuário."""
    options = [
        disnake.SelectOption(
            label=p["product_name"][:100],
            value=p["product_id"],
            emoji=emoji.cardbox,
            description="Clique para selecionar este produto"
        )
        for p in purchases[:25]  # Discord limita 25 opções
    ]

    return disnake.ui.StringSelect(
        custom_id=f"{SELECT_CUSTOM_ID_PREFIX}:{panel_id}:{user_id}",
        placeholder="Selecione o produto que deseja suporte...",
        options=options,
        min_values=1,
        max_values=1,
    )


async def send_product_support_select(
    channel: disnake.TextChannel | disnake.Thread,
    user: disnake.Member,
    panel_id: str,
):
    """
    Envia a mensagem com o select de compras no canal do ticket.
    Se o usuário não tiver compras registradas, envia uma mensagem informativa.
    """
    mode = (db.get_document("custom_mode") or {}).get("mode", "components")
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    purchases = _get_user_purchases(user.id)

    if not purchases:
        # Sem compras — avisa a equipe sem expor dados
        if mode == "embed":
            embed = disnake.Embed(
                description=f"{emoji.wrong} {user.mention} não possui compras registradas para selecionar um produto.",
                color=int(primary_color_hex.replace("#", ""), 16) if primary_color_hex else disnake.Color.red().value,
            )
            await channel.send(embed=embed)
        else:
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            await channel.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(
                            f"{emoji.wrong} {user.mention} não possui compras registradas para selecionar um produto."
                        ),
                        **container_kwargs,
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True),
            )
        return

    select = _build_select(panel_id, user.id, purchases)
    action_row = disnake.ui.ActionRow(select)

    if mode == "embed":
        embed = disnake.Embed(
            title=f"{emoji.cardbox} Qual produto você precisa de suporte?",
            description=(
                f"{user.mention}, selecione abaixo o produto sobre o qual você precisa de ajuda.\n"
                f"-# Somente você e a equipe podem ver esta mensagem."
            ),
            color=int(primary_color_hex.replace("#", ""), 16) if primary_color_hex else None,
        )
        await channel.send(embed=embed, components=[action_row])
    else:
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        await channel.send(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"## {emoji.cardbox} Qual produto você precisa de suporte?\n"
                        f"{user.mention}, selecione abaixo o produto sobre o qual você precisa de ajuda.\n"
                        f"-# Somente você e a equipe podem ver esta seleção."
                    ),
                    disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                    action_row,
                    **container_kwargs,
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )


async def handle_product_support_select(inter: disnake.MessageInteraction):
    """
    Handler chamado pelo cog quando o custom_id começa com
    'ticket_product_support_select'.

    Edita a mensagem original para mostrar qual produto foi selecionado
    (sem exibir o conteúdo entregue). Salva a escolha na database do ticket.
    """
    # custom_id = "ticket_product_support_select:{panel_id}:{user_id}"
    parts = inter.component.custom_id.split(":", 2)
    panel_id = parts[1] if len(parts) > 1 else "?"
    owner_id = int(parts[2]) if len(parts) > 2 else 0

    # Apenas o dono do ticket pode selecionar
    if inter.user.id != owner_id:
        await inter.response.send_message(
            f"{emoji.wrong} Apenas quem abriu o ticket pode selecionar o produto.",
            ephemeral=True,
        )
        return

    selected_product_id = inter.values[0]

    # Busca o nome do produto
    products_doc = db.get_document("loja_products") or {}
    product_data = products_doc.get(selected_product_id, {})
    product_name = product_data.get("name", "Produto desconhecido")

    # Salva a escolha no registro do ticket (campo "support_product")
    try:
        tickets_data = db.get_document("tickets_data") or {}
        channel_id = inter.channel.id
        # Percorre para encontrar o ticket pelo channel_id
        for uid, ticket_list in tickets_data.get("panels", {}).get(panel_id, {}).items():
            for ticket in ticket_list:
                if ticket.get("ticket_id") == channel_id and ticket.get("status") == "open":
                    ticket["support_product"] = {
                        "product_id": selected_product_id,
                        "product_name": product_name,
                    }
                    break
        db.update_document("tickets_data", tickets_data)
    except Exception as e:
        print(f"[ProductSupport] Erro ao salvar produto no ticket: {e}")

    # Edita a mensagem substituindo o select por texto confirmado
    mode = (db.get_document("custom_mode") or {}).get("mode", "components")
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")

    confirmed_text = (
        f"## {emoji.cardbox} Produto para Suporte\n"
        f"**{product_name}**\n"
        f"-# Selecionado por {inter.user.mention}"
    )

    if mode == "embed":
        embed = disnake.Embed(
            title=f"{emoji.cardbox} Produto para Suporte",
            description=f"**{product_name}**\n-# Selecionado por {inter.user.mention}",
            color=int(primary_color_hex.replace("#", ""), 16) if primary_color_hex else None,
        )
        await inter.response.edit_message(embed=embed, components=[])
    else:
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        await inter.response.edit_message(
            components=[
                disnake.ui.Container(
                    disnake.ui.TextDisplay(confirmed_text),
                    **container_kwargs,
                )
            ],
            flags=disnake.MessageFlags(is_components_v2=True),
        )
