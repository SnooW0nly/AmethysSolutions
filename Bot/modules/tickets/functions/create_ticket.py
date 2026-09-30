import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.message import embed_message
from .open_ticket import open_ticket, TicketFormModal
from functions.emoji import emoji


async def _initiate_ticket_creation(inter: disnake.Interaction, bot: commands.Bot, panel_id: str, option_data: dict = None):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id)
    if not panel_data:
        if inter.response.is_done():
            return await embed_message.error(inter, "Painel de ticket não encontrado.", followup=True)
        else:
            return await embed_message.error(inter, "Painel de ticket não encontrado.", send=True)

    questions = None
    if option_data:
        option_id = str(option_data.get("id"))
        questions = panel_data.get("forms", {}).get(option_id, [])

    if questions:
        # Se tem formulário, abrir modal diretamente (verificação será feita no callback do modal)
        if not inter.response.is_done():
            modal = TicketFormModal(inter, bot, panel_data, panel_id, questions, option_data)
            await inter.response.send_modal(modal)
        else:
            # Se já foi defer, usar botão intermediário
            await inter.followup.send(
                ephemeral=True,
                components=[disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Abrir Formulário",
                        style=disnake.ButtonStyle.grey,
                        custom_id=f"ticket_form_open:{panel_id}:{option_id}"
                    )
                )]
            )
    else:
        # Para tickets sem formulário, verificar antes de criar o ticket
        try:
            from modules.cloud.verification_check import is_verification_required, send_verification_required_message, is_user_verified
            
            if is_verification_required():
                # Verificar se o usuário está verificado na database antes de criar o ticket
                if isinstance(inter.user, disnake.Member):
                    member = inter.user
                elif inter.guild:
                    member = inter.guild.get_member(inter.user.id)
                else:
                    member = None
                
                if member:
                    # Fazer defer para não expirar a interação durante verificação async
                    if not inter.response.is_done():
                        await inter.response.defer(ephemeral=True)
                    
                    # Fazer a verificação
                    verified = await is_user_verified(member)
                    
                    if not verified:
                        # Se não estiver verificado, enviar mensagem de verificação
                        await send_verification_required_message(inter)
                        # Resetar o painel para remover valores selecionados dos selects
                        try:
                            from .open_ticket import reset_panel_message
                            if isinstance(inter, disnake.MessageInteraction) and hasattr(inter, 'message') and inter.message:
                                await reset_panel_message(inter, panel_data, panel_id)
                            elif hasattr(inter, 'channel') and inter.channel and inter.guild:
                                # Buscar mensagens recentes do bot no canal que contenham o painel
                                try:
                                    async for msg in inter.channel.history(limit=20):
                                        if msg.author == inter.guild.me and msg.components:
                                            # Verificar se é a mensagem do painel procurando pelos custom_ids
                                            is_panel = False
                                            for component in msg.components:
                                                if isinstance(component, disnake.ui.ActionRow):
                                                    for item in component.children:
                                                        if hasattr(item, 'custom_id'):
                                                            custom_id = item.custom_id
                                                            if custom_id == f"create_ticket_{panel_id}" or custom_id == f"ticket_panel_option_select_{panel_id}":
                                                                is_panel = True
                                                                break
                                                    if is_panel:
                                                        break
                                            if is_panel:
                                                # Criar objeto fake com message para resetar
                                                class FakeInter:
                                                    def __init__(self, msg, guild):
                                                        self.message = msg
                                                        self.guild = guild
                                                
                                                fake_inter = FakeInter(msg, inter.guild)
                                                await reset_panel_message(fake_inter, panel_data, panel_id)
                                                break
                                except Exception as search_error:
                                    print(f"Erro ao buscar mensagem do painel: {search_error}")
                        except Exception as e:
                            print(f"Erro ao resetar painel após mostrar mensagem de verificação: {e}")
                        return
        except Exception as e:
            # Se houver erro na verificação, continuar normalmente (não bloquear)
            print(f"Erro ao verificar verificação OAuth2: {e}")
        
        # Se chegou aqui, usuário está verificado ou não precisa verificar
        # Garantir que a interação foi respondida antes de continuar (pode já ter sido deferida pelo caller)
        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)
        loading_message = await embed_message.wait(inter, followup=True, ephemeral=True)
        try:
            await open_ticket(inter, bot, panel_data, panel_id, option_data, loading_message)
        except (disnake.HTTPException, ValueError) as e:
            # Verificar se é erro de limite de canais
            error_message = str(e)
            if "Limite de canais exedido" in error_message or ("maximum" in error_message.lower() and "channel" in error_message.lower()):
                error_msg = f"{emoji.wrong} Limite de canais exedido na categoria, contate com administrador."
            else:
                error_msg = f"{emoji.wrong} Ocorreu um erro ao criar o ticket: {e}"
            
            # Tentar editar a mensagem de loading ou a mensagem original
            try:
                if loading_message:
                    await loading_message.edit(content=error_msg)
                else:
                    await inter.edit_original_message(content=error_msg)
            except:
                try:
                    await inter.followup.send(content=error_msg, ephemeral=True)
                except:
                    pass
            # Resetar o painel quando erro ocorrer
            if isinstance(inter, disnake.MessageInteraction) and hasattr(inter, 'message') and inter.message:
                try:
                    from .open_ticket import reset_panel_message
                    await reset_panel_message(inter, panel_data, panel_id)
                except Exception as reset_error:
                    print(f"Erro ao resetar painel após erro: {reset_error}")

async def create_ticket_handler(inter: disnake.MessageInteraction, bot, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}).get(panel_id)
    options = panel_data.get("options", [])
    option_data = options[0] if len(options) == 1 else None
    await _initiate_ticket_creation(inter, bot, panel_id, option_data)

async def check_and_create_ticket(inter: disnake.Interaction, bot: commands.Bot, panel_id: str, option_data: dict):
    await _initiate_ticket_creation(inter, bot, panel_id, option_data)
