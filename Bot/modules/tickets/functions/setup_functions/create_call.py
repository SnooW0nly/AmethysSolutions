import disnake
from functions.database import database as db
from functions.emoji import emoji
import traceback
from ...utils import SafeFormatter
from ..permissions import check_attendant_permissions

async def _create_and_announce_call(inter: disnake.MessageInteraction, ticket_info: dict, tickets_data: dict, panel_id: str, tickets_config: dict):
    """
    Helper function to create and announce a voice call for a ticket.
    Returns the new channel object on success, None on failure.
    """
    try:
        # Buscar a categoria do canal do painel
        panel_config = tickets_config.get("panels", {}).get(panel_id, {})
        category_id = panel_config.get("category_id")
        category = inter.guild.get_channel(category_id) if category_id else None

        if not category or not isinstance(category, disnake.CategoryChannel):
            await inter.followup.send("Categoria do painel não encontrada ou inválida.", ephemeral=True)
            return None

        # Permissões
        overwrites = {
            inter.guild.default_role: disnake.PermissionOverwrite(view_channel=False, connect=False)
        }
        
        ticket_owner = inter.guild.get_member(ticket_info["user_id"])
        if ticket_owner:
            overwrites[ticket_owner] = disnake.PermissionOverwrite(connect=True, speak=True, view_channel=True)
        else:
            # Se o dono do ticket não for encontrado, não crie a call
            await inter.followup.send("Não foi possível encontrar o dono do ticket no servidor.", ephemeral=True)
            return None

        for user_id in ticket_info.get("added_users", []):
            member = inter.guild.get_member(user_id)
            if member:
                overwrites[member] = disnake.PermissionOverwrite(connect=True, speak=True, view_channel=True)
        
        attendant_roles_ids = panel_config.get("roles", {}).get("atendentes", [])
        attendant_roles = [inter.guild.get_role(role_id) for role_id in attendant_roles_ids]
        for role in attendant_roles:
            if role:
                overwrites[role] = disnake.PermissionOverwrite(connect=True, speak=True, view_channel=True)
        
        # Nome do canal
        user_name = ticket_owner.name.lower().replace(" ", "-")
        channel_name = f"📞┃call-{user_name}"
        
        new_channel = await category.create_voice_channel(name=channel_name, overwrites=overwrites)
        invite = await new_channel.create_invite(max_age=0, max_uses=0, unique=True, reason=f"Convite de call para o ticket de {ticket_owner.display_name}")

        # Salvar no DB
        ticket_info["call_channel_id"] = new_channel.id
        db.save_document("tickets_data", tickets_data)

        messages = panel_config.get("messages", {})

        # --- Notificação na DM ---
        try:
            dm_template = messages.get("create_call_dm_message", "Olá! Uma call de voz foi criada para o seu ticket `{channel_name}`.")
            placeholders = SafeFormatter(
                channel_name=inter.channel.name,
                user_mention=ticket_owner.mention,
                user_name=ticket_owner.name,
                autor_mention=inter.author.mention,
                autor_name=inter.author.name,
                guild_name=inter.guild.name
            )
            dm_content = dm_template.format_map(placeholders)
            button = disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, disabled=True)
            await ticket_owner.send(f"{dm_content}\n**Convite:** {invite.url}", components=[button])
        except disnake.Forbidden:
            await inter.channel.send(f"{ticket_owner.mention}, não foi possível enviar o convite da call na sua DM.", delete_after=15)
        except Exception:
            traceback.print_exc()

        # --- Anúncio no Canal ---
        mentions = f"{ticket_owner.mention} " + " ".join([role.mention for role in attendant_roles if role])
        
        channel_template = messages.get("create_call_message", "Uma call de voz foi iniciada para este ticket por {autor_mention}.")
        placeholders = SafeFormatter(
            autor_mention=inter.author.mention,
            autor_name=inter.author.name,
            user_mention=ticket_owner.mention,
            user_name=ticket_owner.name,
            channel_name=inter.channel.name,
            guild_name=inter.guild.name
        )
        channel_announcement_content = channel_template.format_map(placeholders)
        
        await inter.channel.send(f"{mentions}\n{channel_announcement_content}\n- **Convite:** {invite.url}")
        
        return new_channel

    except Exception:
        traceback.print_exc()
        await inter.followup.send("Ocorreu um erro inesperado ao criar a call.", ephemeral=True)
        return None

class CallManagerView(disnake.ui.View):
    def __init__(self, bot, original_inter: disnake.MessageInteraction, ticket_info: dict, tickets_data: dict, guild_tickets_settings: dict, panel_id: str, tickets_config: dict):
        super().__init__(timeout=None)
        self.bot = bot
        self.original_inter = original_inter
        self.ticket_info = ticket_info
        self.tickets_data = tickets_data
        self.guild_tickets_settings = guild_tickets_settings
        self.panel_id = panel_id
        self.tickets_config = tickets_config
        self.update_buttons_state()

    def update_buttons_state(self):
        call_exists = self.ticket_info.get("call_channel_id") is not None
        self.create_call_button.disabled = call_exists
        self.delete_call_button.disabled = not call_exists

    async def interaction_check(self, inter: disnake.MessageInteraction) -> bool:
        if inter.author.id != self.original_inter.author.id:
            await inter.response.send_message("Apenas quem abriu este painel pode interagir com ele.", ephemeral=True)
            return False
        return True

    def _save_tickets_data(self):
        db.save_document("tickets_data", self.tickets_data)

    def _save_guild_tickets_settings(self):
        db.save_document("tickets_calls", self.guild_tickets_settings)
        
    async def update_panel(self, inter: disnake.MessageInteraction):
        call_channel_id = self.ticket_info.get("call_channel_id")
        call_channel = inter.guild.get_channel(call_channel_id) if call_channel_id else None
        
        description = f"**{emoji.arrow} Call Atual:** {call_channel.mention}" if call_channel else f"**{emoji.arrow} Call Atual:** Não criada"
        if not call_channel:
            if self.ticket_info.get("call_channel_id"):
                self.ticket_info.pop("call_channel_id", None)
                self._save_tickets_data()

        self.update_buttons_state()

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
                title=f"Gerenciador de Call",
                description=description,
                **embed_kwargs
            )
            await inter.edit_original_message(embed=embed, view=self)
        else:
            container_kwargs = {}
            if primary_color_hex:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except (ValueError, TypeError):
                    pass
            
            container = disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# **Gerenciador de Call**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(description),
                **container_kwargs
            )

            final_components = [container]
            final_components.extend(self.children)

            await inter.edit_original_message(
                content=None,
                embed=None,
                components=final_components
            )

    @disnake.ui.button(label="Criar call", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="ticket_create_new_call")
    async def create_call_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        new_channel = await _create_and_announce_call(
            inter=inter,
            ticket_info=self.ticket_info,
            tickets_data=self.tickets_data,
            panel_id=self.panel_id,
            tickets_config=self.tickets_config
        )
        if new_channel:
            await self.update_panel(inter)

    @disnake.ui.button(label="Apagar call", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="ticket_delete_call")
    async def delete_call_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()

        call_channel_id = self.ticket_info.get("call_channel_id")
        if not call_channel_id:
            await self.update_panel(inter)
            return
            
        call_channel = inter.guild.get_channel(call_channel_id)
        if call_channel:
            try:
                await call_channel.delete(reason=f"Call do ticket #{self.ticket_info.get('ticket_count', 'N/A')} apagada por {inter.author.mention}")
            except disnake.Forbidden:
                await inter.edit_original_message(content="Não tenho permissão para apagar o canal de call.", embed=None, view=None)
                return
            except disnake.NotFound:
                pass

        self.ticket_info.pop("call_channel_id", None)
        self._save_tickets_data()

        delete_content = f"{emoji.information} A call de voz deste ticket foi encerrada pelo atendente {inter.author.mention}."
        system_button = disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, disabled=True)
        await inter.channel.send(delete_content, components=[system_button])

        await self.update_panel(inter)


def find_ticket(tickets_data, channel_id):
    for panel_id, users in tickets_data.get("panels", {}).items():
        for user_id, tickets in users.items():
            for ticket in tickets:
                if ticket.get("ticket_id") == channel_id:
                    ticket['user_id'] = int(user_id)
                    return ticket, panel_id
    return None, None


async def approve_call_request(inter: disnake.MessageInteraction):
    await inter.response.defer()

    tickets_data = db.get_document("tickets_data") or {}
    ticket_info, panel_id = find_ticket(tickets_data, inter.channel.id)
    
    if not ticket_info:
        await inter.followup.send("Ticket não encontrado.", ephemeral=True)
        return

    try:
        tickets_config = db.get_document("tickets_config") or {}
    except FileNotFoundError:
        tickets_config = {}
        
    panel_config = tickets_config.get("panels", {}).get(panel_id, {})
    attendant_roles_ids = panel_config.get("roles", {}).get("atendentes", [])

    is_attendant = any(role.id in attendant_roles_ids for role in inter.author.roles)

    if not is_attendant and not inter.author.guild_permissions.administrator:
        await inter.followup.send("Apenas atendentes podem aprovar a criação de uma call.", ephemeral=True)
        return

    new_channel = await _create_and_announce_call(
        inter=inter,
        ticket_info=ticket_info,
        tickets_data=tickets_data,
        panel_id=panel_id,
        tickets_config=tickets_config
    )

    if new_channel:
        await inter.message.delete()

async def create_call(inter: disnake.MessageInteraction):
    # Verificar permissões
    has_permission = await check_attendant_permissions(inter.author, inter.channel.id)
    if not has_permission:
        return await inter.response.send_message(
            f"{emoji.wrong} Você não tem permissão para usar este comando.",
            ephemeral=True
        )
    
    tickets_data = db.get_document("tickets_data") or {}
    ticket_info, panel_id = find_ticket(tickets_data, inter.channel.id)

    if not ticket_info:
        return await inter.response.send_message(f"{emoji.bad} | Este ticket não foi encontrado no banco de dados.", ephemeral=True)

    try:
        tickets_config = db.get_document("tickets_config") or {}
    except FileNotFoundError:
        tickets_config = {}

    try:
        guild_tickets_settings = db.get_document("tickets_calls") or {}
    except FileNotFoundError:
        guild_tickets_settings = {}

    call_channel_id = ticket_info.get("call_channel_id")
    call_channel = inter.guild.get_channel(call_channel_id) if call_channel_id else None
    
    if not call_channel and call_channel_id:
        ticket_info.pop("call_channel_id", None)
        db.save_document("tickets_data", tickets_data)

    description = f"**{emoji.arrow} Call Atual:** {call_channel.mention}" if call_channel else f"**{emoji.arrow} Call Atual:** Não criada"

    mode = db.get_document("custom_mode").get("mode")
    primary_color_hex = db.get_document("custom_colors").get("primary")
    
    view = CallManagerView(
        bot=inter.bot, 
        original_inter=inter, 
        ticket_info=ticket_info,
        tickets_data=tickets_data,
        guild_tickets_settings=guild_tickets_settings,
        panel_id=panel_id,
        tickets_config=tickets_config
    )

    if mode == "embed":
        embed_kwargs = {}
        if primary_color_hex:
            try:
                embed_kwargs["color"] = disnake.Color(int(primary_color_hex.lstrip("#"), 16))
            except (ValueError, TypeError):
                pass
        
        embed = disnake.Embed(
            title=f"Gerenciador de Call",
            description=description,
            **embed_kwargs
        )
        await inter.response.send_message(embed=embed, view=view, ephemeral=True)
    else:
        container_kwargs = {}
        if primary_color_hex:
            try:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            except (ValueError, TypeError):
                pass
        
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(
                f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# **Gerenciador de Call**"
            ),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(description),
            **container_kwargs
        )
        
        final_components = [container]
        final_components.extend(view.children)

        await inter.response.send_message(
            components=final_components,
            ephemeral=True,
            flags=disnake.MessageFlags(is_components_v2=True)
        )
        message = await inter.original_response()
        inter.bot.add_view(view, message_id=message.id)
