import disnake
from functions.database import database as db
from functions.emoji import emoji
from modules.tickets.functions.setup_functions.create_call import find_ticket
from ...utils import SafeFormatter

class ApproveCallView(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Criar Call", style=disnake.ButtonStyle.green, custom_id="ticket_approve_call_request")
    async def approve_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        # A lógica será tratada no cog/listener principal para ter acesso a mais contexto.
        pass

async def request_call(inter: disnake.MessageInteraction):
    await inter.response.defer(ephemeral=True)

    tickets_data = db.get_document("tickets_data") or {}
    ticket_info, panel_id = find_ticket(tickets_data, inter.channel.id)

    if not ticket_info:
        return await inter.followup.send(f"{emoji.bad} | Não foi possível encontrar os dados deste ticket.", ephemeral=True)

    if ticket_info.get("call_requested"):
        return await inter.followup.send(f"{emoji.warn} | Você já solicitou a criação de uma call para este ticket.", ephemeral=True)

    ticket_info["call_requested"] = True
    db.save_document("tickets_data", tickets_data)
    
    view = ApproveCallView()

    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id, {})
    messages = panel_data.get("messages", {})
    message_template = messages.get("request_call_message", "{emoji.voice} | O usuário {autor_mention} solicitou a criação de uma call.")

    placeholders = SafeFormatter(
        autor_mention=inter.author.mention,
        autor_name=inter.author.name,
        emoji=emoji,
        user_mention=inter.author.mention,
        user_name=inter.author.name,
        channel_name=inter.channel.name,
        guild_name=inter.guild.name,
    )
    formatted_message = message_template.format_map(placeholders)
    
    await inter.channel.send(formatted_message, view=view)
    await inter.followup.send("Sua solicitação de call foi enviada para os atendentes.", ephemeral=True)
