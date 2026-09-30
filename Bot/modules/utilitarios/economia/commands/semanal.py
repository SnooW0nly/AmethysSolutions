import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class WeeklyCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="weekly", aliases=["semanal"])
    async def weekly(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("weekly"):
            return

        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        user_id = ctx.author.id
        remaining = EconomyHelper.check_cooldown(user_id, "weekly")
        if remaining > 0:
            await ctx.reply(
                f"{emoji.wrong} Você já resgatou seu weekly! "
                f"Volte em `{EconomyHelper.format_cooldown(remaining)}`."
            )
            return

        cfg    = EconomyHelper.get_economy_settings().get("weekly", {})
        reward = random.randint(cfg.get("min_reward", 1000), cfg.get("max_reward", 3000))
        EconomyHelper.add_user_coins(user_id, reward)
        EconomyHelper.set_cooldown(user_id, "weekly")

        balance = EconomyHelper.get_user_coins(user_id)
        cur     = EconomyHelper.get_currency_display()

        await ctx.reply(
            f"📆 **Weekly resgatado!**\n"
            f"💰 Você ganhou **{reward:,}** {cur}!\n"
            f"-# Saldo atual: {balance:,}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(WeeklyCommand(bot))
