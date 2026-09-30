import disnake
import aiohttp
from functions.emoji import emoji
from functions.database import database as db


def get_ws_status_text() -> str:
    """
    Retorna uma linha de texto descrevendo o estado atual da conexão WebSocket
    com a API AmyCloud.

    Possíveis estados:
    - Conectado   → exibe o host extraído da URL do servidor.
    - Reconectando → exibe a tentativa atual e o backoff estimado.
    - Desconectado → indica que o bot não está conectado à API.
    """
    try:
        from .update_api import get_websocket_manager
        ws_manager = get_websocket_manager()

        if ws_manager is None:
            return f"{emoji.off} **WebSocket:** `Não iniciado`"

        # Acessar o WSManager interno (atributo _ws do wrapper)
        ws = getattr(ws_manager, "_ws", None)
        if ws is None:
            return f"{emoji.off} **WebSocket:** `Não iniciado`"

        if ws.is_connected():
            # Extrair hostname da URL para exibição amigável
            server_url = getattr(ws, "server_url", None) or "API"
            try:
                # Remover schema (wss:// ou ws://) para exibir apenas o host
                host = server_url.split("//")[-1].split("/")[0]
            except Exception:
                host = server_url
            return f"{emoji.on} **WebSocket:** `Conectado` — `{host}`"

        attempts = getattr(ws, "reconnect_attempts", 0)
        interval = getattr(ws, "reconnect_interval", 3)
        if attempts > 0:
            # Calcular backoff estimado (mesmo cálculo de ws_manager.py)
            import math
            wait = min(interval * (1.5 ** (attempts - 1)), 60)
            return (
                f"{emoji.loading} **WebSocket:** `Reconectando…` "
                f"— tentativa `{attempts}` — próxima em `{wait:.0f}s`"
            )

        return f"{emoji.off} **WebSocket:** `Desconectado`"

    except Exception as e:
        print(f"[helpers] Erro ao obter status do WebSocket: {e}")
        return f"{emoji.off} **WebSocket:** `Indisponível`"


async def get_status_text(inter: disnake.Interaction):
    cloud_config = db.get_document("cloud_data") or {}
    is_configured = bool(cloud_config.get("client_id"))
    verified_members = 0
    
    log_channel_id = cloud_config.get("log_channel_id")
    logs_channel = f"<#{log_channel_id}>" if log_channel_id else "`Não definido`"
    
    cargos_config = db.get_document("cargos") or {}
    verified_role_id = cargos_config.get("cargo_verificado")
    verified_role_mention = f"<@&{verified_role_id}>" if verified_role_id else "`Não definido`"

    if is_configured:
        try:
            from .auth_counter import get_auth_count
            verified_members = await get_auth_count()
        except Exception as e:
            print(f"Erro ao obter contagem de membros em helpers: {e}")
            pass

    status_emoji = emoji.on if is_configured else emoji.off
    status_label = "`Configurado`" if is_configured else "`Não Configurado`"
    ws_status = get_ws_status_text()

    return (
        f"{status_emoji} **Status:** {status_label}\n"
        f"{ws_status}\n"
        f"{emoji.members} **Membros Verificados:** `{verified_members}`\n"
        f"{emoji.textc} **Canal de Logs:** {logs_channel}\n"
        f"{emoji.role} **Cargo de Verificado:** {verified_role_mention}"
    )


class LogChannelModal(disnake.ui.Modal):
    def __init__(self, bot, current_channel_id: str = ""):
        self.bot = bot
        components = [
            disnake.ui.Label(
                text="Selecione o Canal de Logs",
                component=disnake.ui.ChannelSelect(
                    placeholder="Escolha um canal de texto",
                    custom_id="log_channel_select",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                ),
                description="O AmyCloud usará este canal para enviar os logs de verificação.",
            ),
        ]
        super().__init__(title="Definir Canal de Logs", components=components, custom_id="log_channel_modal")

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            valores = inter.resolved_values
            selected = valores.get("log_channel_select")
            # Normalize selection to a string channel ID
            if isinstance(selected, (list, tuple)):
                selected = selected[0] if selected else None
            if isinstance(selected, (str, int)):
                log_channel_id = str(selected)
            elif hasattr(selected, "id"):
                # Likely a channel object
                try:
                    log_channel_id = str(int(selected.id))
                except Exception:
                    log_channel_id = None
            else:
                log_channel_id = None

            cloud_cog = self.bot.get_cog("Cloud")
            if cloud_cog:
                await cloud_cog.process_log_channel(inter, log_channel_id)
            else:
                if not inter.response.is_done():
                    await inter.response.send_message("Erro: Mensagem não encontrada", ephemeral=True)
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(f"Erro ao processar modal: {str(e)}", ephemeral=True)
