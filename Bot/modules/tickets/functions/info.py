import disnake
from functions.database import database as db
from functions.emoji import emoji

async def ticket_info(inter: disnake.MessageInteraction):
    await inter.response.defer(ephemeral=True)

    channel = inter.channel
    tickets_data = db.get_document("tickets_data") or {}

    ticket_info_dict = None
    ticket_owner_id = None

    for panel_id, users in tickets_data.get("panels", {}).items():
        for user_id, tickets in users.items():
            for ticket in tickets:
                if ticket.get("ticket_id") == channel.id:
                    ticket_info_dict = ticket
                    ticket_owner_id = user_id
                    break
            if ticket_info_dict:
                break
        if ticket_info_dict:
            break
            
    if not ticket_info_dict or not ticket_owner_id:
        return await inter.followup.send("Não foi possível encontrar os dados deste ticket.", ephemeral=True)

    ticket_owner = inter.guild.get_member(int(ticket_owner_id))
    owner_str = ticket_owner.mention if ticket_owner else "Usuário não encontrado"

    created_at = ticket_info_dict.get("created_at")
    created_at_str = f"<t:{created_at}:f>" if created_at else "Não registrada"

    assumed_by_id = ticket_info_dict.get("assumed_by")
    assumed_by_str = "`Ninguém`"
    if assumed_by_id:
        assignee = inter.guild.get_member(assumed_by_id)
        if assignee:
            assumed_by_str = assignee.mention

    priority_level = ticket_info_dict.get("priority")
    priority_map = {
        "normal": "🟢 Normal",
        "medium": "🟠 Média",
        "high": "🔴 Máxima",
    }
    priority_str = priority_map.get(priority_level, "Não definida")

    mode = db.get_document("custom_mode").get("mode")
    primary_color_hex = db.get_document("custom_colors").get("primary")

    if mode == "embed":
        embed_kwargs = {}
        if primary_color_hex:
            try:
                embed_kwargs["color"] = disnake.Color(int(primary_color_hex.lstrip("#"), 16))
            except (ValueError, TypeError):
                pass
        
        embed = disnake.Embed(
            title=f"Informações do Ticket",
            **embed_kwargs
        )
        embed.add_field(name=f"{emoji.member} Dono do ticket", value=owner_str, inline=False)
        embed.add_field(name=f"{emoji.clock} Data de abertura", value=created_at_str, inline=False)
        embed.add_field(name=f"{emoji.shield_star} Staff que assumiu", value=assumed_by_str, inline=False)
        embed.add_field(name=f"{emoji.coupon} Prioridade", value=f"`{priority_str}`", inline=False)

        await inter.followup.send(embed=embed, ephemeral=True)
    
    else:
        info_content = (
            f"**{emoji.member} Dono do ticket:** {owner_str}\n"
            f"**{emoji.clock} Data de abertura:** {created_at_str}\n"
            f"**{emoji.shield_star} Staff que assumiu:** {assumed_by_str}\n"
            f"**{emoji.coupon} Prioridade:** `{priority_str}`"
        )

        container_kwargs = {}
        if primary_color_hex:
            try:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            except (ValueError, TypeError):
                pass
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# **Informações do Ticket**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(info_content),
            **container_kwargs
        )
        
        await inter.followup.send(
            components=[container],
            ephemeral=True,
            flags=disnake.MessageFlags(is_components_v2=True)
        )
