import disnake
from functions.emoji import emoji
from functions.database import database as db
from datetime import datetime
from .container_utils import ContainerUtils

# Set simples para rastrear logs já processados (evita duplicação)
# Compartilhado com update_api.py para evitar duplicação entre processamento e envio
_processed_logs = set()


async def send_auth_log(bot, auth_data: dict):
    """Envia log de autenticação para o canal configurado"""
    try:
        # Criar identificador único para o log baseado nos dados principais
        # Usar o mesmo formato que process_auth_log em update_api.py
        user_data = auth_data.get("user", {})
        user_id = user_data.get("id")
        verified_at = user_data.get("verified_at")
        unverified_at = user_data.get("unverified_at")
        
        # Identificar tipo de evento (verificação ou revogação)
        is_revocation = unverified_at is not None
        event_type = "revoke" if is_revocation else "verify"
        
        # Usar timestamp específico do evento para identificar o log
        timestamp = unverified_at if is_revocation else (verified_at or datetime.now().isoformat())
        log_id = f"{user_id}_{event_type}_{timestamp}"
        
        # Verificar se este log já foi processado
        # Também verificar no process_auth_log se estiver disponível
        if log_id in _processed_logs:
            print(f"🔄 Log duplicado ignorado em send_auth_log: {log_id}")
            return True, "Log duplicado ignorado"
        
        # Verificar também no process_auth_log se existir - REMOVIDO pois causava falso positivo
        # O process_auth_log já adiciona o ID antes de chamar esta função, o que fazia com que
        # esta verificação sempre retornasse verdadeiro, bloqueando o envio do log.
        # try:
        #     from .update_api import process_auth_log
        #     if hasattr(process_auth_log, '_processing') and log_id in process_auth_log._processing:
        #         print(f"🔄 Log duplicado ignorado (já processado): {log_id}")
        #         return True, "Log duplicado ignorado"
        # except Exception:
        #     pass
        
        # Adicionar à lista de logs processados ANTES de enviar (evitar race condition)
        _processed_logs.add(log_id)
        
        # Sincronizar com process_auth_log se disponível
        try:
            from .update_api import process_auth_log
            if not hasattr(process_auth_log, '_processing'):
                process_auth_log._processing = set()
            process_auth_log._processing.add(log_id)
        except Exception:
            pass
        
        # Limpar logs antigos (manter apenas os últimos 100)
        if len(_processed_logs) > 100:
            # Converter para lista, remover os mais antigos e converter de volta para set
            logs_list = list(_processed_logs)
            _processed_logs.clear()
            _processed_logs.update(logs_list[-50:])  # Manter apenas os últimos 50
        
        # Limpar também no process_auth_log se disponível
        try:
            from .update_api import process_auth_log
            if hasattr(process_auth_log, '_processing') and len(process_auth_log._processing) > 100:
                process_list = list(process_auth_log._processing)
                process_auth_log._processing.clear()
                process_auth_log._processing.update(process_list[-50:])
        except Exception:
            pass
        
        cloud_config = db.get_document("cloud_data") or {}
        log_channel_id = cloud_config.get("log_channel_id")
        
        if not log_channel_id:
            return False, "Canal de logs não configurado"
        
        channel = bot.get_channel(int(log_channel_id))
        if not channel:
            return False, "Canal de logs não encontrado"
        
        # Obter configuração de modo
        custom_mode = db.get_document("custom_mode") or {}
        mode = custom_mode.get("mode", "embed")
        
        if mode == "embed":
            await send_auth_log_embed(channel, auth_data)
        else:
            await send_auth_log_container(channel, auth_data)
        
        return True, "Log de auth enviado com sucesso"
        
    except Exception as e:
        return False, f"Erro ao enviar log de auth: {str(e)}"

async def send_auth_log_embed(channel: disnake.TextChannel, auth_data: dict):
    """Envia log de autenticação como embed"""
    user = auth_data.get("user", {})
    
    # Cores baseadas no status
    if auth_data.get("success"):
        color = 0x27ae60  # Verde para sucesso
        status_text = "Verificado com sucesso"
        title_emoji = emoji.shield
    else:
        color = 0xe74c3c  # Vermelho para falha/desverificação
        if "unverified_at" in user:
            status_text = "Desverificado"
            title_emoji = emoji.wrong
        else:
            status_text = "Falha na verificação"
            title_emoji = emoji.wrong
    
    embed = disnake.Embed(
        title=f"{title_emoji} Log de Autenticação",
        color=color,
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name=emoji.member + "**Usuário:**",
        value=f"**{user.get('username', 'N/A')}#{user.get('discriminator', '0000')}**\n`{user.get('id', 'N/A')}`",
        inline=True
    )
    
    embed.add_field(
        name=emoji.mail2 + "**Email:**",
        value=user.get('email', 'Não disponível'),
        inline=True
    )
    
    embed.add_field(
        name=emoji.wifi + "**IP:**",
        value=f"`{user.get('ip', 'Desconhecido')}`",
        inline=True
    )
    
    # Data/hora baseada no tipo de evento
    if "unverified_at" in user:
        timestamp_field = user.get('unverified_at', datetime.now().isoformat())
        field_name = emoji.clock + "**Desverificado em:**"
    else:
        timestamp_field = user.get('verified_at', datetime.now().isoformat())
        field_name = emoji.clock + "**Data/Hora:**"
    
    embed.add_field(
        name=field_name,
        value=f"<t:{int(datetime.fromisoformat(timestamp_field).timestamp())}:F>",
        inline=True
    )
    
    embed.add_field(
        name=emoji.correct + "**Status:**",
        value=status_text,
        inline=True
    )
    
    # Adicionar motivo se for desverificação
    if not auth_data.get("success") and "reason" in user:
        embed.add_field(
            name=emoji.edit + "**Motivo:**",
            value=user.get('reason', 'Desconhecido'),
            inline=True
        )
    
    # Botão para ver localização (apenas se tiver IP)
    view = disnake.ui.View()
    if user.get('ip') and user.get('ip') != 'Desconhecido':
        # Criar link direto para API de geolocalização
        ip_address = user.get('ip')
        location_url = f"https://ipinfo.io/{ip_address}"
        
        view.add_item(disnake.ui.Button(
            label="Ver Localização",
            style=disnake.ButtonStyle.link,
            emoji=emoji.location,
            url=location_url
        ))
    
    await channel.send(embed=embed, view=view)

async def send_auth_log_container(channel: disnake.TextChannel, auth_data: dict):
    """Envia log de autenticação como container"""
    user = auth_data.get("user", {})
    
    custom_colors = db.get_document("custom_colors") or {}
    color_hex = custom_colors.get("primary", "#5c5ef0") 
    
    # Logo Zenity completo
    zenity_logo = f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}"

    # Data/hora baseada no tipo de evento
    if "unverified_at" in user:
        timestamp_field = user.get('unverified_at', datetime.now().isoformat())
        time_label = "Desverificado em"
    else:
        timestamp_field = user.get('verified_at', datetime.now().isoformat())
        time_label = "Data/Hora"

    # Determinar se é verificação ou desverificação
    is_verified = auth_data.get("success") and "unverified_at" not in user
    
    if is_verified:
        # Container para Membro Verificado
        content = f"""{emoji.member} **Usuário**: <@{user.get('id', 'N/A')}> `{user.get('username', 'N/A')}`
{emoji.mail2} **Email**: {user.get('email', 'Não disponível')}
{emoji.wifi} **IP**: `{user.get('ip', 'Desconhecido')}`
{emoji.clock} **{time_label}**: <t:{int(datetime.fromisoformat(timestamp_field).timestamp())}:F>"""
        
        # Criar container usando ContainerUtils
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"""# {zenity_logo}\n-# Membro Verificado"""),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(content),
            accent_colour=disnake.Colour(int(color_hex.replace("#", ""), 16))
        )

        # Criar ActionRow com botão (apenas se tiver IP)
        if user.get('ip') and user.get('ip') != 'Desconhecido':
            # Criar link direto para API de geolocalização
            ip_address = user.get('ip')
            location_url = f"https://ipinfo.io/{ip_address}"
            
            button = disnake.ui.Button(
                label="Ver Localização",
                style=disnake.ButtonStyle.link,
                emoji=emoji.location,
                url=location_url
            )
            action_row = disnake.ui.ActionRow(button)
            
            # Enviar container e ActionRow separadamente (padrão do sistema)
            await channel.send(components=[container, action_row], flags=disnake.MessageFlags(is_components_v2=True))
        else:
            # Enviar apenas o container
            await channel.send(components=[container], flags=disnake.MessageFlags(is_components_v2=True))
    
    else:
        # Container para Membro Revogado (sem botão)
        content = f"""**Usuário**: <@{user.get('id', 'N/A')}> `{user.get('username', 'N/A')}`
**Email**: {user.get('email', 'Não disponível')}
**IP**: `{user.get('ip', 'Desconhecido')}`
**{time_label}**: <t:{int(datetime.fromisoformat(timestamp_field).timestamp())}:F>"""
        
        # Adicionar motivo se for desverificação
        if "reason" in user:
            content += f"\n**Motivo**: {user.get('reason', 'Desconhecido')}"
        
        # Criar container usando ContainerUtils
        container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"""# {zenity_logo}\n-# Membro Revogado"""),
            disnake.ui.Separator(),
            disnake.ui.TextDisplay(content),
            accent_colour=disnake.Colour(int(color_hex.replace("#", ""), 16))
        )

        # Enviar apenas o container (sem botão)
        await channel.send(components=[container], flags=disnake.MessageFlags(is_components_v2=True))


