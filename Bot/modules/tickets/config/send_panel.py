import disnake
import aiohttp
import io
from functions.database import database as db
from functions.message import message
from .container_utils import ContainerUtils
from functions.emoji import emoji
from functions.utils import utils

async def send_panel(inter: disnake.Interaction, bot, panel_id: str):
    config = db.get_document("tickets_config") or {}
    panel_data = config.get("panels", {}, ).get(panel_id)

    # --- Validações ---
    if not panel_data:
        return await inter.followup.send("Painel não encontrado.", ephemeral=True)
    
    # Validar configurações e retornar mensagem detalhada
    missing_items = []
    
    channel_id = panel_data.get("channel_id")
    if not channel_id:
        missing_items.append(f"{emoji.textc} **Canal de envio** - Defina o canal onde o painel será enviado")
    else:
        channel = bot.get_channel(channel_id)
        if not channel:
            missing_items.append(f"{emoji.wrong} **Canal válido** - O canal configurado não foi encontrado")

    style = panel_data.get("message_style", "embed")
    content_data = panel_data.get(style, {})
    current_mode = panel_data.get("mode", "channel")

    # Validar conteúdo
    if style == "embed":
        if not content_data.get("title"):
            missing_items.append(f"{emoji.edit} **Título do embed** - Configure em 'Editar Mensagens' > 'Editar Conteúdo'")
    elif style == "content":
        if not (content_data.get("content") or content_data.get("image_url")):
            missing_items.append(f"{emoji.edit} **Conteúdo ou imagem** - Configure em 'Editar Mensagens' > 'Editar Conteúdo'")
    elif style == "container":
        if not content_data.get("content"):
            missing_items.append(f"{emoji.edit} **Conteúdo do container** - Configure em 'Editar Mensagens' > 'Editar Conteúdo'")
    
    # Validar categoria se necessário
    if current_mode == "channel":
        if not panel_data.get("category_id"):
            missing_items.append(f"{emoji.dir} **Categoria** - Defina a categoria onde os tickets serão criados")
    
    # Validar botão/opções
    options = panel_data.get("options", [])
    if len(options) <= 1:
        button_data = panel_data.get("button", {})
        if not button_data.get("label"):
            missing_items.append(f"{emoji.wand} **Botão** - Configure em 'Editar Mensagens' > 'Editar Botão'")
    
    # Se houver itens faltando, retornar mensagem detalhada
    if missing_items:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        mode = db.get_document("custom_mode").get("mode", "embed")
        
        if mode == "components":
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            container = disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"{emoji.information} Para publicar o painel, você precisa configurar:\n\n" + "\n".join(missing_items) + 
                    f"\n\n{emoji.arrow} Configure os itens acima e tente novamente."
                ),
                **container_kwargs
            )
            return await inter.followup.send(
                components=[container],
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True
            )
        else:
            embed_kwargs = {}
            if primary_color_hex:
                embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
            
            embed = disnake.Embed(
                title=f"{emoji.wrong} Configurações Incompletas",
                description=f"{emoji.information} Para publicar o painel, você precisa configurar:\n\n" + "\n".join(missing_items) + 
                           f"\n\n{emoji.arrow} Configure os itens acima e tente novamente.",
                **embed_kwargs
            )
            return await inter.followup.send(embed=embed, ephemeral=True)
    
    # Se chegou aqui, channel está definido
    channel = bot.get_channel(channel_id)

    # --- Construção da Mensagem ---
    payload = {}
    options = panel_data.get("options", [])
    action_row = None

    if len(options) > 1:
        select_options = []
        for opt in options:
            try:
                # Validar e processar emoji de forma segura
                opt_emoji = opt.get("emoji")
                parsed_emoji = None
                if opt_emoji:
                    parsed_emoji = utils.safe_get_emoji(opt_emoji)
                    # Se o emoji for inválido, usar None (sem emoji)
                
                select_options.append(
                    disnake.SelectOption(
                        label=opt.get("name", "Opção sem nome"),
                        value=str(opt.get("id")),
                        emoji=parsed_emoji,
                        description=opt.get("description")
                    )
                )
            except Exception:
                # Se houver qualquer erro ao processar a opção, criar sem emoji
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
        # Uma única opção ou nenhuma - usar botão
        button_data = panel_data.get("button", {})
        button_style_map = {
            "green": disnake.ButtonStyle.success, "grey": disnake.ButtonStyle.secondary,
            "red": disnake.ButtonStyle.danger, "blue": disnake.ButtonStyle.primary
        }
        
        # Usar valores padrão se não configurado
        button_label = button_data.get("label") if button_data.get("label") else "Abrir ticket"
        
        # Validar e processar emoji de forma segura
        button_emoji_raw = button_data.get("emoji")
        button_emoji = None
        if button_emoji_raw:
            button_emoji = utils.safe_get_emoji(button_emoji_raw)
        # Se não houver emoji válido, usar o padrão
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
            # Se houver erro ao criar o botão (ex: emoji inválido), criar sem emoji
            button = disnake.ui.Button(
                label=button_label, 
                emoji=None,
                style=button_style, 
                custom_id=f"create_ticket_{panel_id}"
            )
        action_row = disnake.ui.ActionRow(button)

    if style == "embed":
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
                    pass # Falha silenciosamente no envio final se o download falhar
                    
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

    # --- Envio / Edição ---
    try:
        message_id = panel_data.get("message_id")

        # Se já existe uma mensagem, verifica compatibilidade V1/V2 (container vs embed/content)
        existing_msg = None
        if message_id:
            try:
                existing_msg = await channel.fetch_message(message_id)
            except disnake.NotFound:
                existing_msg = None
        
        # Se vamos enviar embed/content (V1) mas a mensagem existente é V2 (container), apaga antes
        if existing_msg and style in ("embed", "content"):
            if getattr(existing_msg.flags, "is_components_v2", False):
                try:
                    await existing_msg.delete()
                except Exception:
                    pass
                config["panels"][panel_id]["message_id"] = None
                message_id = None
        
        # Se vamos enviar container (V2) mas a mensagem existente é V1, apaga antes
        if existing_msg and style == "container":
            if not getattr(existing_msg.flags, "is_components_v2", False):
                try:
                    await existing_msg.delete()
                except Exception:
                    pass
                config["panels"][panel_id]["message_id"] = None
                message_id = None

        if message_id:
            msg = await channel.fetch_message(message_id)
            await msg.edit(**payload)
            await inter.followup.send(f"Painel atualizado com sucesso em {channel.mention}!", ephemeral=True)
        else:
            msg = await channel.send(**payload)
            config["panels"][panel_id]["message_id"] = msg.id
            await inter.followup.send(f"Painel enviado com sucesso para {channel.mention}!", ephemeral=True)

        # Marca que não há mais alterações pendentes após o sucesso
        config["panels"][panel_id]["has_pending_changes"] = False
        db.save_document("tickets_config", config)

    except disnake.NotFound:
        msg = await channel.send(**payload)
        config["panels"][panel_id]["message_id"] = msg.id
        config["panels"][panel_id]["has_pending_changes"] = False
        db.save_document("tickets_config", config)
        await inter.followup.send(f"A mensagem antiga não foi encontrada. Uma nova foi criada em {channel.mention}!", ephemeral=True)
    except Exception as e:
        await inter.followup.send(f"Falha ao publicar o painel: {e}", ephemeral=True)
