import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms as perms_check
from ..permissions import check_attendant_permissions

class UserHistorySelect(disnake.ui.UserSelect):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(placeholder="Selecione um usuário para ver o histórico...", min_values=1, max_values=1)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)
        
        member = self.values[0]
        if not isinstance(member, disnake.Member):
            member = await inter.guild.get_or_fetch_member(member.id)

        if not member:
            return await inter.edit_original_message(content="Membro não encontrado.", view=None)
        
        user_id = member.id

        tickets_data = db.get_document("tickets_data") or {}
        user_tickets = []

        def collect_tickets(panels_dict):
            for panel_id, users in panels_dict.items():
                if not isinstance(users, dict): continue
                if str(user_id) in users:
                    user_tickets.extend(users[str(user_id)])

        collect_tickets(tickets_data.get("panels", {}))
        
        top_level_panels = {
            k: v for k, v in tickets_data.items()
            if k not in ["panels", "ai_silenced"]
        }
        collect_tickets(top_level_panels)

        total_tickets = len(user_tickets)
        closed_tickets = 0
        calls_requested = 0
        assumed_tickets = 0
        priorities = {"high": 0, "medium": 0, "low": 0}
        reminders_to_user = 0
        reminders_to_staff = 0
        resolved_tickets = 0
        history_events = []

        for ticket in user_tickets:
            if ticket.get("status") == "closed":
                closed_tickets += 1

            if ticket.get("is_resolved"):
                resolved_tickets += 1

            if ticket.get("call_requested"):
                calls_requested += 1
            if "assumed_by" in ticket:
                assumed_tickets += 1
            
            priority = ticket.get("priority")
            if priority in priorities:
                priorities[priority] += 1

            if "history" in ticket:
                history_events.extend(ticket["history"])
                for event in ticket["history"]:
                    if event.get("type") == "notify":
                        details = event.get("details", {})
                        if details.get("direction") == "staff_to_user" and details.get("notified_user_id") == user_id:
                            reminders_to_user += 1
                        elif details.get("direction") == "user_to_staff" and event.get("author_id") == user_id:
                            reminders_to_staff += 1
        
        high_prio = priorities["high"]
        medium_prio = priorities["medium"]
        low_prio = priorities["low"]
        
        last_ticket = max(user_tickets, key=lambda t: t.get("created_at", 0), default=None)
        
        last_ticket_display = None
        if last_ticket:
            last_ticket_channel = self.bot.get_channel(last_ticket['ticket_id'])
            if last_ticket_channel:
                last_ticket_display = f"`{last_ticket_channel.name}`"
            elif last_ticket.get('channel_name'):
                last_ticket_display = f"`{last_ticket.get('channel_name')}`"
            else:
                last_ticket_display = f"ID: `{last_ticket['ticket_id']}`"

        history_events.sort(key=lambda e: e.get("timestamp", 0), reverse=True)

        history_str = ""
        if not history_events:
            history_str = "Nenhum evento registrado."
        else:
            for event in history_events[:5]:
                event_type = event.get("type", "desconhecido")
                author_id = event.get("author_id")
                timestamp = event.get("timestamp")
                details = event.get("details", {})
                
                author_mention = f"<@{author_id}>"
                time_str = f"<t:{timestamp}:R>"
                
                description = f"{author_mention} {time_str}"
                
                if event_type == "create":
                    description += " criou o ticket."
                elif event_type == "close":
                    reason = details.get("reason")
                    description += " fechou o ticket."
                    if reason:
                        description += f" Motivo: *{reason}*"
                elif event_type == "add_user":
                    added_user = f"<@{details.get('added_user_id', '???')}>"
                    description += f" adicionou {added_user}."
                elif event_type == "remove_user":
                    removed_user = f"<@{details.get('removed_user_id', '???')}>"
                    description += f" removeu {removed_user}."
                elif event_type == "assume":
                    description += " assumiu o ticket."
                elif event_type == "rename":
                    description += f" renomeou o ticket para `{details.get('new_name', '???')}`."
                elif event_type == "set_priority":
                    prio = details.get('priority', '???')
                    description += f" definiu a prioridade como `{prio}`."
                elif event_type == "notify":
                    if details.get('direction') == 'user_to_staff':
                        description += " notificou a equipe."
                    else:
                        description += " notificou o usuário."
                elif event_type == "transfer":
                    old_owner = f"<@{details.get('old_owner_id', '???')}>"
                    new_owner = f"<@{details.get('new_owner_id', '???')}>"
                    description += f" transferiu o ticket de {old_owner} para {new_owner}."
                    if details.get('removed_old_owner'):
                        description += " (Dono antigo removido)"
                elif event_type == "resolved":
                    description += f" marcou o ticket como resolvido e o renomeou para `{details.get('new_name', '???')}`."
                
                history_str += f"{emoji.arrow} {description}\n"

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
                title=f"Histórico de Tickets de {member.display_name}",
                **embed_kwargs
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            if last_ticket_display:
                embed.add_field(name="Último Ticket", value=last_ticket_display, inline=True)
            embed.add_field(name="Total de Tickets", value=f"`{total_tickets}`", inline=True)
            embed.add_field(name="Tickets Fechados", value=f"`{closed_tickets}`", inline=True)
            
            embed.add_field(name="Notificou a Equipe", value=f"`{reminders_to_staff}`", inline=True)
            embed.add_field(name="Foi Notificado", value=f"`{reminders_to_user}`", inline=True)
            embed.add_field(name="Calls Solicitadas", value=f"`{calls_requested}`", inline=True)
            
            embed.add_field(name="Tickets Assumidos", value=f"`{assumed_tickets}`", inline=True)
            embed.add_field(
                name="Prioridades (Máx/Méd/Nor)",
                value=f"`{high_prio}`/`{medium_prio}`/`{low_prio}`",
                inline=True
            )
            embed.add_field(name="Tickets Resolvidos", value=f"`{resolved_tickets}`", inline=True)
            embed.add_field(name="\u200b", value="\u200b", inline=True)

            if history_str:
                embed.add_field(name=f"{emoji.clock} Últimas Ações:", value=history_str, inline=False)

            await inter.edit_original_message(embed=embed, components=[])
        
        else:
            last_ticket_str = f"{emoji.ticket} **Último Ticket:** {last_ticket_display}\n" if last_ticket_display else ""

            info_content = (
                f"{last_ticket_str}"
                f"{emoji.ticket} **Total de Tickets Abertos:** `{total_tickets}`\n"
                f"{emoji.delete} **Tickets Fechados:** `{closed_tickets}`\n"
                f"{emoji.double_check} **Tickets Resolvidos:** `{resolved_tickets}`\n"
                f"{emoji.warn} **Vezes que foi Notificado:** `{reminders_to_user}`\n"
                f"{emoji.warn} **Vezes que Notificou a Equipe:** `{reminders_to_staff}`\n"
                f"{emoji.voice} **Calls Solicitadas:** `{calls_requested}`\n"
                f"{emoji.shield_star} **Tickets Assumidos por Atendentes:** `{assumed_tickets}`\n"
                f"{emoji.coupon} **Tickets por Prioridade (Máx/Méd/Nor):** `{high_prio}`/`{medium_prio}`/`{low_prio}`"
            )

            history_container_item = disnake.ui.TextDisplay(f"### {emoji.clock} Últimas Ações:\n{history_str}") if history_str else None

            container_kwargs = {}
            if primary_color_hex:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except (ValueError, TypeError):
                    pass
            
            main_items = [
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# **Histórico de Tickets de {member.display_name}**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(info_content),
            ]
            if history_container_item:
                main_items.append(disnake.ui.Separator())
                main_items.append(history_container_item)

            container = disnake.ui.Container(
                *main_items,
                **container_kwargs
            )
            
            await inter.followup.send(
                ephemeral=True,
                components=[container],
                flags=disnake.MessageFlags(is_components_v2=True)
            )


class HistoryView(disnake.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=180)
        self.add_item(UserHistorySelect(bot))

async def show_history(inter: disnake.MessageInteraction):
    # Verificar permissões
    has_permission = await check_attendant_permissions(inter.author, inter.channel.id)
    if not has_permission:
        return await inter.response.send_message(
            f"{emoji.wrong} Você não tem permissão para usar este comando.",
            ephemeral=True
        )

    await inter.response.send_message(
        "Selecione o usuário que você deseja visualizar o histórico de tickets:",
        view=HistoryView(inter.bot),
        ephemeral=True
    )
