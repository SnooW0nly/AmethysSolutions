import disnake
from disnake.ext import commands
import re
import time
from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms as perms_check
from modules.tickets.functions.history import log_ticket_event
from modules.tickets.utils import SafeFormatter
from modules.tickets.transcripts import generate_transcript
from modules.tickets.transcripts.donwload_transcript import send_transcript_to_dm
from functions.utils import utils
from functions.ai_api import chamar_ia

from modules.tickets.functions.setup_functions.close_ticket import close_ticket as close_ticket_func
from modules.tickets.functions.setup_functions.archive import archive_ticket as archive_ticket_func, unarchive_ticket as unarchive_ticket_func
from modules.tickets.functions.setup_functions.assume_ticket import assume_ticket as assume_ticket_func
from modules.tickets.functions.setup_functions.notify import notify as notify_func
from modules.tickets.functions.setup_functions.create_call import create_call as create_call_func
from modules.tickets.functions.setup_functions.resolved import resolved_ticket as resolved_ticket_func
from modules.tickets.functions.setup_functions.transfer import _execute_transfer, _find_ticket_owner
from modules.tickets.functions.info import ticket_info as ticket_info_func


async def get_ticket_context(inter: disnake.ApplicationCommandInteraction):
    tickets_data = db.get_document("tickets_data") or {}
    
    found_panel_id = None
    ticket_owner_id = None
    ticket_info = None

    for pid, users in tickets_data.get("panels", {}).items():
        if not isinstance(users, dict):
            continue
        for uid, tickets in users.items():
            for t in tickets:
                if t.get("ticket_id") == inter.channel.id:
                    found_panel_id = pid
                    ticket_owner_id = uid
                    ticket_info = t
                    break
            if found_panel_id:
                break
        if found_panel_id:
            break
    
    if not found_panel_id or not ticket_info:
        await inter.response.send_message(
            f"{emoji.wrong} Este comando só pode ser utilizado em um canal de ticket válido.",
            ephemeral=True
        )
        return None, None, None, None

    tickets_config = db.get_document("tickets_config") or {}
    panel_config = tickets_config.get("panels", {}).get(found_panel_id)
    if not panel_config:
        await inter.response.send_message(
            f"{emoji.wrong} A configuração para o painel deste ticket não foi encontrada.",
            ephemeral=True
        )
        return None, None, None, None
        
    return ticket_info, ticket_owner_id, found_panel_id, panel_config


async def check_attendant_permissions(inter: disnake.ApplicationCommandInteraction, panel_config: dict, ticket_info: dict | None = None):
    option_id = ticket_info.get("option_id") if ticket_info else None
    option_data = next((opt for opt in panel_config.get("options", []) if str(opt.get("id")) == str(option_id)), None) if option_id else None

    # Verificar se é admin do bot primeiro
    is_bot_admin = await perms_check.check(inter.author.id)
    if is_bot_admin:
        return True

    # Obter cargos do painel e da opção
    panel_roles = panel_config.get("roles", {})
    option_roles = option_data.get("roles", {}) if option_data else {}
    
    # Pegar cargos de atendentes do painel e da opção
    panel_atendente_roles = panel_roles.get("atendentes", [])
    option_atendente_roles = option_roles.get("atendentes", [])
    
    # Combinar ambos (prioridade para opção, mas aceita ambos)
    atendente_roles_ids = list(set(panel_atendente_roles + option_atendente_roles))
    
    if not atendente_roles_ids:
        await inter.response.send_message(
            f"{emoji.wrong} Não há cargos de atendente configurados para este ticket.",
            ephemeral=True
        )
        return False

    user_roles = [role.id for role in inter.author.roles]
    has_permission = any(role_id in user_roles for role_id in atendente_roles_ids)

    if not has_permission:
        await inter.response.send_message(
            f"{emoji.wrong} Você não tem permissão para usar este comando.",
            ephemeral=True
        )
        return False
    
    return True


class ConfirmCloseAllView(disnake.ui.View):
    def __init__(self, bot: commands.Bot, all_tickets: list, motivo: str, original_inter: disnake.ApplicationCommandInteraction):
        super().__init__(timeout=120)
        self.bot = bot
        self.all_tickets = all_tickets
        self.motivo = motivo
        self.original_inter = original_inter

    @disnake.ui.button(label="Confirmar Fechamento", emoji=emoji.correct, style=disnake.ButtonStyle.red, row=0)
    async def confirm_close(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.defer()
        
        # Fechar todos os tickets
        closed_count = 0
        failed_count = 0
        
        for ticket_info in self.all_tickets:
            try:
                channel = self.original_inter.guild.get_channel(ticket_info["ticket_id"])
                if not channel:
                    # Tentar buscar como thread
                    channel = self.original_inter.guild.get_thread(ticket_info["ticket_id"])
                
                if channel:
                    await close_ticket_func(
                        bot=self.bot,
                        channel=channel,
                        closed_by=self.original_inter.author,
                        reason=self.motivo or "Fechamento em massa",
                        inter=None  # Não passar inter para evitar múltiplas respostas
                    )
                    closed_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"Erro ao fechar ticket {ticket_info['ticket_id']}: {e}")
                failed_count += 1
        
        # Enviar resultado
        result_message = f"{emoji.correct} **Fechamento em massa concluído!**\n\n"
        result_message += f"{emoji.correct} Tickets fechados: **{closed_count}**\n"
        if failed_count > 0:
            result_message += f"{emoji.wrong} Falhas: **{failed_count}**\n"
        
        if self.motivo:
            result_message += f"\n**Motivo:** {self.motivo}"
        
        await inter.edit_original_message(content=result_message, view=None)
        
    @disnake.ui.button(label="Cancelar", emoji=emoji.delete, style=disnake.ButtonStyle.gray, row=0)
    async def cancel(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.edit_message(content=f"{emoji.wrong} Operação cancelada. Nenhum ticket foi fechado.", view=None)


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


class TicketCommands(commands.Cog):
    """Cog for ticket management commands."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.slash_command(
        name="ticket",
        guild_ids=[utils.obter_server_principal()]
    )
    async def ticket(self, inter: disnake.ApplicationCommandInteraction):
        """Parent command for ticket management."""
        pass

    @ticket.sub_command(name="fechar", description="Fecha o ticket atual.")
    async def fechar(
        self,
        inter: disnake.ApplicationCommandInteraction,
        motivo: str = commands.Param(None, description="O motivo para fechar o ticket.")
    ):
        """Closes the current ticket."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return
        
        await close_ticket_func(
            bot=self.bot,
            channel=inter.channel,
            closed_by=inter.author,
            reason=motivo,
            inter=inter
        )

    @ticket.sub_command(name="fechar_todos", description="Fecha todos os tickets abertos no servidor.")
    async def fechar_todos(
        self,
        inter: disnake.ApplicationCommandInteraction,
        motivo: str = commands.Param(None, description="O motivo para fechar todos os tickets.")
    ):
        """Closes all open tickets in the server."""
        # Verificar se é admin do bot
        is_bot_admin = await perms_check.check(inter.author.id)
        if not is_bot_admin:
            await inter.response.send_message(
                f"{emoji.wrong} Você não tem permissão para usar este comando. Apenas administradores do bot podem fechar todos os tickets.",
                ephemeral=True
            )
            return
        
        await inter.response.defer(ephemeral=True)
        
        tickets_data = db.get_document("tickets_data") or {}
        
        # Coletar todos os tickets abertos
        all_tickets = []
        for panel_id, users in tickets_data.get("panels", {}).items():
            if not isinstance(users, dict):
                continue
            for user_id, tickets in users.items():
                for ticket in tickets:
                    if ticket.get("status") != "closed":
                        all_tickets.append({
                            "ticket_id": ticket.get("ticket_id"),
                            "panel_id": panel_id,
                            "user_id": user_id,
                            "ticket_data": ticket
                        })
        
        if not all_tickets:
            await inter.followup.send(
                f"{emoji.wrong} Não há tickets abertos no servidor.",
                ephemeral=True
            )
            return
        
        # Mostrar confirmação com botões
        total_tickets = len(all_tickets)
        view = ConfirmCloseAllView(self.bot, all_tickets, motivo, inter)
        await inter.followup.send(
            f"{emoji.warn} **Atenção!** Você está prestes a fechar **{total_tickets} ticket(s)** aberto(s).\n\n"
            f"**Esta ação não pode ser desfeita!**\n\n"
            f"Clique em **Confirmar Fechamento** para prosseguir.",
            view=view,
            ephemeral=True
        )

    @ticket.sub_command(name="assumir", description="Assume o atendimento do ticket.")
    async def assumir(self, inter: disnake.ApplicationCommandInteraction):
        """Assumes the ticket."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        # The permission check is slightly different for assuming,
        # so we call the function which has its own checks.
        await assume_ticket_func(inter)

    @ticket.sub_command(name="notificar", description="Envia uma notificação para o criador do ticket ou para o atendente.")
    async def notificar(self, inter: disnake.ApplicationCommandInteraction):
        """Notifies the ticket owner or the assigned staff."""
        # The notify function has its own permission checks for both user and staff
        await notify_func(inter)

    @ticket.sub_command_group(name="arquivar", description="Arquiva ou desarquiva um ticket.")
    async def arquivar(self, inter: disnake.ApplicationCommandInteraction):
        pass

    @arquivar.sub_command(name="on", description="Arquiva o ticket.")
    async def arquivar_on(self, inter: disnake.ApplicationCommandInteraction):
        """Archives the ticket."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return
        
        await archive_ticket_func(inter)

    @arquivar.sub_command(name="off", description="Desarquiva o ticket.")
    async def arquivar_off(self, inter: disnake.ApplicationCommandInteraction):
        """Unarchives the ticket."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return
        
        await unarchive_ticket_func(inter)

    @ticket.sub_command(name="resolvido", description="Marca o ticket como resolvido.")
    async def resolvido(self, inter: disnake.ApplicationCommandInteraction):
        """Marks the ticket as resolved."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        # resolved_ticket_func has its own permission checks
        await resolved_ticket_func(inter)

    @ticket.sub_command(name="adicionar", description="Adiciona um membro ao ticket.")
    async def adicionar(
        self,
        inter: disnake.ApplicationCommandInteraction,
        membro: disnake.Member = commands.Param(description="O membro a ser adicionado.")
    ):
        """Adds a member to the ticket."""
        ticket_info, _, panel_id, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return

        await inter.response.defer(ephemeral=True)

        if isinstance(inter.channel, disnake.TextChannel):
            perms = inter.channel.permissions_for(membro)
            if perms.read_messages:
                await inter.followup.send(f"{membro.mention} já está neste ticket.", ephemeral=True)
                return
        
        try:
            if isinstance(inter.channel, disnake.TextChannel):
                await inter.channel.set_permissions(membro, read_messages=True, send_messages=True)
            elif isinstance(inter.channel, disnake.Thread):
                await inter.channel.add_user(membro)

            messages = panel_config.get("messages", {})
            
            message_template = messages.get("add_user_message", "{alvo_mention} foi adicionado a este ticket por {autor_mention}.")
            
            placeholders = SafeFormatter(
                alvo_mention=membro.mention,
                alvo_name=membro.name,
                autor_mention=inter.author.mention,
                autor_name=inter.author.name,
                channel_name=inter.channel.name,
                guild_name=inter.guild.name
            )
            formatted_message = message_template.format_map(placeholders)

            dm_message_template = messages.get("add_user_dm_message")
            if dm_message_template:
                dm_formatted_message = dm_message_template.format_map(placeholders)
                try:
                    await membro.send(dm_formatted_message)
                except disnake.Forbidden:
                    pass

            await inter.followup.send(f"{membro.mention} foi adicionado ao ticket.", ephemeral=True)
            await inter.channel.send(formatted_message)
            log_ticket_event(
                inter.channel.id,
                "add_user",
                inter.author.id,
                {"added_user_id": membro.id}
            )
        except Exception as e:
            await inter.followup.send(f"Ocorreu um erro ao tentar adicionar o usuário: {e}", ephemeral=True)

    @ticket.sub_command(name="remover", description="Remove um membro do ticket.")
    async def remover(
        self,
        inter: disnake.ApplicationCommandInteraction,
        membro: disnake.Member = commands.Param(description="O membro a ser removido.")
    ):
        """Removes a member from the ticket."""
        ticket_info, ticket_owner_id, panel_id, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return
        
        await inter.response.defer(ephemeral=True)

        is_in_ticket = False
        if isinstance(inter.channel, disnake.TextChannel):
            if inter.channel.permissions_for(membro).read_messages:
                is_in_ticket = True
        elif isinstance(inter.channel, disnake.Thread):
            if membro in inter.channel.members:
                 is_in_ticket = True

        if not is_in_ticket:
            return await inter.followup.send(f"{membro.mention} não está neste ticket.", ephemeral=True)

        if membro.id == inter.author.id:
            return await inter.followup.send("Você não pode remover a si mesmo.", ephemeral=True)
            
        if membro.id == self.bot.user.id:
            return await inter.followup.send("Eu não posso ser removido de um ticket.", ephemeral=True)
            
        if membro.id == int(ticket_owner_id):
            return await inter.followup.send("Você não pode remover o dono do ticket.", ephemeral=True)

        try:
            if isinstance(inter.channel, disnake.TextChannel):
                await inter.channel.set_permissions(membro, overwrite=None)
            elif isinstance(inter.channel, disnake.Thread):
                await inter.channel.remove_user(membro)
            
            log_ticket_event(
                inter.channel.id,
                "remove_user",
                inter.author.id,
                {"removed_user_id": membro.id}
            )

            messages = panel_config.get("messages", {})
            message_template = messages.get("remove_user_message", "{alvo_mention} foi removido deste ticket por {autor_mention}.")
            
            placeholders = SafeFormatter(
                alvo_mention=membro.mention,
                alvo_name=membro.name,
                autor_mention=inter.author.mention,
                autor_name=inter.author.name,
                channel_name=inter.channel.name,
                guild_name=inter.guild.name
            )
            formatted_message = message_template.format_map(placeholders)

            dm_message_template = messages.get("remove_user_dm_message")
            if dm_message_template:
                dm_formatted_message = dm_message_template.format_map(placeholders)
                try:
                    await membro.send(dm_formatted_message)
                except disnake.Forbidden:
                    pass

            await inter.followup.send(f"{membro.mention} foi removido do ticket com sucesso.", ephemeral=True)
            await inter.channel.send(formatted_message)
        except Exception as e:
            await inter.followup.send(f"Ocorreu um erro ao tentar remover o usuário: {e}", ephemeral=True)

    @ticket.sub_command(name="renomear", description="Renomeia o ticket.")
    async def renomear(
        self,
        inter: disnake.ApplicationCommandInteraction,
        novo_nome: str = commands.Param(description="O novo nome para o ticket.", max_length=100)
    ):
        """Renames the ticket."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return

        old_name = inter.channel.name
        try:
            await inter.channel.edit(name=novo_nome)
            
            log_ticket_event(
                inter.channel.id,
                "rename",
                inter.author.id,
                {"old_name": old_name, "new_name": novo_nome}
            )
            
            await inter.response.send_message(f"O nome do ticket foi alterado para `{novo_nome}`.", ephemeral=True)
        except Exception as e:
            await inter.response.send_message(f"Ocorreu um erro ao tentar renomear o ticket: {e}", ephemeral=True)

    @ticket.sub_command(name="prioridade", description="Define a prioridade do ticket.")
    async def prioridade(
        self,
        inter: disnake.ApplicationCommandInteraction,
        nivel: str = commands.Param(
            description="O nível de prioridade.",
            choices=[
                disnake.OptionChoice("Prioridade Normal", "normal"),
                disnake.OptionChoice("Prioridade Média", "medium"),
                disnake.OptionChoice("Prioridade Máxima", "high"),
            ]
        )
    ):
        """Sets the ticket's priority."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return

        await inter.response.defer(ephemeral=True)
        
        priority_map = {
            "normal": {"emoji": "🟢", "name": "Normal"},
            "medium": {"emoji": "🟠", "name": "Média"},
            "high": {"emoji": "🔴", "name": "Máxima"},
        }

        priority_emoji = priority_map[nivel]["emoji"]
        priority_name = priority_map[nivel]["name"]

        current_name = inter.channel.name
        cleaned_name = re.sub(r'^[🟢🟠🔴]┃', '', current_name)
        new_name = f"{priority_emoji}┃{cleaned_name}"

        ticket_info["priority"] = nivel
        
        # Manually find and update ticket in database
        tickets_data = db.get_document("tickets_data") or {}
        ticket_updated = False
        for panel_id, users in tickets_data.get("panels", {}).items():
            for user_id, tickets in users.items():
                for ticket in tickets:
                    if ticket.get("ticket_id") == inter.channel.id:
                        ticket["priority"] = nivel
                        ticket_updated = True
                        break
                if ticket_updated: break
            if ticket_updated: break

        if ticket_updated:
            db.save_document("tickets_data", tickets_data)

        try:
            await inter.channel.edit(name=new_name)
            await inter.followup.send(f"A prioridade do ticket foi definida como `{priority_name}`.", ephemeral=True)
            await inter.channel.send(f"{inter.author.mention} definiu a prioridade deste ticket como `{priority_name}`.")
            log_ticket_event(
                inter.channel.id, "set_priority", inter.author.id,
                {"priority": nivel}
            )
        except Exception as e:
            await inter.followup.send(f"Ocorreu um erro ao definir a prioridade: {e}", ephemeral=True)

    @ticket.sub_command(name="transferir", description="Transfere a posse do ticket para outro membro.")
    async def transferir(
        self,
        inter: disnake.ApplicationCommandInteraction,
        membro: disnake.Member = commands.Param(description="O novo dono do ticket.")
    ):
        """Transfers the ticket to another member."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return

        if membro.bot:
            await inter.response.send_message(f"{emoji.wrong} Você não pode transferir um ticket para um bot.", ephemeral=True)
            return

        old_owner_id = _find_ticket_owner(inter.channel.id)

        if not old_owner_id:
            await inter.response.send_message(f"{emoji.wrong} Não foi possível encontrar o dono original do ticket.", ephemeral=True)
            return

        if membro.id == old_owner_id:
            await inter.response.send_message(f"{emoji.wrong} O ticket já pertence a este membro.", ephemeral=True)
            return

        if membro not in inter.channel.members:
            try:
                if isinstance(inter.channel, disnake.Thread):
                    await inter.channel.add_user(membro)
                else:
                    await inter.channel.set_permissions(
                        membro,
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True
                    )
            except disnake.Forbidden:
                await inter.response.send_message(f"{emoji.wrong} Não tenho permissão para adicionar o membro a este canal.", ephemeral=True)
                return
        
        view = TransferConfirmView(self.bot, membro, old_owner_id)
        await inter.response.send_message(
            f"Você tem certeza que deseja transferir o ticket para {membro.mention}?\n"
            "Você também deseja remover o dono antigo do ticket?",
            view=view,
            ephemeral=True
        )

    @ticket.sub_command(name="transcript", description="Gera um transcript do ticket.")
    async def transcript(
        self,
        inter: disnake.ApplicationCommandInteraction,
        limite: int = commands.Param(None, description="Número máximo de mensagens a serem incluídas.")
    ):
        """Generates a transcript of the ticket."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return

        await inter.response.defer(ephemeral=True)

        try:
            transcript_file = await generate_transcript(inter.channel, self.bot, limit=limite)

            if not transcript_file:
                await inter.followup.send(f"{emoji.wrong} Não foi possível gerar o transcript.", ephemeral=True)
                return

            await send_transcript_to_dm(inter, transcript_file)

        except Exception as e:
            print(f"Ocorreu um erro ao gerar o transcript via comando: {e}")
            await inter.followup.send(f"{emoji.wrong} Desculpe, ocorreu um erro inesperado.", ephemeral=True)

    @ticket.sub_command(name="call", description="Gerencia a call de voz do ticket.")
    async def call(self, inter: disnake.ApplicationCommandInteraction):
        """Manages the voice call for the ticket."""
        ticket_info, _, _, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return

        await create_call_func(inter)

    @ticket.sub_command(name="info", description="Exibe informações sobre o ticket.")
    async def info(self, inter: disnake.ApplicationCommandInteraction):
        """Displays information about the ticket."""
        ticket_info, ticket_owner_id, panel_id, panel_config = await get_ticket_context(inter)
        if not ticket_info:
            return

        if not await check_attendant_permissions(inter, panel_config, ticket_info):
            return

        await ticket_info_func(inter)

    @commands.slash_command(
        name="ask",
        description="Pergunte algo para a IA do bot.",
        guild_ids=[utils.obter_server_principal()]
    )
    async def ask(
        self, 
        inter: disnake.ApplicationCommandInteraction,
        mensagem: str = commands.Param(description="Sua pergunta para a IA")
    ):
        """Pergunta algo para a IA do bot."""
        await inter.response.defer(ephemeral=True)
        
        try:
            resposta = await chamar_ia(mensagem, "AskCommand")
            
            # Truncar resposta se for muito longa
            if len(resposta) > 1900:
                resposta = resposta[:1900] + "..."
            
            await inter.followup.send(
                f"{emoji.information} **Resposta da IA:**\n\n{resposta}",
                ephemeral=True
            )
        except Exception as e:
            await inter.followup.send(
                f"{emoji.wrong} Erro ao consultar a IA: {str(e)}",
                ephemeral=True
            )


def setup(bot: commands.Bot):
    """Loads the TicketCommands cog."""
    bot.add_cog(TicketCommands(bot))
