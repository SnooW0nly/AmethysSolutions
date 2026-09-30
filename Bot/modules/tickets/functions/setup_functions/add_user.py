import disnake
from functions.database import database as db
from functions.emoji import emoji
from ..history import log_ticket_event
from ...utils import SafeFormatter
from ..permissions import check_attendant_permissions

class AddUserSelect(disnake.ui.UserSelect):
    def __init__(self, channel: disnake.TextChannel | disnake.Thread):
        self.channel = channel
        super().__init__(placeholder="Selecione um usuário para adicionar...", min_values=1, max_values=1)

    async def callback(self, inter: disnake.MessageInteraction):
        await inter.response.defer()
        member_to_add = self.values[0]

        # Verifica se o membro já está no ticket
        if isinstance(self.channel, disnake.TextChannel):
            perms = self.channel.permissions_for(member_to_add)
            if perms.read_messages:
                await inter.edit_original_message(content=f"{member_to_add.mention} já está neste ticket.", view=None)
                return
        
        try:
            if isinstance(self.channel, disnake.TextChannel):
                await self.channel.set_permissions(member_to_add, read_messages=True, send_messages=True)
            elif isinstance(self.channel, disnake.Thread):
                await self.channel.add_user(member_to_add)

            config = db.get_document("tickets_config") or {}
            tickets_data = db.get_document("tickets_data") or {}
            
            panel_id = None
            for pid, users in tickets_data.get("panels", {}).items():
                for uid, tickets in users.items():
                    if any(t.get("ticket_id") == self.channel.id for t in tickets):
                        panel_id = pid
                        break
                if panel_id: break

            panel_data = config.get("panels", {}).get(panel_id, {})
            messages = panel_data.get("messages", {})
            
            message_template = messages.get("add_user_message", "{alvo_mention} foi adicionado a este ticket por {autor_mention}.")
            
            placeholders = SafeFormatter(
                alvo_mention=member_to_add.mention,
                alvo_name=member_to_add.name,
                autor_mention=inter.author.mention,
                autor_name=inter.author.name,
                channel_name=self.channel.name,
                guild_name=inter.guild.name
            )
            formatted_message = message_template.format_map(placeholders)

            dm_message_template = messages.get("add_user_dm_message")
            if dm_message_template:
                dm_formatted_message = dm_message_template.format_map(placeholders)
                try:
                    await member_to_add.send(dm_formatted_message)
                except disnake.Forbidden:
                    pass  # O usuário pode ter DMs desativadas

            await inter.edit_original_message(content=f"{member_to_add.mention} foi adicionado ao ticket.", view=None)
            await self.channel.send(formatted_message)
            log_ticket_event(
                self.channel.id,
                "add_user",
                inter.author.id,
                {"added_user_id": member_to_add.id}
            )
        except Exception as e:
            await inter.edit_original_message(content=f"Ocorreu um erro ao tentar adicionar o usuário: {e}", view=None)

class AddUserView(disnake.ui.View):
    def __init__(self, channel: disnake.TextChannel | disnake.Thread):
        super().__init__(timeout=180)
        self.add_item(AddUserSelect(channel))
        
async def add_user(inter: disnake.MessageInteraction):
    # Verificar permissões
    has_permission = await check_attendant_permissions(inter.author, inter.channel.id)
    if not has_permission:
        return await inter.response.send_message(
            f"{emoji.wrong} Você não tem permissão para usar este comando.",
            ephemeral=True
        )
    
    await inter.response.send_message(
        "Selecione o usuário que você deseja adicionar a este ticket:",
        view=AddUserView(inter.channel),
        ephemeral=True
    )
