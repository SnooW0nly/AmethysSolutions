import disnake
from disnake.ext import commands
import logging
from functions.database import database as db
from modules.cloud.update_api import get_websocket_manager

logger = logging.getLogger(__name__)

class CloudEvents(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_member_join")
    async def on_member_join_persistent_auth(self, member: disnake.Member):
        try:
            cloud_config = db.get_document("cloud_data") or {}
            definitions = cloud_config.get("definitions", {})
            
            if not definitions.get("persistent_oauth2", {}).get("enabled", False):
                return

            logger.info(f"🔍 [PERSISTENT_AUTH] Verificando membro {member.name} ({member.id}) que entrou no servidor {member.guild.name}.")

            client_id = cloud_config.get("client_id")
            if not client_id:
                logger.warning("⚠️ [PERSISTENT_AUTH] Client ID do bot da cloud não configurado.")
                return

            ws_manager = get_websocket_manager()
            if not ws_manager.is_connected():
                logger.warning("⚠️ [PERSISTENT_AUTH] WebSocket não conectado. Impossível verificar o membro.")
                return

            response = await ws_manager.check_user_verification(client_id, member.id)
            
            if response.get("success") and response.get("data", {}).get("is_verified"):
                logger.info(f"✅ [PERSISTENT_AUTH] Membro {member.name} já é verificado. Atribuindo cargo.")
                
                cargos_config = db.get_document("cargos") or {}
                verified_role_id = cargos_config.get("cargo_verificado")
                if not verified_role_id:
                    logger.warning("⚠️ [PERSISTENT_AUTH] Cargo de verificado não configurado.")
                    return

                verified_role = member.guild.get_role(int(verified_role_id))
                if not verified_role:
                    logger.warning(f"⚠️ [PERSISTENT_AUTH] Cargo de verificado {verified_role_id} não encontrado.")
                    return
                
                if verified_role not in member.roles:
                    await member.add_roles(verified_role, reason="Verificação persistente via AmyCloud")
                    logger.info(f"✅ [PERSISTENT_AUTH] Cargo de verificado atribuído a {member.name}.")
            else:
                logger.info(f"ℹ️ [PERSISTENT_AUTH] Membro {member.name} não está na base de dados de verificação ou não é verificado.")

        except Exception as e:
            logger.error(f"❌ [PERSISTENT_AUTH] Erro ao processar on_member_join: {e}")

def setup(bot: commands.Bot):
    bot.add_cog(CloudEvents(bot))
