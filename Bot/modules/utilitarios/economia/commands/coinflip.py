import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class CoinflipCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="coinflip", aliases=["cf", "moeda", "flip"])
    async def coinflip(self, ctx: commands.Context, choice: str = None, bet: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("coinflip"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cfg = EconomyHelper.get_economy_settings().get("coinflip", {})
        min_bet = cfg.get("min_bet", 10)
        max_bet = cfg.get("max_bet", 10000)
        cur = EconomyHelper.get_currency_display()

        if choice is None or bet is None:
            await ctx.reply(
                f"{emoji.wrong} Use: `coinflip <cara/coroa> <aposta>`\n"
                f"Ex: `coinflip cara 500` | Aposta: `{min_bet:,}` a `{max_bet:,}`"
            )
            return

        choice_lower = choice.lower()
        valid = {"cara": "cara", "coroa": "coroa", "heads": "cara", "tails": "coroa", "c": "cara", "k": "coroa"}
        if choice_lower not in valid:
            await ctx.reply(f"{emoji.wrong} Escolha `cara` ou `coroa`.")
            return
        choice_norm = valid[choice_lower]

        try:
            bet_int = int(bet.replace(",", "").replace(".", ""))
            if bet_int <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Valor de aposta inválido.")
            return

        if bet_int < min_bet or bet_int > max_bet:
            await ctx.reply(
                f"{emoji.wrong} Aposta fora do limite. "
                f"Min: `{min_bet:,}` | Max: `{max_bet:,}`"
            )
            return

        user_coins = EconomyHelper.get_user_coins(ctx.author.id)
        if user_coins < bet_int:
            await ctx.reply(
                f"{emoji.wrong} Saldo insuficiente. "
                f"Saldo: `{user_coins:,}` | Aposta: `{bet_int:,}`"
            )
            return

        result = random.choice(["cara", "coroa"])
        result_emoji = "🪙" if result == "cara" else "👑"

        if result == choice_norm:
            EconomyHelper.add_user_coins(ctx.author.id, bet_int)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"{result_emoji} Caiu **{result}**! Você acertou e ganhou **{bet_int:,}** {cur}!\n"
                f"-# Saldo atual: {balance:,}"
            )
        else:
            EconomyHelper.remove_user_coins(ctx.author.id, bet_int)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"{result_emoji} Caiu **{result}**! Você errou e perdeu **{bet_int:,}** {cur}.\n"
                f"-# Saldo atual: {balance:,}"
            )


def setup(bot: commands.Bot):
    bot.add_cog(CoinflipCommand(bot))