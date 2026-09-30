import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji
import random

class InteractionsCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_handler(self, ctx, target, action_type, verb, emoji_str, gif_list=None):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        if target is None:
            await ctx.reply(f"{emoji.wrong} Mencione alguém para {action_type}!")
            return

        if target.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Você não pode {action_type} a si mesmo.")
            return

        # Incrementar contador
        EconomyHelper.add_interaction(ctx.author.id, action_type)
        user_data = EconomyHelper.get_social_data(ctx.author.id)
        count = user_data.get("interactions", {}).get(action_type, 0)

        embed = disnake.Embed(
            description=f"{emoji_str} **{ctx.author.display_name}** {verb} **{target.display_name}**!",
            color=0x2B2D31
        )
        if gif_list:
            embed.set_image(url=random.choice(gif_list))
        
        embed.set_footer(text=f"Você já {verb} outras pessoas {count} vezes.")
        await ctx.reply(embed=embed)

    @commands.command(name="beijar", aliases=["kiss"])
    async def kiss(self, ctx: commands.Context, target: disnake.Member = None):
        gifs = [
            "https://i.imgur.com/39A1f4u.gif", "https://i.imgur.com/Gf76S9t.gif",
            "https://i.imgur.com/W6Gv7q6.gif", "https://i.imgur.com/lmYid9h.gif"
        ]
        await self.interaction_handler(ctx, target, "beijar", "beijou", "💋", gifs)

    @commands.command(name="abracar", aliases=["hug", "abraçar"])
    async def hug(self, ctx: commands.Context, target: disnake.Member = None):
        gifs = [
            "https://i.imgur.com/r9aU2xv.gif", "https://i.imgur.com/v47MbeW.gif",
            "https://i.imgur.com/6q6vX6z.gif", "https://i.imgur.com/348hS98.gif"
        ]
        await self.interaction_handler(ctx, target, "abracar", "abraçou", "🫂", gifs)

    @commands.command(name="tapa", aliases=["slap", "tapar"])
    async def slap(self, ctx: commands.Context, target: disnake.Member = None):
        gifs = [
            "https://i.imgur.com/9v6N99p.gif", "https://i.imgur.com/V7Yq7lB.gif",
            "https://i.imgur.com/f9WvH3K.gif", "https://i.imgur.com/mIg8erJ.gif"
        ]
        await self.interaction_handler(ctx, target, "tapa", "deu um tapa em", "🖐️", gifs)

    @commands.command(name="cafune", aliases=["pat", "cafuné"])
    async def pat(self, ctx: commands.Context, target: disnake.Member = None):
        gifs = [
            "https://i.imgur.com/UWb7MUp.gif", "https://i.imgur.com/79A7v7a.gif",
            "https://i.imgur.com/2lacm7y.gif", "https://i.imgur.com/U6f966F.gif"
        ]
        await self.interaction_handler(ctx, target, "cafune", "fez cafuné em", "💆", gifs)

def setup(bot: commands.Bot):
    bot.add_cog(InteractionsCommand(bot))
