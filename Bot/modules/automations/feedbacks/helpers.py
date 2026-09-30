import disnake
from functions.database import database as db
from functions.emoji import emoji
from functions.ai_api import chamar_ia

def truncar_texto(texto: str, limite: int, sufixo: str = "...") -> str:
    """Trunca um texto respeitando um limite de caracteres, tentando não cortar palavras."""
    if not texto or len(texto) <= limite:
        return texto
    
    # Se o limite é muito pequeno, apenas trunca
    if limite <= len(sufixo):
        return texto[:limite]
    
    texto_truncado = texto[:limite - len(sufixo)]
    
    # Tenta encontrar o último espaço para não cortar palavras
    ultimo_espaco = texto_truncado.rfind(' ')
    if ultimo_espaco > limite * 0.7:  # Se encontrou um espaço em uma posição razoável
        texto_truncado = texto_truncado[:ultimo_espaco]
    
    return texto_truncado + sufixo

def truncar_para_embed_field(texto: str) -> str:
    """Trunca texto para uso em embed field value (limite: 1024 caracteres)."""
    return truncar_texto(texto, 1024)

def truncar_para_code_block(texto: str) -> str:
    """Trunca texto para uso em code block dentro de TextDisplay (limite: ~1900 caracteres considerando ```)."""
    return truncar_texto(texto, 1900)


def carregar_config() -> dict:
    """Carrega a configuração da coleção 'feedbacks'."""
    return db.get_document("automations_feedbacks") or {"ativado": False}

def salvar_config(data: dict) -> None:
    """Salva a configuração na coleção 'feedbacks'."""
    db.save_document("automations_feedbacks", {}, data)

def carregar_log() -> dict:
    """Carrega o log de DMs de feedback da coleção 'feedbacks_log'."""
    return db.get_document("automations_feedbacks_log") or {}

def salvar_log(data: dict) -> None:
    """Salva o log de DMs de feedback na coleção 'feedbacks_log'."""
    db.save_document("automations_feedbacks_log", {}, data)

# Função chamar_ia agora importada de functions.ai_api

async def notificar_admins(bot: disnake.ext.commands.Bot, message: disnake.Message, classification: str):
    """Envia uma notificação em DM para administradores e donos do bot."""
    cargos_config = db.get_document("cargos") or {}
    admin_role_id = cargos_config.get("cargo_admin")

    # Usar a classe perms para obter lista de usuários com permissão
    from functions.perms import perms as perms_module
    bot_owners = perms_module.get_all_users()
    # Incluir o owner também
    owner_id = perms_module.get_owner_id()
    if owner_id:
        bot_owners = [owner_id] + [uid for uid in bot_owners if uid != owner_id]

    admins = set()

    if admin_role_id:
        guild = message.guild
        admin_role = guild.get_role(int(admin_role_id))
        if admin_role:
            admins.update(member for member in admin_role.members)

    for user_id in bot_owners:
        try:
            user = await bot.fetch_user(int(user_id))
            if user:
                admins.add(user)
        except (disnake.NotFound, ValueError):
            continue
    
    mode = db.get_document("custom_mode").get("mode")
    notifications = []
    
    if mode == "embed":
        embed, components = criar_notificacao_embed(message, classification)
        for admin in admins:
            try:
                dm_message = await admin.send(embed=embed, components=components)
                notifications.append({"admin_id": admin.id, "dm_channel_id": dm_message.channel.id, "message_id": dm_message.id})
            except disnake.Forbidden:
                print(f"Não foi possível enviar DM para o admin {admin.id}.")
            except Exception as e:
                print(f"Erro ao enviar DM para o admin {admin.id}: {e}")
    else:
        components = criar_notificacao_components(message, classification)
        for admin in admins:
            try:
                dm_message = await admin.send(components=components)
                notifications.append({"admin_id": admin.id, "dm_channel_id": dm_message.channel.id, "message_id": dm_message.id})
            except disnake.Forbidden:
                print(f"Não foi possível enviar DM para o admin {admin.id}.")
            except Exception as e:
                print(f"Erro ao enviar DM para o admin {admin.id}: {e}")

    if notifications:
        log = carregar_log()
        log[str(message.id)] = {
            "notifications": notifications,
            "action_taken": None,
            "original_message": {
                "content": message.content,
                "author_id": message.author.id,
                "author_mention": message.author.mention,
                "jump_url": message.jump_url
            }
        }
        salvar_log(log)

def criar_notificacao_components(message: disnake.Message, classification: str) -> list[disnake.ui.Container]:
    """Cria os componentes da UI para a mensagem de notificação."""
    colors = db.get_document("custom_colors") or {}
    primary_color_hex = colors.get("primary")
    container_kwargs = {}
    if primary_color_hex:
        color_int = int(primary_color_hex.replace("#", ""), 16)
        container_kwargs["accent_colour"] = disnake.Colour(color_int)

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Monitoramento de Feedbacks\nUm feedback potencialmente problemático foi detectado."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**Autor:** {message.author.mention} (`{message.author.id}`)\n"
                f"**Classificação:** `{classification}`\n"
                f"**Mensagem:**\n```{truncar_para_code_block(message.content)}```"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),   
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Apagar Mensagem", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"feedback_delete:{message.id}:{message.channel.id}"),
                disnake.ui.Button(label="Foi um engano", style=disnake.ButtonStyle.green, emoji=emoji.correct, custom_id=f"feedback_ignore:{message.id}:{message.channel.id}"),
                disnake.ui.Button(label="Ir para o Canal", style=disnake.ButtonStyle.link, url=message.jump_url)
            ),
            **container_kwargs,
        ),
    ]

def criar_notificacao_embed(message: disnake.Message, classification: str) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
    """Cria o embed e os componentes para a mensagem de notificação."""
    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed = disnake.Embed(
        title=f"Monitoramento de Feedbacks",
        description="Um feedback potencialmente problemático foi detectado."
    )
    if primary_color_hex:
        embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
    
    embed.add_field(name="Autor", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
    embed.add_field(name="Classificação", value=f"`{classification}`", inline=False)
    embed.add_field(name="Mensagem", value=f"```{truncar_para_embed_field(message.content)}```", inline=False)
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Apagar Mensagem", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"feedback_delete:{message.id}:{message.channel.id}"),
            disnake.ui.Button(label="Foi um engano", style=disnake.ButtonStyle.green, emoji=emoji.correct, custom_id=f"feedback_ignore:{message.id}:{message.channel.id}"),
            disnake.ui.Button(label="Ir para o Canal", style=disnake.ButtonStyle.link, url=message.jump_url)
        )
    ]
    return embed, components

def criar_notificacao_components_atualizada(original_message: disnake.Message, admin_user: disnake.Member, action: str, original_channel_id: int) -> list[disnake.ui.Container]:
    """Cria os componentes da UI para a mensagem de notificação atualizada."""
    
    colors = db.get_document("custom_colors") or {}
    color_map = {
        "deleted": "danger",
        "ignored": "success",
        "deletion_failed_not_found": "warning",
        "deletion_failed_forbidden": "warning",
    }
    color_key = color_map.get(action)
    color_hex = colors.get(color_key) if color_key else None

    container_kwargs = {}
    if color_hex:
        color_int = int(color_hex.replace("#", ""), 16)
        container_kwargs["accent_colour"] = disnake.Colour(color_int)
    
    action_text = ""
    if action == "deleted":
        action_text = "A mensagem foi apagada com sucesso."
    elif action == "ignored":
        action_text = "A mensagem foi marcada como engano."
    elif action == "deletion_failed_not_found":
        action_text = "Tentativa de apagar falhou: a mensagem já não existia."
    elif action == "deletion_failed_forbidden":
        action_text = "Tentativa de apagar falhou: sem permissão."

    return [
        disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Monitoramento de Feedbacks\nUm feedback potencialmente problemático foi detectado."),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"**Autor:** {original_message.author.mention} (`{original_message.author.id}`)\n"
                f"**Mensagem:**\n```{truncar_para_code_block(original_message.content)}```"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(f"Ação tomada por {admin_user.mention}: **{action_text}**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),   
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Apagar Mensagem", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"feedback_delete:{original_message.id}:{original_channel_id}", disabled=True),
                disnake.ui.Button(label="Foi um engano", style=disnake.ButtonStyle.green, emoji=emoji.correct, custom_id=f"feedback_ignore:{original_message.id}:{original_channel_id}", disabled=True),
                disnake.ui.Button(label="Ir para o Canal", style=disnake.ButtonStyle.link, url=original_message.jump_url)
            ),
            **container_kwargs,
        ),
    ]

def criar_notificacao_embed_atualizada(original_message: disnake.Message, admin_user: disnake.Member, action: str, original_channel_id: int) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
    """Cria o embed e os componentes para a mensagem de notificação atualizada."""
    colors = db.get_document("custom_colors") or {}
    
    action_text = ""
    color = None
    color_hex = None
    description_verb = "Ação tomada por"
    title_suffix = "(Ação Tomada)"

    if action == "deleted":
        action_text = "Mensagem apagada."
        color_hex = colors.get("danger")
        color = disnake.Color.red()
    elif action == "ignored":
        action_text = "Marcado como engano."
        color_hex = colors.get("success")
        color = disnake.Color.green()
    elif action == "deletion_failed_not_found":
        action_text = "Tentativa de apagar falhou: a mensagem já não existia."
        color_hex = colors.get("warning")
        color = disnake.Color.yellow()
        description_verb = "Ação registrada por"
        title_suffix = "(Falha ao Apagar)"
    elif action == "deletion_failed_forbidden":
        action_text = "Tentativa de apagar falhou: sem permissão."
        color_hex = colors.get("warning")
        color = disnake.Color.orange()
        description_verb = "Ação registrada por"
        title_suffix = "(Falha ao Apagar)"

    if color_hex:
        color = disnake.Colour(int(color_hex.replace("#", ""), 16))

    embed = disnake.Embed(
        title=f"Monitoramento de Feedbacks {title_suffix}",
        description=f"{description_verb} {admin_user.mention} (`{admin_user.id}`).\n**Resultado:** {action_text}"
    )
    if color:
        embed.color = color
    else:
        primary_color_hex = colors.get("primary")
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
    
    embed.add_field(name="Autor do Feedback", value=f"{original_message.author.mention} (`{original_message.author.id}`)", inline=False)
    embed.add_field(name="Mensagem Original", value=f"```{truncar_para_embed_field(original_message.content)}```", inline=False)
    
    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Apagar Mensagem", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"feedback_delete:{original_message.id}:{original_channel_id}", disabled=True),
            disnake.ui.Button(label="Foi um engano", style=disnake.ButtonStyle.green, emoji=emoji.correct, custom_id=f"feedback_ignore:{original_message.id}:{original_channel_id}", disabled=True),
            disnake.ui.Button(label="Ir para o Canal", style=disnake.ButtonStyle.link, url=original_message.jump_url)
        )
    ]
    return embed, components
