import disnake
from datetime import datetime, timezone
from functions.database import database as db
from functions.emoji import emoji
from ..config_giveaways import get_giveaways
from tasks.giveaways.logger_giveaways import log_giveaway_event

REQUIREMENTS_CONFIG = {
    # Requisitos de Ativar/Desativar (só clicar)
    #"is_customer": {"label": "Ser cliente", "description": "O participante deve ter comprado na sua loja."},
    #"is_oauth2_verified": {"label": "Ser verificado via OAuth2", "description": "O participante deve ter verificado a conta via OAuth2."},
    "in_any_voice_channel": {"label": "Estar em um canal de voz", "description": "O participante deve estar em qualquer canal de voz."},
    "is_voice_muted": {"label": "Estar com o microfone mutado", "description": "O participante deve estar com o microfone mutado."},
    "is_voice_deafened": {"label": "Estar com o fone desativado", "description": "O participante deve estar com o fone desativado (surdo)."},
    "has_feedback": {"label": "Ter deixado feedback", "description": "O participante deve ter deixado um feedback no canal de feedbacks."},
    
    # Requisitos com Modal (configurar texto)
    "min_account_age_days": {"label": "Dias mínimos da conta", "description": "Define a idade mínima da conta do Discord.", "modal": True},
    "min_server_age_days": {"label": "Dias mínimos no servidor", "description": "Define o tempo mínimo que o membro deve estar no servidor.", "modal": True},
    "custom_nickname": {"label": "Nickname customizado", "description": "Exige que o participante tenha um texto específico no nickname.", "modal": True},
    "custom_status": {"label": "Status customizado", "description": "Exige que o participante tenha um texto específico no status.", "modal": True},
    "invited_by": {"label": "Ser convidado por", "description": "Define um ou mais membros que devem ter convidado o participante.", "modal": True},
    "min_invites": {"label": "Mínimo de convites", "description": "Define o número mínimo de convites que o membro deve ter.", "modal": True},
    
    # Requisitos com Modal (configurar valor específico)
    "specific_voice_channel": {"label": "Estar em canal de voz específico", "description": "Define um canal de voz onde o membro deve estar.", "modal": True},
    "server_tag": {"label": "Usar tag do servidor", "description": "Define um servidor específico cuja tag o usuário deve estar usando.", "modal": True},
    
    # Requisitos removidos por enquanto
    #"custom_bio": {"label": "Bio customizada", "description": "Exige que o participante tenha um texto específico na bio.", "modal": True},
    #"first_purchase_days_ago": {"label": "Primeira compra há X dias", "description": "Define o tempo máximo desde a primeira compra do membro.", "modal": True},
    #"custom_states_regions": {"label": "Estados/Regiões permitidos", "description": "Permite a participação apenas de membros de certos estados/regiões.", "modal": True},
    #"custom_cities": {"label": "Cidades permitidas", "description": "Permite a participação apenas de membros de certas cidades.", "modal": True},
    #"custom_countries": {"label": "Países permitidos", "description": "Permite a participação apenas de membros de certos países.", "modal": True},
}

def RequirementsView_components(inter: disnake.Interaction, giveaway_id: str) -> list[disnake.ui.Container]:
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    requirements = giveaway_data.get("requirements", {})

    status_lines = []
    for key, config in REQUIREMENTS_CONFIG.items():
        req_data = requirements.get(key, {})
        status = req_data.get("enabled", False)

        status_lines.append(f"{emoji.on if status else emoji.off} **{config['label']}**")
    
    status_text = "\n".join(status_lines)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    options = []
    for key, config in REQUIREMENTS_CONFIG.items():
        req_data = requirements.get(key, {})
        is_enabled = req_data.get("enabled", False)
        
        if is_enabled:
            # Se está ativo, mostrar o valor configurado
            value = req_data.get("value")
            if value is not None:
                if key == "specific_voice_channel":
                    try:
                        channel = inter.guild.get_channel(int(value))
                        display_value = f"Canal: {channel.name if channel else f'ID: {value}'}"
                    except (ValueError, TypeError):
                        display_value = f"ID: {value}"
                elif key == "invited_by":
                    members = [inter.guild.get_member(int(uid)) for uid in value]
                    names = [m.display_name for m in members if m]
                    display_value = f"Convidado por: {', '.join(names) if names else 'Ninguém'}"
                elif key == "server_tag":
                    display_value = f"ID do servidor: {value}"
                elif key in ["min_account_age_days", "min_server_age_days"]:
                    display_value = f"Mínimo: {value} dias"
                else:
                    display_value = f"Texto: {value}"
                
                options.append(disnake.SelectOption(
                    label=f"{config['label']}", 
                    value=key, 
                    emoji=emoji.correct, 
                    description=display_value
                ))
            else:
                # Requisito ativo mas sem valor (requisitos simples)
                options.append(disnake.SelectOption(
                    label=f"{config['label']}", 
                    value=key, 
                    emoji=emoji.correct, 
                    description="Ativo"
                ))
        else:
            # Se não está ativo, mostrar descrição padrão
            options.append(disnake.SelectOption(
                label=config['label'], 
                value=key, 
                emoji=emoji.arrow, 
                description=config['description']
            ))

    container = disnake.ui.Container(
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sorteios > {giveaway_name} > Preferências > **Definir Requisitos**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"GiveawayReq_Select_{giveaway_id}",
                placeholder="Selecione um requisito para ativar/desativar ou configurar",
                options=options
            )
        ),
        **container_kwargs
    )
    
    buttons = disnake.ui.ActionRow(
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayPref_BackToPreferences_{giveaway_id}")
    )

    return [container, buttons]

def RequirementsView_embed(inter: disnake.Interaction, giveaway_id: str):
    giveaway_data = get_giveaways().get(giveaway_id, {})
    giveaway_name = giveaway_data.get("name", "N/A")
    requirements = giveaway_data.get("requirements", {})

    status_lines = []
    for key, config in REQUIREMENTS_CONFIG.items():
        req_data = requirements.get(key, {})
        status = req_data.get("enabled", False)

        status_lines.append(f"{emoji.on if status else emoji.off} **{config['label']}**")
    
    description = "\n".join(status_lines)

    primary_color_hex = db.get_document("custom_colors").get("primary")
    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title=f"Definir Requisitos: {giveaway_name}", 
        description=description,
        **embed_kwargs
    )
    
    options = []
    for key, config in REQUIREMENTS_CONFIG.items():
        req_data = requirements.get(key, {})
        is_enabled = req_data.get("enabled", False)
        
        if is_enabled:
            # Se está ativo, mostrar o valor configurado
            value = req_data.get("value")
            if value is not None:
                if key == "specific_voice_channel":
                    try:
                        channel = inter.guild.get_channel(int(value))
                        display_value = f"Canal: {channel.name if channel else f'ID: {value}'}"
                    except (ValueError, TypeError):
                        display_value = f"ID: {value}"
                elif key == "invited_by":
                    members = [inter.guild.get_member(int(uid)) for uid in value]
                    names = [m.display_name for m in members if m]
                    display_value = f"Convidado por: {', '.join(names) if names else 'Ninguém'}"
                elif key == "server_tag":
                    display_value = f"ID do servidor: {value}"
                elif key in ["min_account_age_days", "min_server_age_days"]:
                    display_value = f"Mínimo: {value} dias"
                else:
                    display_value = f"Texto: {value}"
                
                options.append(disnake.SelectOption(
                    label=f"{config['label']}", 
                    value=key, 
                    emoji=emoji.correct, 
                    description=display_value
                ))
            else:
                # Requisito ativo mas sem valor (requisitos simples)
                options.append(disnake.SelectOption(
                    label=f"{config['label']}", 
                    value=key, 
                    emoji=emoji.correct, 
                    description="Ativo"
                ))
        else:
            # Se não está ativo, mostrar descrição padrão
            options.append(disnake.SelectOption(
                label=config['label'], 
                value=key, 
                emoji=emoji.arrow, 
                description=config['description']
            ))

    components = [
        disnake.ui.ActionRow(
            disnake.ui.StringSelect(
                custom_id=f"GiveawayReq_Select_{giveaway_id}",
                placeholder="Selecione um requisito para ativar/desativar ou configurar",
                options=options
            )
        ),
        disnake.ui.ActionRow(
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"GiveawayPref_BackToPreferences_{giveaway_id}")
        )
    ]

    return embed, components

# --- Requirements Verification Functions ---

class RequirementModal(disnake.ui.Modal):
    def __init__(self, inter: disnake.Interaction, giveaway_id: str, requirement_key: str):
        self.inter = inter
        self.giveaway_id = giveaway_id
        self.requirement_key = requirement_key

        req_config = REQUIREMENTS_CONFIG[requirement_key]
        giveaway_data = get_giveaways().get(giveaway_id, {})
        current_value = giveaway_data.get("requirements", {}).get(requirement_key, {}).get("value", "")

        # Definir placeholder específico para cada tipo de requisito
        if requirement_key == "server_tag":
            placeholder = "Digite o ID do servidor... (deixe vazio para desativar)"
        elif requirement_key == "specific_voice_channel":
            placeholder = "Digite o ID do canal de voz... (deixe vazio para desativar)"
        elif requirement_key == "invited_by":
            placeholder = "IDs dos membros, separados por vírgula..."
        else:
            placeholder = "Digite o valor necessário... (deixe vazio para desativar)"

        components = [
            disnake.ui.TextInput(
                label=req_config["label"],
                custom_id="req_value",
                style=disnake.TextInputStyle.short,
                placeholder=placeholder,
                value=str(current_value) if current_value else "",
                required=False,
            ),
        ]
        super().__init__(title=f"Configurar: {req_config['label']}", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        value = inter.text_values["req_value"].strip()

        # Se o valor estiver vazio, desativar o requisito
        if not value:
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(self.giveaway_id, {})
            requirements = giveaway.setdefault("requirements", {})
            req_data = requirements.setdefault(self.requirement_key, {})

            req_data["enabled"] = False
            req_data.pop("value", None)  # Remove o valor se existir
            db.salvar("database/giveaways/giveaways_data.json", config)

            await inter.response.defer(ephemeral=True)
            await inter.followup.send(f"{emoji.delete} Requisito **{REQUIREMENTS_CONFIG[self.requirement_key]['label']}** desativado com sucesso.", ephemeral=True)
            
            await log_giveaway_event(
                bot=inter.bot,
                giveaway_id=self.giveaway_id,
                title="Sorteios - Requisito Alterado",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                    f"{emoji.settings} **Requisito:** {REQUIREMENTS_CONFIG[self.requirement_key]['label']}",
                    f"{emoji.edit} **Ação:** Requisito desativado",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await self.inter.edit_original_message(components=RequirementsView_components(self.inter, self.giveaway_id))
            else:
                embed, components = RequirementsView_embed(self.inter, self.giveaway_id)
                await self.inter.edit_original_message(embed=embed, components=components)
            return

        # Validar valor para campos numéricos
        numeric_fields = ["min_account_age_days", "min_server_age_days", "min_invites", "first_purchase_days_ago"]
        if self.requirement_key in numeric_fields:
            try:
                numeric_value = int(value)
                if numeric_value <= 0:
                    await inter.response.send_message(f"{emoji.wrong} O valor para **{REQUIREMENTS_CONFIG[self.requirement_key]['label']}** deve ser um número inteiro positivo.", ephemeral=True)
                    return
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} O valor para **{REQUIREMENTS_CONFIG[self.requirement_key]['label']}** deve ser um número.", ephemeral=True)
                return

        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(self.giveaway_id, {})
        requirements = giveaway.setdefault("requirements", {})
        req_data = requirements.setdefault(self.requirement_key, {})

        req_data["enabled"] = True
        req_data["value"] = value if self.requirement_key not in numeric_fields else int(value)
        db.salvar("database/giveaways/giveaways_data.json", config)

        await inter.response.defer(ephemeral=True)
        await inter.followup.send(f"{emoji.correct} Requisito **{REQUIREMENTS_CONFIG[self.requirement_key]['label']}** definido para: `{value}`.", ephemeral=True)
        
        await log_giveaway_event(
            bot=inter.bot,
            giveaway_id=self.giveaway_id,
            title="Sorteios - Requisito Alterado",
            lines=[
                f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                f"{emoji.settings} **Requisito:** {REQUIREMENTS_CONFIG[self.requirement_key]['label']}",
                f"{emoji.edit} **Novo Valor:** `{value}`",
                f"{emoji.member} **Executor:** {inter.author.mention}"
            ]
        )
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await self.inter.edit_original_message(components=RequirementsView_components(self.inter, self.giveaway_id))
        else:
            embed, components = RequirementsView_embed(self.inter, self.giveaway_id)
            await self.inter.edit_original_message(embed=embed, components=components)

# --- Requirements Verification Functions ---

async def check_individual_requirement(member: disnake.Member, requirement_key: str, requirement_value: any, bot) -> tuple[bool, str]:
    """
    Verifica um requisito individual para um membro.
    Retorna (sucesso, mensagem_erro)
    """
    
    if requirement_key == "is_customer":
        # Verificar se é cliente (implementar lógica específica do seu sistema)
        # Por enquanto, sempre retorna True
        return True, ""
    
    elif requirement_key == "has_feedback":
        # Verificar se deixou feedback no canal de feedbacks
        try:
            channels_config = db.get_document("canais")
            feedback_channel_id = channels_config.get("canal_de_feedback")
            
            if not feedback_channel_id:
                return False, f"{emoji.wrong} O canal de feedbacks não foi configurado pelo administrador."
            
            feedback_channel = member.guild.get_channel(int(feedback_channel_id))
            if not feedback_channel:
                return False, f"{emoji.wrong} O canal de feedbacks configurado não foi encontrado ou está inacessível."
            
            # Verificar se o usuário tem mensagens no canal de feedbacks
            # Buscar mensagens do usuário no canal (limitado a 100 mensagens)
            async for message in feedback_channel.history(limit=100):
                if message.author.id == member.id:
                    return True, ""
            
            return False, f"{emoji.wrong} Você precisa deixar um feedback no canal {feedback_channel.mention} para participar."
            
        except Exception as e:
            return False, f"{emoji.wrong} Ocorreu um erro ao verificar seus feedbacks. Tente novamente."
    
    elif requirement_key == "is_oauth2_verified":
        # Verificar se é verificado via OAuth2
        return True, ""  # Implementar lógica específica
    
    elif requirement_key == "in_any_voice_channel":
        # Verificar se está em qualquer canal de voz
        if not member.voice:
            return False, f"{emoji.wrong} Você precisa estar conectado em um canal de voz para participar."
        return True, ""
    
    elif requirement_key == "is_voice_muted":
        # Verificar se está com microfone mutado
        if not member.voice:
            return False, f"{emoji.wrong} Você precisa estar conectado em um canal de voz para participar."
        if not member.voice.self_mute:
            return False, f"{emoji.wrong} Você precisa estar com o microfone mutado para participar."
        return True, ""
    
    elif requirement_key == "is_voice_deafened":
        # Verificar se está com fone desativado
        if not member.voice:
            return False, f"{emoji.wrong} Você precisa estar conectado em um canal de voz para participar."
        if not member.voice.self_deaf:
            return False, f"{emoji.wrong} Você precisa estar com o fone desativado (surdo) para participar."
        return True, ""
    
    elif requirement_key == "specific_voice_channel":
        # Verificar se está em canal específico
        if not member.voice:
            return False, f"{emoji.wrong} Você precisa estar conectado em um canal de voz para participar."
        
        # requirement_value agora é uma string com o ID do canal
        try:
            required_channel_id = int(requirement_value)
            if member.voice.channel.id != required_channel_id:
                channel = member.guild.get_channel(required_channel_id)
                channel_name = channel.name if channel else f"ID: {required_channel_id}"
                current_channel = member.voice.channel.name if member.voice.channel else "Nenhum"
                return False, f"{emoji.wrong} Você precisa estar no canal de voz **{channel_name}** (atualmente em **{current_channel}**)."
            return True, ""
        except (ValueError, TypeError):
            return False, f"{emoji.wrong} O ID do canal de voz configurado para o sorteio é inválido."
    
    elif requirement_key == "min_account_age_days":
        # Verificar idade mínima da conta
        account_age_days = (datetime.now(timezone.utc) - member.created_at).days
        if account_age_days < requirement_value:
            return False, f"{emoji.wrong} Sua conta precisa ter no mínimo **{requirement_value} dias** de idade (a sua tem **{account_age_days}**)."
        return True, ""
    
    elif requirement_key == "min_server_age_days":
        # Verificar tempo mínimo no servidor
        server_age_days = (datetime.now(timezone.utc) - member.joined_at).days
        if server_age_days < requirement_value:
            return False, f"{emoji.wrong} Você precisa estar no servidor há no mínimo **{requirement_value} dias** (você está há **{server_age_days}**)."
        return True, ""
    
    elif requirement_key == "min_invites":
        # Verificar convites mínimos
        convites_doc = db.get_document("convites")
        
        guild_id = str(member.guild.id)
        member_id = str(member.id)
        
        guild_data = convites_doc.get(guild_id, {})

        invites_data = guild_data.get("invites", {})
        
        member_invites = invites_data.get(member_id, {})
        
        total_invites = member_invites.get("valid", 0) + member_invites.get("bonus", 0)
        
        if total_invites < requirement_value:
            return False, f"{emoji.wrong} Você precisa de no mínimo **{requirement_value} convites** (você tem **{total_invites}**)."
        
        return True, ""
    
    elif requirement_key == "invited_by":
        # Verificar se foi convidado por alguém específico
        convites_doc = db.get_document("convites")

        guild_id = str(member.guild.id)
        member_id = str(member.id)

        guild_data = convites_doc.get(guild_id, {})

        members_data = guild_data.get("members", {})

        inviter_info = members_data.get(member_id, {})

        if "inviter" not in inviter_info:
            return False, f"{emoji.wrong} Não foi possível verificar quem te convidou para o servidor."

        inviter_id = inviter_info["inviter"]
        
        required_inviters = [inviter.strip() for inviter in str(requirement_value).split(",")]
        
        if inviter_id not in required_inviters:
            return False, f"{emoji.wrong} Você não foi convidado por um dos membros requeridos."
            
        return True, ""
    
    elif requirement_key == "custom_nickname":
        # Verificar nickname customizado com texto específico
        current_nick = member.nick or member.display_name
        if requirement_value.lower() not in current_nick.lower():
            return False, f'{emoji.wrong} Seu nickname/nome de exibição precisa conter "**{requirement_value}**" (atual: **{current_nick}**).'
        return True, ""
    
    elif requirement_key == "custom_status":
        # Verificar status customizado com texto específico
        custom_status = None
        for activity in member.activities:
            if activity.type == disnake.ActivityType.custom:
                custom_status = activity.name
                break
        
        if not custom_status:
            return False, f'{emoji.wrong} Seu status precisa conter "**{requirement_value}**" (você não tem um status customizado).'
        if requirement_value.lower() not in custom_status.lower():
            return False, f'{emoji.wrong} Seu status precisa conter "**{requirement_value}**" (atual: **{custom_status}**).'
        return True, ""
    
    elif requirement_key == "custom_bio":
        # Verificar bio customizada com texto específico usando API REST
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = f"https://discord.com/api/v10/users/{member.id}"
                headers = {
                    "Authorization": f"Bot {bot.http.token}",
                    "User-Agent": "DiscordBot (https://github.com/DisnakeDev/disnake)"
                }
                
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 401:
                        return False, f"{emoji.wrong} Erro de autorização: não consigo ler perfis de usuário."
                    elif resp.status == 403:
                        return False, f"{emoji.wrong} Acesso negado: não consigo ler seu perfil."
                    elif resp.status != 200:
                        return False, f"{emoji.wrong} Erro ({resp.status}) ao ler seu perfil. Tente novamente."
                    
                    data = await resp.json()
                    bio = data.get("bio")
                    
                    # Verificar se bio é None, string vazia, ou string "None"
                    is_bio_empty = (bio is None or 
                                  bio == "" or 
                                  bio == "None" or 
                                  (isinstance(bio, str) and bio.strip() == ""))
                    
                    if is_bio_empty:
                        # Tentar o endpoint de perfil do usuário no servidor
                        guild_profile_url = f"https://discord.com/api/v10/guilds/{member.guild.id}/members/{member.id}"
                        
                        async with session.get(guild_profile_url, headers=headers) as guild_resp:
                            if guild_resp.status == 200:
                                guild_data = await guild_resp.json()
                                guild_bio = guild_data.get("bio")
                                if guild_bio and guild_bio != "None" and guild_bio.strip():
                                    bio = guild_bio
                                else:
                                    return False, f'{emoji.wrong} Sua bio precisa conter "**{requirement_value}**" (você não tem uma bio configurada).'
                            else:
                                return False, f'{emoji.wrong} Sua bio precisa conter "**{requirement_value}**" (você não tem uma bio configurada).'
                    
                    bio_lower = bio.lower()
                    search_lower = requirement_value.lower()
                    found = search_lower in bio_lower
                    
                    if not found:
                        display_bio = bio[:100] + "..." if len(bio) > 100 else bio
                        return False, f'{emoji.wrong} Sua bio precisa conter "**{requirement_value}**" (atual: **{display_bio}**).'
                    
                    return True, ""
                    
        except aiohttp.ClientError as e:
            return False, f"{emoji.wrong} Erro de conexão ao verificar sua bio. Tente novamente."
        except Exception as e:
            return False, f"{emoji.wrong} Erro inesperado ao verificar sua bio. Tente novamente."
    
    elif requirement_key == "server_tag":
        # Verificar se o usuário está usando a tag de um servidor específico
        try:
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                url = f"https://discord.com/api/v10/users/{member.id}"
                headers = {
                    "Authorization": f"Bot {bot.http.token}",
                    "User-Agent": "DiscordBot (https://github.com/DisnakeDev/disnake)"
                }
                
                async with session.get(url, headers=headers) as resp:
                    if resp.status != 200:
                        if resp.status == 401:
                            return False, f"{emoji.wrong} Erro de autorização: não consigo ler perfis de usuário."
                        elif resp.status == 403:
                            return False, f"{emoji.wrong} Acesso negado: não consigo ler seu perfil."
                        else:
                            return False, f"{emoji.wrong} Erro ({resp.status}) ao ler seu perfil. Tente novamente."
                    
                    data = await resp.json()
                    
                    # Verificar se existe o campo clan (tag do servidor)
                    clan = data.get("clan")
                    if not clan:
                        return False, f"{emoji.wrong} Você precisa usar a tag de um servidor para participar (você não tem uma)."
                    
                    identity_guild_id = clan.get("identity_guild_id")
                    if not identity_guild_id:
                        return False, f"{emoji.wrong} Você precisa usar a tag de um servidor para participar (você não tem uma)."
                    
                    tag = clan.get("tag", "")
                    identity_enabled = clan.get("identity_enabled", False)
                    
                    # Verificar se o ID do servidor corresponde ao configurado
                    if str(identity_guild_id) != str(requirement_value):
                        return False, f"{emoji.wrong} Você precisa usar a tag do servidor **{requirement_value}** (você usa a do servidor **{identity_guild_id}**)."
                    
                    if not identity_enabled:
                        return False, f"{emoji.wrong} Você precisa habilitar a exibição da tag do servidor **{requirement_value}** para participar."
                    
                    return True, ""
                    
        except aiohttp.ClientError as e:
            return False, f"{emoji.wrong} Erro de conexão ao verificar sua tag do servidor. Tente novamente."
        except Exception as e:
            return False, f"{emoji.wrong} Erro inesperado ao verificar sua tag do servidor. Tente novamente."
    
    elif requirement_key == "first_purchase_days_ago":
        # Verificar primeira compra há X dias (implementar lógica específica)
        # Por enquanto, sempre retorna True
        return True, ""
    
    elif requirement_key == "custom_states_regions":
        # Verificar estados/regiões (implementar lógica específica)
        # Por enquanto, sempre retorna True
        return True, ""
    
    elif requirement_key == "custom_cities":
        # Verificar cidades (implementar lógica específica)
        # Por enquanto, sempre retorna True
        return True, ""
    
    elif requirement_key == "custom_countries":
        # Verificar países (implementar lógica específica)
        # Por enquanto, sempre retorna True
        return True, ""
    
    # Se não for reconhecido, permite participar
    return True, ""

def get_requirements_check_order():
    """
    Define a ordem de verificação dos requisitos.
    O primeiro requisito que falhar será reportado ao usuário.
    """
    return [
        # Requisitos básicos (só clicar)
        "is_customer",
        "is_oauth2_verified", 
        "in_any_voice_channel",
        "is_voice_muted",
        "is_voice_deafened",
        "has_feedback",
        
        # Requisitos com configuração específica
        "specific_voice_channel",
        "min_account_age_days",
        "min_server_age_days",
        "min_invites",
        "invited_by",
        "custom_nickname",
        "custom_status",
        "custom_bio",
        "server_tag"
    ]

async def check_giveaway_requirements(member: disnake.Member, giveaway_id: str, bot) -> tuple[bool, str]:
    """
    Verifica todos os requisitos de um sorteio para um membro.
    Retorna (sucesso, mensagem_erro)
    """
    giveaway_data = get_giveaways().get(giveaway_id, {})
    requirements = giveaway_data.get("requirements", {})
    
    # Obter ordem de verificação
    check_order = get_requirements_check_order()
    
    # Verificar cada requisito na ordem definida
    for req_key in check_order:
        req_data = requirements.get(req_key, {})
        
        # Se o requisito está habilitado
        if req_data.get("enabled", False):
            req_value = req_data.get("value")
            
            # Verificar o requisito
            success, error_message = await check_individual_requirement(
                member, req_key, req_value, bot
            )
            
            # Se falhou, retornar erro
            if not success:
                return False, error_message
    
    # Se todos os requisitos passaram
    return True, ""
