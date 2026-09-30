import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class HourlyCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="hourly", aliases=["hora", "recompensa_hora"])
    async def hourly(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("hourly"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        user_id = ctx.author.id
        remaining = EconomyHelper.check_cooldown(user_id, "hourly")
        if remaining > 0:
            await ctx.reply(
                f"{emoji.wrong} Aguarde `{EconomyHelper.format_cooldown(remaining)}` para resgatar a próxima hora!"
            )
            return

        cfg = EconomyHelper.get_economy_settings().get("hourly", {"min_reward": 30, "max_reward": 120, "cooldown": 3600})
        reward_raw = random.randint(cfg.get("min_reward", 30), cfg.get("max_reward", 120))
        reward = EconomyHelper.add_user_coins(user_id, reward_raw, reason="Recompensa Hourly", member=ctx.author)
        EconomyHelper.set_cooldown(user_id, "hourly")

        streak = EconomyHelper.update_streak(user_id, "hourly")
        streak_line = f"\n🔥 **Streak:** {streak} hora{'s' if streak != 1 else ''}!" if streak > 1 else ""

        balance = EconomyHelper.get_user_coins(user_id)
        cur = EconomyHelper.get_currency_display()
        await ctx.reply(
            f"⏰ Você resgatou sua recompensa de hora!\n"
            f"💰 **+{reward:,}** {cur}{streak_line}\n"
            f"-# Saldo atual: {balance:,}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(HourlyCommand(bot))
