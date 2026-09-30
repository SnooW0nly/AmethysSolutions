import disnake
from disnake.ext import commands
from functions.database import database as db
from modules.automations.response_auto.helpers import truncar_para_mensagem
import re

class ResponseAutoTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if not message.guild or message.author.bot:
            return

        config = db.get_document("automations_response_auto")

        if not config or not config.get("status") or not message.content:
            return

        content_lower = message.content.lower()
        responses = config.get("responses", [])
        for resp in responses:
            keyword_lower = resp["keyword"].lower()
            if re.search(r'\b' + re.escape(keyword_lower) + r'\b', content_lower):
                # Truncar resposta para garantir limites do Discord
                response_text = truncar_para_mensagem(resp['response'])
                
                if resp["ephemeral"]:
                    try:
                        # Truncar também a mensagem completa da DM
                        mensagem_dm = f"**Sua mensagem em {message.channel.mention} acionou uma resposta automática:**\n\n{response_text}"
                        mensagem_dm_truncada = truncar_para_mensagem(mensagem_dm)
                        await message.author.send(mensagem_dm_truncada)
                        await message.channel.send("Verifique sua DM.", reference=message, mention_author=False, delete_after=5)
                    except disnake.Forbidden:
                        await message.channel.send("Eu tentei te enviar uma DM, mas elas estão desativadas.", ephemeral=True, delete_after=10)
                else:
                    try:
                        await message.channel.send(response_text, reference=message, mention_author=False)
                    except disnake.HTTPException:
                         await message.channel.send(response_text, mention_author=False)

def setup(bot: commands.Bot):
    bot.add_cog(ResponseAutoTaskCog(bot))
