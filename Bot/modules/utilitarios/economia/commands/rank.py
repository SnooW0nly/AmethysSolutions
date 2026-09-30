from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

MEDALS = ["🥇", "🥈", "🥉"]


class LeaderboardCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="leaderboard", aliases=["ranking", "top", "lb"])
    async def leaderboard(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("leaderboard"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        top = EconomyHelper.get_leaderboard(10)
        if not top:
            await ctx.reply(f"{emoji.wrong} Nenhum usuário encontrado no ranking.")
            return

        cur_name = EconomyHelper.get_currency_name()
        cur_em = EconomyHelper.get_currency_emoji()
        lines = [f"# 🏆 Top 10 — {cur_em} {cur_name}\n"]

        for i, (uid, coins) in enumerate(top):
            medal = MEDALS[i] if i < 3 else f"`#{i+1}`"
            try:
                user = ctx.guild.get_member(int(uid)) or await ctx.guild.fetch_member(int(uid))
                name = user.display_name
            except Exception:
                name = f"Usuário #{uid}"
            lines.append(f"{medal} **{name}** — `{coins:,}` {cur_name}")

        # Posição do autor
        all_data = EconomyHelper.get_leaderboard(9999)
        user_pos = next((i + 1 for i, (uid, _) in enumerate(all_data) if uid == str(ctx.author.id)), None)
        author_coins = EconomyHelper.get_user_coins(ctx.author.id)
        if user_pos:
            lines.append(f"\n-# Sua posição: #{user_pos} com `{author_coins:,}` {cur_name}")

        await ctx.reply("\n".join(lines))


def setup(bot: commands.Bot):
    bot.add_cog(LeaderboardCommand(bot))