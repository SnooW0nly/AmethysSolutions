import disnake
import aiohttp
import io
import re
import time
import asyncio

from functions.emoji import emoji
from disnake.ext import commands
from functions.database import database as db
from functions.message import embed_message
from .ticket_checks import check_office_hours, check_permissions, check_existing_ticket
from modules.tickets.config.container_utils import ContainerUtils
from .logs_tickets import log_ticket_creation
from functions.utils import utils
from .permissions import get_attendant_roles

# ========== IMPORTS ADICIONADOS PELO PATCH ==========
from . import ticket_index
from . import ticket_locks
from . import tickets_data_cache
# ====================================================


class TicketFormModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.Interaction, bot: commands.Bot, panel_data: dict, panel_id: str, questions: list, option_data: dict = None):
        self.inter = inter
        self.bot = bot
        self.panel_data = panel_data
        self.panel_id = panel_id
        self.option_data = option_data
        self.questions = questions

        components = []
        for question in questions:
            style = disnake.TextInputStyle.paragraph if question.get("style") == "paragraph" else disnake.TextInputStyle.short
            components.append(
                disnake.ui.TextInput(
                    label=question["label"],
                    custom_id=question["id"],
                    style=style,
                    placeholder=question.get("placeholder"),
                    required=question.get("required", True),
                    max_length=500
                )
            )

        super().__init__(title="Responda para Abrir o Ticket", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        # Garantir que emoji está disponível
        from functions.emoji import emoji
        
        # Fazer defer imediatamente para não expirar a interação durante verificações async
        if not inter.response.is_done():
            await inter.response.defer(ephemeral=True)
        
        # Mostrar mensagem de carregamento enquanto verifica
        loading_msg = await inter.followup.send(f"{emoji.loading} Verificando informações...", ephemeral=True)
        
        # Verificações LENTAS (OAuth2, horário, permissões, ticket existente)
        try:
            # Verificar se a verificação OAuth2 é obrigatória
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
                    verified = await is_user_verified(member)
                    if not verified:
                        # Deletar mensagem de loading e enviar mensagem de verificação
                        try:
                            await loading_msg.delete()
                        except:
                            pass
                        await send_verification_required_message(inter)
                        # Resetar o painel para remover valores selecionados dos selects
                        try:
                            if isinstance(self.inter, disnake.MessageInteraction) and hasattr(self.inter, 'message') and self.inter.message:
                                await reset_panel_message(self.inter, self.panel_data, self.panel_id)
                            elif hasattr(inter, 'channel') and inter.channel and inter.guild:
                                # Buscar mensagens recentes do bot no canal que contenham o painel
                                async for msg in inter.channel.history(limit=20):
                                    if msg.author == inter.guild.me and msg.components:
                                        # Verificar se é a mensagem do painel procurando pelos custom_ids
                                        is_panel = False
                                        for component in msg.components:
                                            if isinstance(component, disnake.ui.ActionRow):
                                                for item in component.children:
                                                    if hasattr(item, 'custom_id'):
                                                        custom_id = item.custom_id
                                                        if custom_id == f"create_ticket_{self.panel_id}" or custom_id == f"ticket_panel_option_select_{self.panel_id}":
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
                                            await reset_panel_message(fake_inter, self.panel_data, self.panel_id)
                                            break
                        except Exception as e:
                            print(f"Erro ao resetar painel após mostrar mensagem de verificação no modal: {e}")
                        return
        except Exception as e:
            # Se houver erro na verificação, continuar normalmente (não bloquear)
            import traceback
            print(f"Erro ao verificar verificação OAuth2 no modal: {e}")
            traceback.print_exc()
        
        form_answers = {q["id"]: inter.text_values[q["id"]] for q in self.questions}
        
        # Verificações de horário, permissões e ticket existente
        ok, error_msg = await check_office_hours(inter, self.panel_data)
        if not ok:
            await loading_msg.edit(content=error_msg)
            # Resetar o painel quando verificação falhar
            try:
                if isinstance(self.inter, disnake.MessageInteraction) and hasattr(self.inter, 'message') and self.inter.message:
                    await reset_panel_message(self.inter, self.panel_data, self.panel_id)
                elif hasattr(inter, 'channel') and inter.channel and inter.guild:
                    # Buscar mensagens recentes do bot no canal que contenham o painel
                    async for msg in inter.channel.history(limit=20):
                        if msg.author == inter.guild.me and msg.components:
                            # Verificar se é a mensagem do painel procurando pelos custom_ids
                            is_panel = False
                            for component in msg.components:
                                if isinstance(component, disnake.ui.ActionRow):
                                    for item in component.children:
                                        if hasattr(item, 'custom_id'):
                                            custom_id = item.custom_id
                                            if custom_id == f"create_ticket_{self.panel_id}" or custom_id == f"ticket_panel_option_select_{self.panel_id}":
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
                                await reset_panel_message(fake_inter, self.panel_data, self.panel_id)
                                break
            except Exception as e:
                print(f"Erro ao resetar painel após falha em verificação: {e}")
            return

        ok, error_msg = await check_permissions(inter, self.panel_data, self.option_data)
        if not ok:
            await loading_msg.edit(content=error_msg)
            # Resetar o painel quando verificação falhar
            try:
                if isinstance(self.inter, disnake.MessageInteraction) and hasattr(self.inter, 'message') and self.inter.message:
                    await reset_panel_message(self.inter, self.panel_data, self.panel_id)
                elif hasattr(inter, 'channel') and inter.channel and inter.guild:
                    # Buscar mensagens recentes do bot no canal que contenham o painel
                    async for msg in inter.channel.history(limit=20):
                        if msg.author == inter.guild.me and msg.components:
                            # Verificar se é a mensagem do painel procurando pelos custom_ids
                            is_panel = False
                            for component in msg.components:
                                if isinstance(component, disnake.ui.ActionRow):
                                    for item in component.children:
                                        if hasattr(item, 'custom_id'):
                                            custom_id = item.custom_id
                                            if custom_id == f"create_ticket_{self.panel_id}" or custom_id == f"ticket_panel_option_select_{self.panel_id}":
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
                                await reset_panel_message(fake_inter, self.panel_data, self.panel_id)
                                break
            except Exception as e:
                print(f"Erro ao resetar painel após falha em verificação: {e}")
            return

        ok, error_msg = await check_existing_ticket(inter, self.bot, self.panel_id)
        if not ok:
            await loading_msg.edit(content=error_msg)
            # Resetar o painel quando verificação falhar
            try:
                if isinstance(self.inter, disnake.MessageInteraction) and hasattr(self.inter, 'message') and self.inter.message:
                    await reset_panel_message(self.inter, self.panel_data, self.panel_id)
                elif hasattr(inter, 'channel') and inter.channel and inter.guild:
                    # Buscar mensagens recentes do bot no canal que contenham o painel
                    async for msg in inter.channel.history(limit=20):
                        if msg.author == inter.guild.me and msg.components:
                            # Verificar se é a mensagem do painel procurando pelos custom_ids
                            is_panel = False
                            for component in msg.components:
                                if isinstance(component, disnake.ui.ActionRow):
                                    for item in component.children:
                                        if hasattr(item, 'custom_id'):
                                            custom_id = item.custom_id
                                            if custom_id == f"create_ticket_{self.panel_id}" or custom_id == f"ticket_panel_option_select_{self.panel_id}":
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
                                await reset_panel_message(fake_inter, self.panel_data, self.panel_id)
                                break
            except Exception as e:
                print(f"Erro ao resetar painel após falha em verificação: {e}")
            return

        # Não deletar a mensagem de loading - ela será editada com a mensagem de sucesso
        try:
            await _finish_ticket_creation(
                inter, self.bot, self.panel_data, self.panel_id,
                option_data=self.option_data,
                form_answers=form_answers,
                loading_message=loading_msg
            )
            # Resetar a mensagem do painel original
            # Se self.inter tem message (interação original), usar ela
            # Caso contrário, buscar a mensagem do painel no canal
            try:
                if isinstance(self.inter, disnake.MessageInteraction) and hasattr(self.inter, 'message') and self.inter.message:
                    await reset_panel_message(self.inter, self.panel_data, self.panel_id)
                elif hasattr(inter, 'channel') and inter.channel and inter.guild:
                    # Buscar mensagens recentes do bot no canal que contenham o painel
                    async for msg in inter.channel.history(limit=20):
                        if msg.author == inter.guild.me and msg.components:
                            # Verificar se é a mensagem do painel procurando pelos custom_ids
                            is_panel = False
                            for component in msg.components:
                                if isinstance(component, disnake.ui.ActionRow):
                                    for item in component.children:
                                        if hasattr(item, 'custom_id'):
                                            custom_id = item.custom_id
                                            if custom_id == f"create_ticket_{self.panel_id}" or custom_id == f"ticket_panel_option_select_{self.panel_id}":
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
                                await reset_panel_message(fake_inter, self.panel_data, self.panel_id)
                                break
            except Exception as e:
                print(f"Erro ao resetar painel após criar ticket via modal: {e}")
        except (ValueError, disnake.HTTPException) as e:
            # Garantir que emoji está disponível
            from functions.emoji import emoji
            # Verificar se é erro de limite de canais
            error_message = str(e)
            if "Limite de canais exedido" in error_message or ("maximum" in error_message.lower() and "channel" in error_message.lower()):
                error_msg = f"{emoji.wrong} Limite de canais exedido na categoria, contate com administrador."
            elif isinstance(e, ValueError):
                error_msg = f"{emoji.wrong} {str(e)}"
            else:
                error_msg = f"{emoji.wrong} Ocorreu um erro ao criar o ticket: {e}"
            
            try:
                await loading_msg.edit(content=error_msg)
            except:
                await inter.followup.send(content=error_msg, ephemeral=True)
            # Resetar o painel quando erro ocorrer
            try:
                if isinstance(self.inter, disnake.MessageInteraction) and hasattr(self.inter, 'message') and self.inter.message:
                    await reset_panel_message(self.inter, self.panel_data, self.panel_id)
                elif hasattr(inter, 'channel') and inter.channel and inter.guild:
                    # Buscar mensagens recentes do bot no canal que contenham o painel
                    async for msg in inter.channel.history(limit=20):
                        if msg.author == inter.guild.me and msg.components:
                            # Verificar se é a mensagem do painel procurando pelos custom_ids
                            is_panel = False
                            for component in msg.components:
                                if isinstance(component, disnake.ui.ActionRow):
                                    for item in component.children:
                                        if hasattr(item, 'custom_id'):
                                            custom_id = item.custom_id
                                            if custom_id == f"create_ticket_{self.panel_id}" or custom_id == f"ticket_panel_option_select_{self.panel_id}":
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
                                await reset_panel_message(fake_inter, self.panel_data, self.panel_id)
                                break
            except Exception as reset_error:
                print(f"Erro ao resetar painel após erro: {reset_error}")
        except Exception as e:
            # Garantir que emoji está disponível
            from functions.emoji import emoji
            try:
                await loading_msg.edit(content=f"{emoji.wrong} Ocorreu um erro inesperado: {e}")
            except:
                await inter.followup.send(content=f"{emoji.wrong} Ocorreu um erro inesperado: {e}", ephemeral=True)
            # Resetar o painel quando erro ocorrer
            try:
                if isinstance(self.inter, disnake.MessageInteraction) and hasattr(self.inter, 'message') and self.inter.message:
                    await reset_panel_message(self.inter, self.panel_data, self.panel_id)
                elif hasattr(inter, 'channel') and inter.channel and inter.guild:
                    # Buscar mensagens recentes do bot no canal que contenham o painel
                    async for msg in inter.channel.history(limit=20):
                        if msg.author == inter.guild.me and msg.components:
                            # Verificar se é a mensagem do painel procurando pelos custom_ids
                            is_panel = False
                            for component in msg.components:
                                if isinstance(component, disnake.ui.ActionRow):
                                    for item in component.children:
                                        if hasattr(item, 'custom_id'):
                                            custom_id = item.custom_id
                                            if custom_id == f"create_ticket_{self.panel_id}" or custom_id == f"ticket_panel_option_select_{self.panel_id}":
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
                                await reset_panel_message(fake_inter, self.panel_data, self.panel_id)
                                break
            except Exception as reset_error:
                print(f"Erro ao resetar painel após erro: {reset_error}")

async def reset_panel_message(inter: disnake.MessageInteraction, panel_data: dict, panel_id: str):
    """Reseta a mensagem do painel removendo valores selecionados dos selects"""
    try:
        if not hasattr(inter, 'message') or not inter.message:
            return
        
        style = panel_data.get("message_style", "embed")
        payload = {}
        options = panel_data.get("options", [])
        action_row = None

        if len(options) > 1:
            select_options = []
            for opt in options:
                try:
                    opt_emoji = opt.get("emoji")
                    parsed_emoji = None
                    if opt_emoji:
                        parsed_emoji = utils.safe_get_emoji(opt_emoji)
                    
                    select_options.append(
                        disnake.SelectOption(
                            label=opt.get("name", "Opção sem nome"),
                            value=str(opt.get("id")),
                            emoji=parsed_emoji,
                            description=opt.get("description")
                        )
                    )
                except Exception:
                    select_options.append(
                        disnake.SelectOption(
                            label=opt.get("name", "Opção sem nome"),
                            value=str(opt.get("id")),
                            emoji=None,
                            description=opt.get("description")
                        )
                    )
            
            select = disnake.ui.StringSelect(
                custom_id=f"ticket_panel_option_select_{panel_id}",
                placeholder="Selecione uma opção para abrir o ticket...",
                options=select_options
            )
            action_row = disnake.ui.ActionRow(select)
        else:
            button_data = panel_data.get("button", {})
            button_style_map = {
                "green": disnake.ButtonStyle.success, "grey": disnake.ButtonStyle.secondary,
                "red": disnake.ButtonStyle.danger, "blue": disnake.ButtonStyle.primary
            }
            
            button_label = button_data.get("label") if button_data.get("label") else "Abrir ticket"
            button_emoji_raw = button_data.get("emoji")
            button_emoji = None
            if button_emoji_raw:
                button_emoji = utils.safe_get_emoji(button_emoji_raw)
            if not button_emoji:
                button_emoji = emoji.mail2
            
            button_style = button_style_map.get(button_data.get("style", "grey").lower(), disnake.ButtonStyle.secondary)
            
            try:
                button = disnake.ui.Button(
                    label=button_label, 
                    emoji=button_emoji,
                    style=button_style, 
                    custom_id=f"create_ticket_{panel_id}"
                )
            except Exception:
                button = disnake.ui.Button(
                    label=button_label, 
                    emoji=None,
                    style=button_style, 
                    custom_id=f"create_ticket_{panel_id}"
                )
            action_row = disnake.ui.ActionRow(button)

        if style == "embed":
            content_data = panel_data.get("embed", {})
            try:
                color_str = content_data.get("color", "#5865F2").lstrip("#")
                color = disnake.Color(int(color_str, 16))
            except (ValueError, TypeError):
                color = disnake.Color.default()

            embed = disnake.Embed(
                title=content_data.get("title"), 
                description=content_data.get("description"),
                color=color
            )
            if image_url := content_data.get("image_url"):
                if "http" in image_url: embed.set_image(url=image_url)
            if thumb_url := content_data.get("thumbnail_url"):
                if "http" in thumb_url: embed.set_thumbnail(url=thumb_url)
            
            payload["embed"] = embed
            payload["components"] = [action_row]
            
        elif style == "content":
            content_data = panel_data.get("content", {})
            payload["content"] = content_data.get("content")
            payload["components"] = [action_row]
            if image_url := content_data.get("image_url"):
                if "http" in image_url:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as resp:
                                if resp.status == 200:
                                    image_bytes = await resp.read()
                                    payload["file"] = disnake.File(io.BytesIO(image_bytes), filename="image.png")
                    except Exception:
                        pass
                        
        elif style == "container":
            content_data = panel_data.get("container", {})
            content = content_data.get("content")
            image_url = content_data.get("image_url")
            thumbnail_url = content_data.get("thumbnail_url")
            color_hex = content_data.get("color")

            container = ContainerUtils.montar_container(
                conteudo=content, 
                imagem_url=image_url, 
                cor_hex=color_hex, 
                extra_children=[action_row],
                thumbnail_url=thumbnail_url
            )
            payload["components"] = [container]
            payload["flags"] = disnake.MessageFlags(is_components_v2=True)

        # Editar a mensagem do painel
        try:
            # Verificar se a mensagem ainda existe e está acessível
            if not inter.message:
                return
            
            # Tentar buscar a mensagem novamente para garantir que ainda existe
            try:
                message = await inter.message.channel.fetch_message(inter.message.id)
            except (disnake.NotFound, disnake.HTTPException):
                # Mensagem não existe mais, não podemos editá-la
                return
            
            await message.edit(**payload)
        except (disnake.NotFound, disnake.HTTPException) as e:
            # Mensagem pode ter sido deletada ou não estar mais acessível
            # Não fazer nada, apenas ignorar silenciosamente
            pass
        except Exception as e:
            print(f"Erro inesperado ao resetar painel: {e}")
    except Exception as e:
        # Falha silenciosamente se não conseguir resetar o painel
        print(f"Erro ao resetar painel: {e}")

async def send_opening_message(channel: disnake.TextChannel | disnake.Thread, user: disnake.Member, panel_data: dict, option_data: dict = None, form_answers: dict = None, questions: list = None):
    if option_data:
        open_message_data = option_data.get("open_message", {})
    else:
        open_message_data = panel_data.get("open_message", {})

    style = open_message_data.get("style", "embed")

    # 1. Determina o conteúdo inicial (sem menções - serão enviadas separadamente)
    initial_content = ""

    # 2. Verifica se há conteúdo personalizado para a mensagem de abertura
    has_custom_content = False
    if style == "embed":
        has_custom_content = bool(open_message_data.get("embed", {}).get("title") or open_message_data.get("embed", {}).get("description"))
    elif style == "content":
        has_custom_content = bool(open_message_data.get("content", {}).get("content") or open_message_data.get("content", {}).get("image_url"))
    elif style == "container":
        has_custom_content = bool(open_message_data.get("container", {}).get("content"))

    mode = db.get_document("custom_mode").get("mode")
    primary_color_hex = db.get_document("custom_colors").get("primary")

    # 3. Cria os botões de ação, se aplicável
    action_row = None
    buttons = [
        disnake.ui.Button(
            label="Painel do Atendente",
            emoji=emoji.shield_star,
            style=disnake.ButtonStyle.grey,
            custom_id="ticket_attendant_setup"
        ),
        disnake.ui.Button(
            label="Painel do Usuário",
            emoji=emoji.member,
            style=disnake.ButtonStyle.grey,
            custom_id="ticket_user_setup"
        ),
        disnake.ui.Button(
            label="",
            emoji=emoji.information,
            style=disnake.ButtonStyle.grey,
            custom_id="ticket_info"
        )
    ]
    action_row = disnake.ui.ActionRow(*buttons)

    # --- Lógica de Envio de Mensagem ---

    # Lida com componentes V2 (estilo container) separadamente para evitar conflitos de API
    if style == "container":
        if initial_content:
            await channel.send(initial_content)
        
        components_to_send = []
        if has_custom_content:
            data = open_message_data.get("container", {})
            
            form_string = ""
            if form_answers and questions:
                question_map = {q['id']: q['label'] for q in questions}
                form_string = "\n\n**Respostas do Formulário:**\n" + "\n".join(
                    f"**{question_map.get(qid, 'Pergunta desconhecida')}:**\n{answer}"
                    for qid, answer in form_answers.items()
                )

            container_content = data.get("content", "") + form_string

            container = ContainerUtils.montar_container(
                conteudo=container_content,
                imagem_url=data.get("image_url"),
                cor_hex=data.get("color"),
                thumbnail_url=data.get("thumbnail_url")
            )
            components_to_send.append(container)
        
        if components_to_send:
            await channel.send(components=components_to_send, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Se houver respostas do formulário e NÃO houver conteúdo customizado, enviar as respostas separadamente
        if form_answers and questions and not has_custom_content:
            question_map = {q['id']: q['label'] for q in questions}
            form_text = "**Motivo/Informações do Ticket:**\n\n" + "\n\n".join(
                f"**{question_map.get(qid, 'Pergunta desconhecida')}:**\n{answer}"
                for qid, answer in form_answers.items()
            )
            await channel.send(form_text)
        
        if action_row:
            await channel.send(components=[action_row])
        
        return

    # Lida com componentes legados (embed, content, ou apenas menções)
    payload = {}
    if not has_custom_content:
        if mode == "embed":
            embed_kwargs = {}
            if primary_color_hex:
                embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
            
            # Se houver respostas do formulário, incluir no embed
            description = "Seu ticket foi aberto."
            if form_answers and questions:
                question_map = {q['id']: q['label'] for q in questions}
                form_string = "\n\n**Motivo/Informações:**\n" + "\n".join(
                    f"**{question_map.get(qid, 'Pergunta')}:** {answer}"
                    for qid, answer in form_answers.items()
                )
                description += form_string
            
            # Envia menções fora do embed, no content da mesma mensagem
            payload["content"] = initial_content or None
            embed = disnake.Embed(
                description=description,
                **embed_kwargs
            )
            payload["embed"] = embed
        else:
            content = initial_content or None
            # Se houver respostas do formulário, incluir no conteúdo
            if form_answers and questions:
                question_map = {q['id']: q['label'] for q in questions}
                form_text = "\n\n**Motivo/Informações do Ticket:**\n" + "\n".join(
                    f"**{question_map.get(qid, 'Pergunta')}:** {answer}"
                    for qid, answer in form_answers.items()
                )
                content = (content or "") + form_text
            payload["content"] = content

    elif style == "embed":
        data = open_message_data.get("embed", {})
        # Sempre envia menções no content, não no embed
        payload["content"] = initial_content if initial_content else None
        
        color_str = data.get("color") or primary_color_hex
        embed_kwargs = {}
        if color_str:
            try:
                embed_kwargs["color"] = disnake.Color(int(color_str.lstrip("#"), 16))
            except (ValueError, TypeError):
                pass
        
        description = data.get("description", "")
        
        form_string = ""
        if form_answers and questions:
            question_map = {q['id']: q['label'] for q in questions}
            form_string = "\n\n**Respostas do Formulário:**\n" + "\n".join(
                f"**{question_map.get(qid, 'Pergunta desconhecida')}:**\n{answer}"
                for qid, answer in form_answers.items()
            )

        full_description = f"{description}{form_string}".strip()

        embed = disnake.Embed(title=data.get("title"), description=full_description, **embed_kwargs)
        if image_url := data.get("image_url"):
            embed.set_image(url=image_url)
        if thumbnail_url := data.get("thumbnail_url"):
            embed.set_thumbnail(url=thumbnail_url)
        payload["embed"] = embed

    elif style == "content":
        data = open_message_data.get("content", {})
        content = data.get("content", "")
        
        form_string = ""
        if form_answers and questions:
            question_map = {q['id']: q['label'] for q in questions}
            form_string = "\n\n**Respostas do Formulário:**\n" + "\n".join(
                f"**{question_map.get(qid, 'Pergunta desconhecida')}:**\n```{answer}```"
                for qid, answer in form_answers.items()
            )

        payload["content"] = f"{initial_content}\n{content}{form_string}".strip()
    
    if action_row:
        payload["components"] = [action_row]

    file_to_send = None
    if style == "content" and (image_url := open_message_data.get("content", {}).get("image_url")):
        if "http" in image_url:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status == 200:
                            image_bytes = await resp.read()
                            file_to_send = disnake.File(io.BytesIO(image_bytes), filename="image.png")
            except Exception:
                pass

    if payload.get("content") or payload.get("embed") or payload.get("components") or file_to_send:
        await channel.send(file=file_to_send, **payload)


async def open_ticket(inter: disnake.Interaction, bot: commands.Bot, panel_data: dict, panel_id: str, option_data: dict = None, loading_message: disnake.Message = None):
    # Esta função agora só é chamada depois de um message.wait
    # O chamador lida com as exceções.
    
    # Função auxiliar para editar a mensagem correta
    async def edit_message(content: str):
        if loading_message:
            try:
                await loading_message.edit(content=content)
            except:
                try:
                    await inter.edit_original_message(content=content)
                except:
                    pass
        else:
            try:
                await inter.edit_original_message(content=content)
            except:
                pass
    
    # Mover as checagens para cá para o fluxo sem formulário
    ok, error_msg = await check_office_hours(inter, panel_data)
    if not ok:
        await edit_message(error_msg)
        # Resetar o painel quando verificação falhar
        if isinstance(inter, disnake.MessageInteraction) and hasattr(inter, 'message') and inter.message:
            try:
                await reset_panel_message(inter, panel_data, panel_id)
            except Exception as e:
                print(f"Erro ao resetar painel após falha em verificação: {e}")
        return

    ok, error_msg = await check_permissions(inter, panel_data, option_data)
    if not ok:
        await edit_message(error_msg)
        # Resetar o painel quando verificação falhar
        if isinstance(inter, disnake.MessageInteraction) and hasattr(inter, 'message') and inter.message:
            try:
                await reset_panel_message(inter, panel_data, panel_id)
            except Exception as e:
                print(f"Erro ao resetar painel após falha em verificação: {e}")
        return

    ok, error_msg = await check_existing_ticket(inter, bot, panel_id)
    if not ok:
        await edit_message(error_msg)
        # Resetar o painel quando verificação falhar
        if isinstance(inter, disnake.MessageInteraction) and hasattr(inter, 'message') and inter.message:
            try:
                await reset_panel_message(inter, panel_data, panel_id)
            except Exception as e:
                print(f"Erro ao resetar painel após falha em verificação: {e}")
        return

    await _finish_ticket_creation(inter, bot, panel_data, panel_id, option_data, loading_message=loading_message)


# ========== FUNÇÃO _finish_ticket_creation SUBSTITUÍDA PELO PATCH ==========
async def _finish_ticket_creation(
    inter, bot, panel_data, panel_id,
    option_data=None, form_answers=None, loading_message=None
):
    user = inter.author

    # ── Lock por usuário+painel: evita criação duplicada em cliques rápidos ──
    async with ticket_locks.for_user(panel_id, user.id):
        # Re-verificar ticket existente dentro do lock
        tickets_data = tickets_data_cache.get(db)
        user_tickets = tickets_data.get("panels", {}).get(panel_id, {}).get(str(user.id), [])
        for t in user_tickets:
            if t.get("status") == "open":
                try:
                    ch = bot.get_channel(t["ticket_id"]) or await bot.fetch_channel(t["ticket_id"])
                    if ch:
                        msg = f"{emoji.wrong} Você já possui um ticket aberto em {ch.mention}."
                        if loading_message:
                            await loading_message.edit(content=msg)
                        else:
                            try:
                                await inter.edit_original_message(content=msg)
                            except Exception:
                                pass
                        return None
                except (disnake.NotFound, disnake.Forbidden):
                    t["status"] = "closed"

        # ── Criação do canal/tópico ───────────────────────────────────────────
        mode = panel_data.get("mode") or "channel"
        if option_data:
            ticket_name_raw = option_data.get("name", "ticket")
        else:
            ticket_name_raw = panel_data.get("name", "ticket")

        import re
        ticket_name = re.sub(r'[^a-z0-9-]', '', ticket_name_raw.lower().replace(' ', '-'))[:25]
        if not ticket_name:
            ticket_name = "ticket"

        new_ticket_channel = None

        if mode == "topic":
            channel_id = panel_data.get("channel_id")
            channel = bot.get_channel(channel_id)
            if not channel or not isinstance(channel, disnake.TextChannel):
                raise ValueError("O canal para criação de tópicos não foi encontrado.")
            new_ticket_channel = await channel.create_thread(
                name=f"{ticket_name}-{user.name}",
                type=disnake.ChannelType.private_thread,
                invitable=False
            )

        elif mode == "channel":
            from .permissions import get_attendant_roles
            category_id = panel_data.get("category_id")
            category = bot.get_channel(category_id)
            if not category or not isinstance(category, disnake.CategoryChannel):
                raise ValueError("A categoria para criação de canais não foi encontrada.")

            text_channels_in_category = [ch for ch in category.channels if isinstance(ch, disnake.TextChannel)]
            if len(text_channels_in_category) >= 50:
                raise ValueError("Limite de canais exedido na categoria, contate com administrador.")

            roles_data = option_data.get("roles", {}) if option_data else panel_data.get("roles", {})
            atendentes_roles_ids = get_attendant_roles(roles_data)
            overwrites = {
                inter.guild.default_role: disnake.PermissionOverwrite(read_messages=False),
                user: disnake.PermissionOverwrite(read_messages=True, send_messages=True),
                inter.guild.me: disnake.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
            }
            for role_id in atendentes_roles_ids:
                role = inter.guild.get_role(role_id)
                if role:
                    overwrites[role] = disnake.PermissionOverwrite(read_messages=True, send_messages=True)

            try:
                new_ticket_channel = await inter.guild.create_text_channel(
                    name=f"{ticket_name}-{user.name}",
                    category=category,
                    overwrites=overwrites,
                )
            except disnake.HTTPException as e:
                if "maximum" in str(e).lower() or "limit" in str(e).lower() or e.code == 50035:
                    raise ValueError("Limite de canais exedido na categoria, contate com administrador.")
                raise
        else:
            raise ValueError(f"Modo de painel desconhecido: '{mode}'.")

        if not new_ticket_channel:
            return None

        # ── Salvar na database e no índice ────────────────────────────────────
        import time as _time
        tickets_data.setdefault("panels", {}).setdefault(panel_id, {}).setdefault(str(user.id), [])
        ticket_payload = {
            "ticket_id": new_ticket_channel.id,
            "status": "open",
            "created_at": int(_time.time()),
            "history": [{"type": "create", "author_id": user.id, "timestamp": int(_time.time()), "details": {}}],
        }
        if option_data:
            ticket_payload["option_id"] = option_data.get("id")
        if form_answers:
            ticket_payload["form_answers"] = form_answers

        tickets_data["panels"][panel_id][str(user.id)].append(ticket_payload)
        tickets_data_cache.save(db, tickets_data)

        # Registrar no índice imediatamente
        ticket_index.register(new_ticket_channel.id, panel_id, str(user.id), ticket_payload)

    # ── Fora do lock: envio de mensagens (I/O lento não precisa de lock) ──────
    from .logs_tickets import log_ticket_creation
    from .open_ticket import send_opening_message
    import asyncio as _asyncio

    await log_ticket_creation(bot, new_ticket_channel, user, panel_data.get("name", "N/A"), mode)

    questions = []
    if form_answers and option_data:
        option_id = str(option_data.get("id"))
        questions = panel_data.get("forms", {}).get(option_id, [])
    await send_opening_message(new_ticket_channel, user, panel_data, option_data, form_answers, questions)

    # ── Suporte a Produto: envia select de compras se ativado ────────────────
    product_support_enabled = panel_data.get("preferences", {}).get("product_support", {}).get("enabled", False)
    if product_support_enabled:
        try:
            from .product_support import send_product_support_select
            await send_product_support_select(new_ticket_channel, user, panel_id)
        except Exception as e:
            print(f"[ProductSupport] Erro ao enviar select de compras: {e}")
    # ─────────────────────────────────────────────────────────────────────────

    # Menções temporárias
    from .permissions import get_attendant_roles as _gar
    roles_data = option_data.get("roles", {}) if option_data else panel_data.get("roles", {})
    mentions = [user.mention] + [
        inter.guild.get_role(rid).mention
        for rid in _gar(roles_data)
        if inter.guild.get_role(rid)
    ]
    try:
        mention_msg = await new_ticket_channel.send(" ".join(mentions))
        await _asyncio.sleep(2)
        await mention_msg.delete()
    except Exception:
        pass

    success_msg = f"{emoji.correct} Ticket criado com sucesso em {new_ticket_channel.mention}!"
    if loading_message:
        try:
            await loading_message.edit(content=success_msg)
        except Exception:
            pass
    else:
        try:
            await inter.edit_original_message(content=success_msg)
        except Exception:
            pass

    # Reset do painel
    if isinstance(inter, disnake.MessageInteraction) and hasattr(inter, "message") and inter.message:
        try:
            from .open_ticket import reset_panel_message
            await reset_panel_message(inter, panel_data, panel_id)
        except Exception as e:
            print(f"Erro ao resetar painel: {e}")

    return new_ticket_channel
# ============================================================================