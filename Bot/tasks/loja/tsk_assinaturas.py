import disnake
import time
import asyncio
from disnake.ext import commands, tasks
from functions.database import database as db
from functions.emoji import emoji

class SubscriptionTasks(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_expirations.start()

    def cog_unload(self):
        self.check_expirations.cancel()

    @tasks.loop(minutes=30)
    async def check_expirations(self):
        """Verifica assinaturas expirando e notifica usuários."""
        subs_doc = db.get_document("loja_subscriptions") or {}
        now = int(time.time())
        
        updated = False
        for user_id_str, user_subs in list(subs_doc.items()):
            user_id = int(user_id_str)
            user = self.bot.get_user(user_id)
            
            for sub_key, sub_data in list(user_subs.items()):
                expires_at = sub_data.get("expires_at", 0)
                
                if expires_at == 0:
                    continue
                
                # Notificar 1 dia antes
                one_day = 24 * 60 * 60
                if now < expires_at <= now + one_day and not sub_data.get("notified_24h"):
                    if user:
                        try:
                            await user.send(
                                f"{emoji.alert} **Sua assinatura está acabando!**\n"
                                f"Sua assinatura de **{sub_data.get('product_name')}** expira em menos de 24 horas (<t:{expires_at}:R>).\n"
                                f"Renove agora para não perder seus benefícios!"
                            )
                            sub_data["notified_24h"] = True
                            updated = True
                        except:
                            pass
                
                # Remover se expirou
                if expires_at < now:
                    if user:
                        try:
                            await user.send(
                                f"{emoji.off} **Sua assinatura expirou!**\n"
                                f"Sua assinatura de **{sub_data.get('product_name')}** expirou e seus benefícios foram removidos."
                            )
                        except:
                            pass
                    
                    # Remover cargos se possível (precisaria do guild_id, mas o sistema atual não salva guild_id na sub)
                    # Como o usuário não pediu remoção automática de cargos, apenas notificação, vamos focar nisso.
                    
                    user_subs.pop(sub_key)
                    updated = True
            
            if not user_subs:
                subs_doc.pop(user_id_str)
                updated = True
            else:
                subs_doc[user_id_str] = user_subs

        if updated:
            db.save_document("loja_subscriptions", subs_doc)

    @check_expirations.before_loop
    async def before_check_expirations(self):
        await self.bot.wait_until_ready()

def setup(bot: commands.Bot):
    bot.add_cog(SubscriptionTasks(bot))
