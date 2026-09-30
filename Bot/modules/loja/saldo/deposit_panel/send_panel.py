"""
Enviar painel de depósito para um canal
"""
import disnake
import aiohttp
import io
from functions.database import database as db
from functions.emoji import emoji
from functions.utils import utils


async def send_deposit_panel(inter: disnake.MessageInteraction, bot, channel: disnake.TextChannel = None):
    """Envia ou atualiza o painel de depósito no canal especificado"""
    config = db.get_document("loja_saldo_config") or {}
    deposit_panel = config.get("deposit_panel", {})
    
    # Helper para responder corretamente dependendo do modo
    async def reply(content_text, is_error=False):
        mode = db.get_document("custom_mode").get("mode", "components")
        color_data = db.get_document("custom_colors") or {}
        primary_color_hex = color_data.get("primary")
        
        if mode == "components":
            container_kwargs = {}
            if primary_color_hex:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except:
                    pass
            
            await inter.edit_original_message(
                content=None,
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(content_text),
                        **container_kwargs
                    )
                ]
            )
        else:
            embed_kwargs = {}
            if primary_color_hex and not is_error:
                try:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                except:
                    pass
            
            if is_error:
                embed_kwargs["color"] = disnake.Color.red()
            
            embed = disnake.Embed(description=content_text, **embed_kwargs)
            
            await inter.edit_original_message(
                content=None,
                embed=embed,
                components=[]
            )

    # Se o canal não for passado, buscar da config
    if not channel:
        channel_id = deposit_panel.get("channel_id")
        if not channel_id:
            return await reply(f"{emoji.wrong} Configure o canal de envio primeiro.", is_error=True)
        
        channel = bot.get_channel(channel_id)
        if not channel:
            return await reply(f"{emoji.wrong} Canal não encontrado. Verifique se o bot tem acesso.", is_error=True)
    
    style = deposit_panel.get("message_style", "embed")
    content_data = deposit_panel.get(style, {})
    
    # Verificar conteúdo
    if style == "embed":
        if not content_data.get("title"):
            return await reply(f"{emoji.wrong} Configure o conteúdo do embed primeiro.", is_error=True)
    elif style == "content":
        if not content_data.get("content"):
            return await reply(f"{emoji.wrong} Configure o conteúdo do texto primeiro.", is_error=True)
    elif style == "container":
        if not content_data.get("content"):
            return await reply(f"{emoji.wrong} Configure o conteúdo do container primeiro.", is_error=True)
    
    # Construir botão
    button_data = deposit_panel.get("button", {})
    button_style_map = {
        "green": disnake.ButtonStyle.success,
        "grey": disnake.ButtonStyle.secondary,
        "red": disnake.ButtonStyle.danger,
        "blue": disnake.ButtonStyle.primary
    }
    
    button_label = button_data.get("label", "Depositar")
    button_emoji_raw = button_data.get("emoji")
    button_emoji = None
    if button_emoji_raw:
        button_emoji = utils.safe_get_emoji(button_emoji_raw)
    if not button_emoji:
        button_emoji = emoji.wallet
    
    button_style = button_style_map.get(
        button_data.get("style", "green").lower(),
        disnake.ButtonStyle.success
    )
    
    try:
        button = disnake.ui.Button(
            label=button_label,
            emoji=button_emoji,
            style=button_style,
            custom_id="deposit_saldo_open"
        )
    except Exception:
        button = disnake.ui.Button(
            label=button_label,
            emoji=None,
            style=button_style,
            custom_id="deposit_saldo_open"
        )
    
    action_row = disnake.ui.ActionRow(button)
    
    # Construir mensagem
    payload = {}
    
    if style == "embed":
        try:
            color_str = content_data.get("color", "#5c5ef0").lstrip("#")
            color = disnake.Color(int(color_str, 16))
        except (ValueError, TypeError):
            color = disnake.Color.default()
        
        embed = disnake.Embed(
            title=content_data.get("title"),
            description=content_data.get("description"),
            color=color
        )
        
        if image_url := content_data.get("image_url"):
            if "http" in image_url:
                embed.set_image(url=image_url)
        
        if thumb_url := content_data.get("thumbnail_url"):
            if "http" in thumb_url:
                embed.set_thumbnail(url=thumb_url)
        
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
                                payload["file"] = disnake.File(
                                    io.BytesIO(image_bytes),
                                    filename="image.png"
                                )
                except Exception:
                    pass
    
    elif style == "container":
        from modules.tickets.config.container_utils import ContainerUtils
        
        container = ContainerUtils.montar_container(
            conteudo=content_data.get("content"),
            imagem_url=content_data.get("image_url"),
            cor_hex=content_data.get("color"),
            extra_children=[action_row],
            thumbnail_url=content_data.get("thumbnail_url")
        )
        payload["components"] = [container]
        payload["flags"] = disnake.MessageFlags(is_components_v2=True)
    
    # Enviar ou atualizar
    try:
        message_id = deposit_panel.get("message_id")
        
        if message_id:
            try:
                existing_msg = await channel.fetch_message(message_id)
                
                # Verificar compatibilidade V1/V2
                if style in ("embed", "content"):
                    if getattr(existing_msg.flags, "is_components_v2", False):
                        await existing_msg.delete()
                        config["deposit_panel"]["message_id"] = None
                        message_id = None
                elif style == "container":
                    if not getattr(existing_msg.flags, "is_components_v2", False):
                        await existing_msg.delete()
                        config["deposit_panel"]["message_id"] = None
                        message_id = None
                
                if message_id:
                    await existing_msg.edit(**payload)
                    await reply(f"{emoji.correct} Painel atualizado em {channel.mention}!")
                    config["deposit_panel"]["message_id"] = existing_msg.id
                    db.save_document("loja_saldo_config", config)
                    return
                    
            except disnake.NotFound:
                message_id = None
        
        # Enviar nova mensagem
        msg = await channel.send(**payload)
        config["deposit_panel"]["message_id"] = msg.id
        db.save_document("loja_saldo_config", config)
        
        await reply(f"{emoji.correct} Painel enviado para {channel.mention}!")
        
    except disnake.Forbidden:
        await reply(f"{emoji.wrong} Sem permissão para enviar mensagens no canal.", is_error=True)
    except Exception as e:
        await reply(f"{emoji.wrong} Erro ao enviar painel: {e}", is_error=True)
