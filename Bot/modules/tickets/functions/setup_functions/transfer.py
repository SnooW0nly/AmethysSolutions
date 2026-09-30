import disnake
from disnake.ui import UserSelect
from functions.database import database as db
from functions.emoji import emoji
from disnake.ext import commands
from functions.perms import perms
from functions.message import message
from modules.tickets.functions.history import log_ticket_event
from ...utils import SafeFormatter
from ..permissions import check_attendant_permissions

def _get_panel_data_by_channel(channel_id: int) -> dict:
    tickets_data = db.get_document("tickets_data") or {} or {}
    panel_id_found = None

    def find_panel_id_in(panels_dict):
        for panel_id, users in panels_dict.items():
            if not isinstance(users, dict):
                continue
            for uid, tickets in (users or {}).items():
                for t in (tickets or []):
                    if t.get("ticket_id") == channel_id and t.get("status") == "open":
                        return panel_id
        return None

    panel_id_found = find_panel_id_in(tickets_data.get("panels", {}))

    if not panel_id_found:
        top_level_panels = {
            k: v for k, v in tickets_data.items()
            if k not in ["panels", "ai_silenced"]
        }
        panel_id_found = find_panel_id_in(top_level_panels)

    if panel_id_found:
        config = db.get_document("tickets_config") or {} or {}
        return (config.get("panels") or {}).get(panel_id_found, {})
    
    return {}

def _find_ticket_owner(channel_id: int) -> int | None:
    tickets_data = db.get_document("tickets_data") or {} or {}
    
    def search_in(panels_dict):
        for panel_id, users in panels_dict.items():
            if not isinstance(users, dict): 
                continue
            for uid, tickets in (users or {}).items():
                for t in (tickets or []):
                    if t.get("ticket_id") == channel_id and t.get("status") == "open":
                        return int(uid)
        return None

    owner_id = search_in(tickets_data.get("panels", {}))
    if owner_id:
        return owner_id

    top_level_panels = {
        k: v for k, v in tickets_data.items()
        if k not in ["panels", "ai_silenced"]
    }
    owner_id = search_in(top_level_panels)
    return owner_id

async def _execute_transfer(inter: disnake.MessageInteraction, new_owner: disnake.Member, old_owner_id: int, remove_old_owner: bool):
    await inter.response.defer()

    tickets_data = db.get_document("tickets_data") or {} or {}
    old_owner_id_str = str(old_owner_id)
    new_owner_id_str = str(new_owner.id)
    ticket_found_and_moved = False

    def move_ticket_in_panel(panel):
        nonlocal ticket_found_and_moved
        if old_owner_id_str in panel:
            tickets = panel[old_owner_id_str]
            for i, t in enumerate(tickets):
                if t.get("ticket_id") == inter.channel.id:
                    ticket_to_move = tickets.pop(i)
                    if not tickets:
                        del panel[old_owner_id_str]
                    
                    if new_owner_id_str not in panel:
                        panel[new_owner_id_str] = []
                    panel[new_owner_id_str].append(ticket_to_move)

                    ticket_found_and_moved = True
                    return True
        return False

    panels_dict = tickets_data.get("panels", {})
    for panel_id, panel_data in panels_dict.items():
        if move_ticket_in_panel(panel_data):
            break
    
    if not ticket_found_and_moved:
        top_level_panels = {
            k: v for k, v in tickets_data.items()
            if k not in ["panels", "ai_silenced"]
        }
        for panel_id, panel_data in top_level_panels.items():
             if move_ticket_in_panel(panel_data):
                break

    if not ticket_found_and_moved:
        await inter.edit_original_response(
            content=f"{emoji.wrong} Ocorreu um erro ao encontrar os dados do ticket para transferência.",
            view=None
        )
        return
    
    db.save_document("tickets_data", tickets_data)
    
    log_ticket_event(
        channel_id=inter.channel.id,
        event_type="transfer",
        author_id=inter.author.id,
        details={
            "old_owner_id": old_owner_id,
            "new_owner_id": new_owner.id,
            "removed_old_owner": remove_old_owner
        }
    )

    old_owner_member = inter.guild.get_member(old_owner_id)

    if remove_old_owner and old_owner_member:
        try:
            if isinstance(inter.channel, disnake.Thread):
                await inter.channel.remove_user(old_owner_member)
            else:
                await inter.channel.set_permissions(old_owner_member, overwrite=None)
        except disnake.Forbidden:
            pass 
    
    jump_button = disnake.ui.Button(label="Ir para o Ticket", style=disnake.ButtonStyle.link, url=inter.channel.jump_url)

    try:
        message_new = f"O ticket `{inter.channel.name}` foi transferido para você por {inter.author.name}."
        await new_owner.send(message_new, components=[jump_button])
    except disnake.Forbidden:
        pass

    if old_owner_member:
        try:
            if inter.author.id != old_owner_id:
                message_old = f"O atendente {inter.author.name} transferiu seu ticket `{inter.channel.name}` para {new_owner.name}."
                if remove_old_owner:
                    message_old += "\nVocê foi removido do ticket."
                await old_owner_member.send(message_old, components=[jump_button])
        except disnake.Forbidden:
            pass
    
    panel_data = _get_panel_data_by_channel(inter.channel.id)
    messages = panel_data.get("messages", {})
    transfer_message_template = messages.get("transfer_message", "{autor_mention} transferiu o ticket de {old_owner_mention} para {new_owner_mention}.")

    placeholders = SafeFormatter(
        autor_mention=inter.author.mention,
        autor_name=inter.author.name,
        old_owner_mention=old_owner_member.mention if old_owner_member else "um usuário desconhecido",
        old_owner_name=old_owner_member.name if old_owner_member else "usuário desconhecido",
        new_owner_mention=new_owner.mention,
        new_owner_name=new_owner.name,
        channel_name=inter.channel.name,
        guild_name=inter.guild.name
    )
    transfer_message_content = transfer_message_template.format_map(placeholders)

    await inter.channel.send(transfer_message_content)
    await inter.edit_original_response(content=f"{emoji.correct} Ticket transferido com sucesso!", view=None)

class TransferConfirmView(disnake.ui.View):
    def __init__(self, bot: commands.Bot, new_owner: disnake.Member, old_owner_id: int):
        super().__init__(timeout=120)
        self.bot = bot
        self.new_owner = new_owner
        self.old_owner_id = old_owner_id

    @disnake.ui.button(label="Sim, transferir e remover", emoji=emoji.double_check, style=disnake.ButtonStyle.red, row=0)
    async def confirm_and_remove(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await _execute_transfer(inter, self.new_owner, self.old_owner_id, remove_old_owner=True)

    @disnake.ui.button(label="Apenas transferir", emoji=emoji.arrow, style=disnake.ButtonStyle.green, row=0)
    async def confirm_only(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await _execute_transfer(inter, self.new_owner, self.old_owner_id, remove_old_owner=False)
        
    @disnake.ui.button(label="Cancelar", emoji=emoji.delete, style=disnake.ButtonStyle.gray, row=1)
    async def cancel(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.edit_message(content=f"{emoji.wrong} Transferência cancelada.", view=None)

class TransferUserSelect(disnake.ui.UserSelect):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(
            placeholder="Selecione um membro para transferir o ticket",
            min_values=1,
            max_values=1
        )

    async def callback(self, inter: disnake.MessageInteraction):
        try:
            selected_user_id = int(inter.values[0])
            new_owner = await inter.guild.fetch_member(selected_user_id)
        except (ValueError, IndexError, disnake.NotFound):
            await inter.response.send_message(f"{emoji.wrong} Membro selecionado inválido ou não encontrado.", ephemeral=True)
            return

        if new_owner.bot:
            await inter.response.send_message(f"{emoji.wrong} Você não pode transferir um ticket para um bot.", ephemeral=True)
            return

        old_owner_id = _find_ticket_owner(inter.channel.id)

        if not old_owner_id:
            await inter.response.send_message(f"{emoji.wrong} Não foi possível encontrar o dono original do ticket.", ephemeral=True)
            return

        if new_owner.id == old_owner_id:
            await inter.response.send_message(f"{emoji.wrong} O ticket já pertence a este membro.", ephemeral=True)
            return

        if new_owner not in inter.channel.members:
            try:
                if isinstance(inter.channel, disnake.Thread):
                    await inter.channel.add_user(new_owner)
                else:
                    await inter.channel.set_permissions(
                        new_owner,
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True
                    )
            except disnake.Forbidden:
                await inter.response.send_message(f"{emoji.wrong} Não tenho permissão para adicionar o membro a este canal.", ephemeral=True)
                return
        
        view = TransferConfirmView(self.bot, new_owner, old_owner_id)
        await inter.response.edit_message(
            content=f"Você tem certeza que deseja transferir o ticket para {new_owner.mention}?\n"
                    "Você também deseja remover o dono antigo do ticket?",
            view=view
        )

class TransferView(disnake.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(TransferUserSelect(bot))

async def transfer_ticket(inter: disnake.MessageInteraction):
    # Verificar permissões usando sistema centralizado
    has_permission = await check_attendant_permissions(inter.author, inter.channel.id)
    
    # Também permitir que o dono do ticket transfira
    owner_id = _find_ticket_owner(inter.channel.id)
    is_owner = inter.author.id == owner_id
    
    if not has_permission and not is_owner:
        return await inter.response.send_message(
            f"{emoji.wrong} Você não tem permissão para transferir este ticket.",
            ephemeral=True
        )

    await inter.response.send_message(view=TransferView(inter.bot), ephemeral=True)
