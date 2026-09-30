import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

class BankCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="dep", aliases=["depositar"])
    async def deposit(self, ctx: commands.Context, amount: str = None):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        user_id = ctx.author.id
        user_coins = EconomyHelper.get_user_coins(user_id)
        cur = EconomyHelper.get_currency_display()

        if amount is None:
            await ctx.reply(f"{emoji.wrong} Informe a quantia para depositar ou use `dep all`.")
            return

        if amount.lower() == "all":
            final_amount = user_coins
        else:
            try:
                final_amount = int(amount)
            except ValueError:
                await ctx.reply(f"{emoji.wrong} Quantia inválida.")
                return

        if final_amount <= 0:
            await ctx.reply(f"{emoji.wrong} A quantia deve ser maior que zero.")
            return

        if user_coins < final_amount:
            await ctx.reply(f"{emoji.wrong} Você não tem coins suficientes em mãos.")
            return

        if EconomyHelper.deposit_coins(user_id, final_amount):
            bank_bal = EconomyHelper.get_user_bank(user_id)
            await ctx.reply(
                f"{emoji.success} Você depositou **{final_amount:,}** {cur} no banco!\n"
                f"-# Saldo no banco: **{bank_bal:,}**"
            )
        else:
            await ctx.reply(f"{emoji.wrong} Ocorreu um erro ao processar o depósito.")

    @commands.command(name="sacar", aliases=["withdraw", "saque"])
    async def withdraw(self, ctx: commands.Context, amount: str = None):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        user_id = ctx.author.id
        bank_bal = EconomyHelper.get_user_bank(user_id)
        cur = EconomyHelper.get_currency_display()

        if amount is None:
            await ctx.reply(f"{emoji.wrong} Informe a quantia para sacar ou use `sacar all`.")
            return

        if amount.lower() == "all":
            final_amount = bank_bal
        else:
            try:
                final_amount = int(amount)
            except ValueError:
                await ctx.reply(f"{emoji.wrong} Quantia inválida.")
                return

        if final_amount <= 0:
            await ctx.reply(f"{emoji.wrong} A quantia deve ser maior que zero.")
            return

        if bank_bal < final_amount:
            await ctx.reply(f"{emoji.wrong} Você não tem essa quantia no banco.")
            return

        if EconomyHelper.withdraw_coins(user_id, final_amount):
            hand_bal = EconomyHelper.get_user_coins(user_id)
            await ctx.reply(
                f"{emoji.success} Você sacou **{final_amount:,}** {cur} do banco!\n"
                f"-# Saldo em mãos: **{hand_bal:,}**"
            )
        else:
            await ctx.reply(f"{emoji.wrong} Ocorreu um erro ao processar o saque.")

def setup(bot: commands.Bot):
    bot.add_cog(BankCommand(bot))
