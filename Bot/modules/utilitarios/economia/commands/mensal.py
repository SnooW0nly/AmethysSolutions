import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class MonthlyCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="monthly", aliases=["mensal"])
    async def monthly(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("monthly"):
            return

        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        user_id = ctx.author.id
        remaining = EconomyHelper.check_cooldown(user_id, "monthly")
        if remaining > 0:
            await ctx.reply(
                f"{emoji.wrong} Você já resgatou seu monthly! "
                f"Volte em `{EconomyHelper.format_cooldown(remaining)}`."
            )
            return

        cfg    = EconomyHelper.get_economy_settings().get("monthly", {})
        reward = random.randint(cfg.get("min_reward", 5000), cfg.get("max_reward", 15000))
        EconomyHelper.add_user_coins(user_id, reward)
        EconomyHelper.set_cooldown(user_id, "monthly")

        balance = EconomyHelper.get_user_coins(user_id)
        cur     = EconomyHelper.get_currency_display()

        await ctx.reply(
            f"🗓️ **Monthly resgatado!**\n"
            f"💰 Você ganhou **{reward:,}** {cur}!\n"
            f"-# Saldo atual: {balance:,}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(MonthlyCommand(bot))
