import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms as perms_check
from ..history import log_ticket_event
from ...utils import SafeFormatter
from ..permissions import check_attendant_permissions, get_attendant_roles

class RemoveUserSelect(disnake.ui.UserSelect):
    def __init__(self, bot, channel: disnake.TextChannel | disnake.Thread):
        self.bot = bot
        self.channel = channel
        super().__init__(placeholder="Selecione um usuário para remover...", min_values=1, max_values=1)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer()
        member_to_remove = self.values[0]

        # Verifica se o membro está no ticket
        is_in_ticket = False
        if isinstance(self.channel, disnake.TextChannel):
            if self.channel.permissions_for(member_to_remove).read_messages:
                is_in_ticket = True
        elif isinstance(self.channel, disnake.Thread):
            try:
                thread_members = await self.channel.fetch_members()
                if member_to_remove.id in [tm.id for tm in thread_members]:
                    is_in_ticket = True
            except disnake.Forbidden:
                return await inter.edit_original_message(content="Não tenho permissão para buscar os membros deste tópico.", view=None)

        if not is_in_ticket:
            return await inter.edit_original_message(content=f"{member_to_remove.mention} não está neste ticket.", view=None)

        # Lógica de permissão para remoção
        if member_to_remove.id == inter.author.id:
            return await inter.edit_original_message(content="Você não pode remover a si mesmo.", view=None)
            
        if member_to_remove.id == self.bot.user.id:
            return await inter.edit_original_message(content="Eu não posso ser removido de um ticket.", view=None)

        config = db.get_document("tickets_config") or {}
        tickets_data = db.get_document("tickets_data") or {}

        found_panel_id, ticket_owner_id = None, None
        for panel_id, users in tickets_data.get("panels", {}).items():
            for uid, tickets in users.items():
                if any(t.get("ticket_id") == self.channel.id for t in tickets):
                    found_panel_id, ticket_owner_id = panel_id, uid
                    break
            if found_panel_id: break
        
        if not found_panel_id or not ticket_owner_id:
            return await inter.edit_original_message(content="Não foi possível encontrar os dados deste ticket.", view=None)
            
        if member_to_remove.id == int(ticket_owner_id):
            return await inter.edit_original_message(content="Você não pode remover o dono do ticket.", view=None)

        is_author_admin = await perms_check.check(inter.author.id)
        panel_data = config.get("panels", {}).get(found_panel_id, {})
        roles_data = panel_data.get("roles", {})
        atendentes_roles_ids = get_attendant_roles(roles_data)
        is_ticket_owner = inter.author.id == int(ticket_owner_id)

        if is_ticket_owner and not is_author_admin:
            member_to_remove_roles = [role.id for role in member_to_remove.roles]
            if any(role_id in atendentes_roles_ids for role_id in member_to_remove_roles):
                return await inter.edit_original_message(content="Você não pode remover um membro da equipe de atendimento.", view=None)

        try:
            if isinstance(self.channel, disnake.TextChannel):
                await self.channel.set_permissions(member_to_remove, overwrite=None)
            elif isinstance(self.channel, disnake.Thread):
                await self.channel.remove_user(member_to_remove)
            
            log_ticket_event(
                self.channel.id,
                "remove_user",
                inter.author.id,
                {"removed_user_id": member_to_remove.id}
            )

            messages = panel_data.get("messages", {})
            message_template = messages.get("remove_user_message", "{alvo_mention} foi removido deste ticket por {autor_mention}.")
            
            placeholders = SafeFormatter(
                alvo_mention=member_to_remove.mention,
                alvo_name=member_to_remove.name,
                autor_mention=inter.author.mention,
                autor_name=inter.author.name,
                channel_name=self.channel.name,
                guild_name=inter.guild.name
            )
            formatted_message = message_template.format_map(placeholders)

            dm_message_template = messages.get("remove_user_dm_message")
            if dm_message_template:
                dm_formatted_message = dm_message_template.format_map(placeholders)
                try:
                    await member_to_remove.send(dm_formatted_message)
                except disnake.Forbidden:
                    pass

            await inter.edit_original_message(content=f"{member_to_remove.mention} foi removido do ticket com sucesso.", view=None)
            await self.channel.send(formatted_message)
        except Exception as e:
            await inter.edit_original_message(content=f"Ocorreu um erro ao tentar remover o usuário: {e}", view=None)

class RemoveUserView(disnake.ui.View):
    def __init__(self, bot, channel):
        super().__init__(timeout=180)
        self.add_item(RemoveUserSelect(bot, channel))

async def remove_user(inter: disnake.MessageInteraction):
    # Verificar permissões
    has_permission = await check_attendant_permissions(inter.author, inter.channel.id)
    if not has_permission:
        return await inter.response.send_message(
            f"{emoji.wrong} Você não tem permissão para usar este comando.",
            ephemeral=True
        )
    
    await inter.response.send_message(
        "Selecione o usuário que você deseja remover deste ticket:",
        view=RemoveUserView(inter.bot, inter.channel),
        ephemeral=True
    )
