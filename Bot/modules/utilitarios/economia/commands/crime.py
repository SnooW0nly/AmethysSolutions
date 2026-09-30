import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class CrimeCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="crime", aliases=["crimar"])
    async def crime(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("crime"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        user_id = ctx.author.id
        remaining = EconomyHelper.check_cooldown(user_id, "crime")
        if remaining > 0:
            await ctx.reply(
                f"{emoji.wrong} Fique baixo por mais `{EconomyHelper.format_cooldown(remaining)}`."
            )
            return

        cfg = EconomyHelper.get_economy_settings().get("crime", {})
        chance = cfg.get("success_chance", 60)
        cur = EconomyHelper.get_currency_display()
        EconomyHelper.set_cooldown(user_id, "crime")

        if random.randint(1, 100) <= chance:
            # Sucesso
            reward = random.randint(cfg.get("min_reward", 200), cfg.get("max_reward", 1000))
            msg = random.choice(cfg.get("success_messages", ["Você cometeu um crime"]))
            EconomyHelper.add_user_coins(user_id, reward, reason="Crime bem-sucedido")
            balance = EconomyHelper.get_user_coins(user_id)
            await ctx.reply(
                f"🔫 **{msg}** e fugiu com **{reward:,}** {cur}!\n"
                f"-# Saldo atual: {balance:,}"
            )
        else:
            # Falha
            fine = random.randint(cfg.get("fine_min", 100), cfg.get("fine_max", 400))
            msg = random.choice(cfg.get("fail_messages", ["Você foi pego pela polícia"]))
            removed = EconomyHelper.remove_user_coins(user_id, fine, reason="Multa por crime")
            balance = EconomyHelper.get_user_coins(user_id)
            fine_txt = f"**{fine:,}** {cur} de multa" if removed else "mas estava sem dinheiro para pagar a multa"
            await ctx.reply(
                f"👮 **{msg}** e pagou {fine_txt}!\n"
                f"-# Saldo atual: {balance:,}"
            )


def setup(bot: commands.Bot):
    bot.add_cog(CrimeCommand(bot))