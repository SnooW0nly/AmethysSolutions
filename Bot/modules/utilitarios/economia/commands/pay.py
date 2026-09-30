import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class PayCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="pay", aliases=["pagar", "transferir", "enviar"])
    async def pay(self, ctx: commands.Context, target: disnake.Member = None, amount: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("pay"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if target is None or amount is None:
            await ctx.reply(
                f"{emoji.wrong} Uso correto: `pay @usuário <quantia>`\n"
                "Ex: `pay @João 500`"
            )
            return

        if target.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Você não pode transferir para si mesmo.")
            return

        if target.bot:
            await ctx.reply(f"{emoji.wrong} Você não pode transferir para um bot.")
            return

        try:
            amount_int = int(amount.replace(",", "").replace(".", ""))
            if amount_int <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Valor inválido.")
            return

        cfg = EconomyHelper.get_economy_settings().get("pay", {})
        min_t = cfg.get("min_transfer", 1)
        if amount_int < min_t:
            await ctx.reply(f"{emoji.wrong} O valor mínimo de transferência é `{min_t:,}`.")
            return

        user_coins = EconomyHelper.get_user_coins(ctx.author.id)
        if user_coins < amount_int:
            await ctx.reply(
                f"{emoji.wrong} Você não tem coins suficientes. "
                f"Seu saldo: **{user_coins:,}** | Necessário: **{amount_int:,}**."
            )
            return

        success, net = EconomyHelper.transfer_coins(ctx.author.id, target.id, amount_int)
        if not success:
            await ctx.reply(f"{emoji.wrong} Transferência falhou.")
            return

        tax = amount_int - net
        cur = EconomyHelper.get_currency_display()
        tax_line = f"\n💸 Taxa: `{tax:,}` | Recebido: `{net:,}`" if tax > 0 else ""

        await ctx.reply(
            f"💸 **Transferência realizada!**\n"
            f"Você enviou **{amount_int:,}** {cur} para **{target.display_name}**!{tax_line}\n"
            f"-# Seu saldo: {EconomyHelper.get_user_coins(ctx.author.id):,}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(PayCommand(bot))