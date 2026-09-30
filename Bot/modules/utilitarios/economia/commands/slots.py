import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class SlotsCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="slots", aliases=["slot", "cassino", "girar"])
    async def slots(self, ctx: commands.Context, bet: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("slots"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cfg = EconomyHelper.get_economy_settings().get("slots", {})
        min_bet = cfg.get("min_bet", 10)
        max_bet = cfg.get("max_bet", 5000)
        cur = EconomyHelper.get_currency_display()

        if bet is None:
            await ctx.reply(
                f"{emoji.wrong} Use: `slots <aposta>`\n"
                f"Aposta: `{min_bet:,}` a `{max_bet:,}`"
            )
            return

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
                f"{emoji.wrong} Você não tem coins suficientes. "
                f"Saldo: `{user_coins:,}` | Aposta: `{bet_int:,}`"
            )
            return

        symbols = cfg.get("symbols", ["🍒", "🍋", "🍊", "🍇", "⭐", "💎"])
        jackpot_sym = symbols[-1]  # 💎 é o jackpot
        reels = [random.choice(symbols) for _ in range(3)]

        # Calcular resultado
        EconomyHelper.remove_user_coins(ctx.author.id, bet_int)

        if reels[0] == reels[1] == reels[2]:
            if reels[0] == jackpot_sym:
                mult = cfg.get("jackpot_multiplier", 15.0)
                result_txt = f"🎉 **JACKPOT!!!** `{mult}x`"
            else:
                mult = cfg.get("three_match_multiplier", 5.0)
                result_txt = f"🎊 **TRÊS IGUAIS!** `{mult}x`"
            winnings = int(bet_int * mult)
            EconomyHelper.add_user_coins(ctx.author.id, winnings)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"🎰 **[ {' | '.join(reels)} ]**\n"
                f"{result_txt} — Você ganhou **{winnings:,}** {cur}!\n"
                f"-# Saldo atual: {balance:,}"
            )
        elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
            mult = cfg.get("two_match_multiplier", 1.5)
            winnings = int(bet_int * mult)
            EconomyHelper.add_user_coins(ctx.author.id, winnings)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"🎰 **[ {' | '.join(reels)} ]**\n"
                f"✨ **DOIS IGUAIS!** `{mult}x` — Você ganhou **{winnings:,}** {cur}!\n"
                f"-# Saldo atual: {balance:,}"
            )
        else:
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"🎰 **[ {' | '.join(reels)} ]**\n"
                f"😢 Sem sorte! Você perdeu **{bet_int:,}** {cur}.\n"
                f"-# Saldo atual: {balance:,}"
            )


def setup(bot: commands.Bot):
    bot.add_cog(SlotsCommand(bot))