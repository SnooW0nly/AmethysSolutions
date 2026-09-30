import random
import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class DailyCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="daily", aliases=["diario"])
    async def daily(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("daily"):
            return

        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        user_id = ctx.author.id
        remaining = EconomyHelper.check_cooldown(user_id, "daily")
        if remaining > 0:
            await ctx.reply(
                f"{emoji.wrong} Você já resgatou seu daily! "
                f"Tente novamente em `{EconomyHelper.format_cooldown(remaining)}`."
            )
            return

        cfg   = EconomyHelper.get_economy_settings().get("daily", {})
        min_r = cfg.get("min_reward", 100)
        max_r = cfg.get("max_reward", 500)
        reward = random.randint(min_r, max_r)

        streak = EconomyHelper.update_streak(user_id, "daily")
        streak_bonus = 0
        streak_text = ""
        if cfg.get("streak_bonus", True) and streak > 1:
            streak_mult = cfg.get("streak_multiplier", 0.1)
            max_days    = cfg.get("max_streak_days", 30)
            bonus_pct   = min(streak * streak_mult, max_days * streak_mult)
            streak_bonus = int(reward * bonus_pct)
            streak_text = f"\n🔥 **Streak:** {streak} dias consecutivos! (+{streak_bonus:,} bônus)"

        total = EconomyHelper.add_user_coins(user_id, reward + streak_bonus)
        EconomyHelper.set_cooldown(user_id, "daily")

        balance = EconomyHelper.get_user_coins(user_id)
        cur     = EconomyHelper.get_currency_display()

        await ctx.reply(
            f"📅 **Daily resgatado!**\n"
            f"💰 Você ganhou **{reward:,}** {cur}!{streak_text}\n"
            f"-# Saldo atual: {balance:,}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(DailyCommand(bot))
