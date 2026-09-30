import disnake
import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

class SocialCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ship", aliases=["love"])
    async def ship(self, ctx: commands.Context, user1: disnake.Member = None, user2: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        if user1 is None:
            await ctx.reply(f"{emoji.wrong} Mencione pelo menos um usuário!")
            return

        if user2 is None:
            user2 = user1
            user1 = ctx.author

        if user1.id == user2.id:
            await ctx.reply(f"{emoji.wrong} Você não pode shipar uma pessoa com ela mesma!")
            return

        # Calcular porcentagem baseada nos IDs para ser consistente no mesmo dia
        seed = int(user1.id) + int(user2.id) + int(random.randint(0, 100)) # Semente aleatória simples
        random.seed(seed)
        percent = random.randint(0, 100)
        random.seed() # Resetar seed

        # Gerar barra de progresso
        bar_length = 10
        filled = int(percent / bar_length)
        bar = "❤️" * filled + "🖤" * (bar_length - filled)

        # Determinar comentário
        if percent < 20: comment = "💔 Melhor nem tentar..."
        elif percent < 50: comment = "📉 Amizade colorida?"
        elif percent < 80: comment = "❤️ Tem futuro!"
        else: comment = "💍 Casal perfeito!"

        embed = disnake.Embed(
            title="💞 Máquina do Amor",
            description=f"**{user1.display_name}** + **{user2.display_name}**\n\n"
                        f"**{percent}%** [{bar}]\n\n"
                        f"{comment}",
            color=0xFF69B4
        )
        await ctx.reply(embed=embed)

    @commands.command(name="bff", aliases=["melhoramigo"])
    async def bff(self, ctx: commands.Context, target: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        if target is None:
            await ctx.reply(f"{emoji.wrong} Mencione seu melhor amigo!")
            return

        if target.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Você não pode ser seu próprio BFF.")
            return

        percent = random.randint(0, 100)
        bar_length = 10
        filled = int(percent / bar_length)
        bar = "⭐" * filled + "⚪" * (bar_length - filled)

        embed = disnake.Embed(
            title="⭐ Nível de Amizade (BFF)",
            description=f"**{ctx.author.display_name}** e **{target.display_name}**\n\n"
                        f"**{percent}%** [{bar}]\n\n"
                        f"{'🤞 Inseparáveis!' if percent > 80 else '🤝 Bons amigos!'}",
            color=0xFFA500
        )
        await ctx.reply(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(SocialCommand(bot))
