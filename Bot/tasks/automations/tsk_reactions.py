import disnake
from disnake.ext import commands
from modules.automations.reactions.helpers import ReacoesDB

class ReactionsTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = ReacoesDB()

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if message.author.bot or not self.db.get_status():
            return

        reactions = self.db.get_reactions()
        for reaction in reactions:
            reaction_type = reaction.get("type")
            value = reaction.get("value")
            emoji = reaction.get("emoji")

            should_react = False
            if reaction_type == "channel":
                # Convert both to int for comparison to handle JSON string/int issues
                try:
                    if int(value) == message.channel.id:
                        should_react = True
                except (ValueError, TypeError):
                    pass
            elif reaction_type == "keyword":
                if message.content and isinstance(value, str) and value.lower() in message.content.lower():
                    should_react = True
            
            if should_react:
                try:
                    await message.add_reaction(emoji)
                except disnake.HTTPException as e:
                    # Log error for debugging (emoji might be invalid or bot lacks permissions)
                    print(f"[Reactions] Failed to add reaction '{emoji}' to message {message.id}: {e}")
                except Exception as e:
                    # Catch any other errors (invalid emoji format, etc.)
                    print(f"[Reactions] Unexpected error adding reaction '{emoji}': {e}")

def setup(bot: commands.Bot):
    bot.add_cog(ReactionsTaskCog(bot))
