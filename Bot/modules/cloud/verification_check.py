"""
Helper para verificar se usuário está verificado e mostrar mensagem de verificação quando necessário
"""
import disnake
from functions.database import database as db
from functions.utils import utils
from .container_utils import ContainerUtils


async def is_user_verified(member: disnake.Member) -> bool:
    """
    Verifica se o usuário está verificado consultando a API (database do bot)
    
    Args:
        member: Membro do Discord
        
    Returns:
        bool: True se o usuário está verificado na database, False caso contrário
    """
    try:
        # Obter configuração do cloud
        cloud_config = db.get_document("cloud_data") or {}
        bot_id = cloud_config.get("client_id")
        
        if not bot_id:
            # Se não há bot configurado, considerar como verificado (não bloquear)
            return True
        
        # Obter WebSocket manager (funciona via WS ou HTTP fallback)
        from .update_api import get_websocket_manager
        ws_manager = get_websocket_manager()
        
        # Consultar API para verificar se o usuário está verificado
        response = await ws_manager.check_user_verification(bot_id, member.id)
        
        if response.get("success"):
            is_verified = response.get("data", {}).get("is_verified", False)
            return bool(is_verified)
        else:
            # Se houver erro na consulta, considerar como verificado (não bloquear)
            error_msg = response.get('message', 'Erro desconhecido')
            # Não logar erro se WebSocket não está conectado (é esperado em alguns casos)
            if "não conectado" not in error_msg.lower() and "não foi possível enviar" not in error_msg.lower():
                print(f"Erro ao verificar usuário na API: {error_msg}")
            return True
        
    except Exception as e:
        print(f"Erro ao verificar se usuário está verificado: {e}")
        import traceback
        traceback.print_exc()
        # Em caso de erro, não bloquear o usuário
        return True


def get_verification_message_and_view(inter: "disnake.Interaction") -> tuple[str, "disnake.ui.View"] | tuple[None, None]:
    """
    Gera a mensagem e view (com botão de verificação) para quando o usuário não está verificado.
    
    Args:
        inter: Interação do Discord
        
    Returns:
        tuple: (message_text, view) ou (None, None) se não for possível gerar
    """
    try:
        # Verificar se há client_id configurado (necessário para funcionar)
        cloud_config = db.get_document("cloud_data") or {}
        client_id = cloud_config.get("client_id")
        if not client_id:
            return None, None
        
        # Gerar link de autenticação
        from .cloud_config import get_auth_callback_url
        redirect_uri = get_auth_callback_url()
        state = f"{client_id}-{inter.guild.id if inter.guild else '0'}"
        auth_url = (
            f"https://discord.com/api/oauth2/authorize?client_id={client_id}"
            f"&redirect_uri={redirect_uri}&response_type=code&scope=identify%20email%20guilds.join"
            f"&state={state}"
        )
        
        message_text = "Esse servidor requer que você seja verificado para usar algumas funcionalidades."
        button = disnake.ui.Button(
            label="Verificar",
            style=disnake.ButtonStyle.link,
            url=auth_url
        )
        
        view = disnake.ui.View(timeout=None)
        view.add_item(button)
        
        return message_text, view
        
    except Exception as e:
        print(f"Erro ao gerar mensagem de verificação: {e}")
        return None, None


def is_verification_required() -> bool:
    """
    Verifica se a opção 'Requerer Verificação OAuth2' está ativada nas preferências
    e se há client_id configurado (necessário para funcionar)
    
    Returns:
        bool: True se a verificação é obrigatória e está configurada, False caso contrário
    """
    try:
        cloud_config = db.get_document("cloud_data") or {}
        
        # Verificar se há client_id configurado (necessário para o checker funcionar)
        client_id = cloud_config.get("client_id")
        if not client_id:
            return False
        
        # Verificar se a opção está ativada
        definitions = cloud_config.get("definitions", {})
        return definitions.get("require_oauth2", {}).get("enabled", False)
        
    except Exception:
        return False


async def send_verification_required_message(inter: disnake.Interaction) -> bool:
    """
    Envia mensagem efêmera simples de verificação quando o usuário não está verificado
    
    Args:
        inter: Interação do Discord
        
    Returns:
        bool: True se a mensagem foi enviada, False caso contrário
    """
    try:
        # Verificar se a verificação é obrigatória
        if not is_verification_required():
            return False
        
        # Verificar se há client_id configurado (necessário para funcionar)
        cloud_config = db.get_document("cloud_data") or {}
        client_id = cloud_config.get("client_id")
        if not client_id:
            # Se não houver client_id, não enviar mensagem
            return False
        
        # Verificar se o usuário está verificado
        if isinstance(inter.user, disnake.Member):
            member = inter.user
        else:
            # Se não for Member, tentar obter do guild
            if inter.guild:
                member = inter.guild.get_member(inter.user.id)
                if not member:
                    # Se não conseguir obter o membro, não bloquear
                    return False
            else:
                return False
        
        # Verificar se o usuário está verificado (função agora é async)
        verified = await is_user_verified(member)
        if verified:
            return False
        
        # Gerar link de autenticação
        from .cloud_config import get_auth_callback_url
        redirect_uri = get_auth_callback_url()
        state = f"{client_id}-{inter.guild.id if inter.guild else '0'}"
        auth_url = (
            f"https://discord.com/api/oauth2/authorize?client_id={client_id}"
            f"&redirect_uri={redirect_uri}&response_type=code&scope=identify%20email%20guilds.join"
            f"&state={state}"
        )
        
        message_text = "Esse servidor requer que você seja verificado para usar algumas funcionalidades."
        button = disnake.ui.Button(
            label="Verificar",
            style=disnake.ButtonStyle.link,
            url=auth_url
        )
        
        # Enviar mensagem simples com botão
        view = disnake.ui.View(timeout=None)
        view.add_item(button)
        
        if inter.response.is_done():
            await inter.followup.send(
                message_text,
                ephemeral=True,
                view=view
            )
        else:
            await inter.response.send_message(
                message_text,
                ephemeral=True,
                view=view
            )
        
        return True
        
    except Exception as e:
        print(f"Erro ao enviar mensagem de verificação obrigatória: {e}")
        import traceback
        traceback.print_exc()
        return False

