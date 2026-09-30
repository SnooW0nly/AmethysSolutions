import random
from disnake.ext import commands
import disnake
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class RobCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="rob", aliases=["roubar", "assaltar"])
    async def rob(self, ctx: commands.Context, target: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("rob"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if target is None:
            await ctx.reply(f"{emoji.wrong} Mencione alguém para roubar. Ex: `rob @usuário`")
            return

        if target.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Você não pode roubar a si mesmo.")
            return

        if target.bot:
            await ctx.reply(f"{emoji.wrong} Você não pode roubar um bot.")
            return

        user_id = ctx.author.id
        target_id = target.id
        cur = EconomyHelper.get_currency_display()

        remaining = EconomyHelper.check_cooldown(user_id, "rob")
        if remaining > 0:
            await ctx.reply(
                f"{emoji.wrong} Aguarde `{EconomyHelper.format_cooldown(remaining)}` antes de roubar novamente."
            )
            return

        cfg = EconomyHelper.get_economy_settings().get("rob", {})
        min_bal = cfg.get("min_target_balance", 200)
        target_coins = EconomyHelper.get_user_coins(target_id)
        # O roubo agora ignora o saldo no banco (EconomyHelper.get_user_bank(target_id))

        if target_coins < min_bal:
            await ctx.reply(
                f"{emoji.wrong} **{target.display_name}** não tem coins suficientes em mãos para ser roubado "
                f"(mínimo: `{min_bal:,}`). O dinheiro no banco está protegido!"
            )
            return

        EconomyHelper.set_cooldown(user_id, "rob")
        chance = cfg.get("success_chance", 40)

        if random.randint(1, 100) <= chance:
            # Sucesso
            min_pct = cfg.get("min_steal_percent", 10) / 100
            max_pct = cfg.get("max_steal_percent", 40) / 100
            pct = random.uniform(min_pct, max_pct)
            stolen = max(1, int(target_coins * pct))
            EconomyHelper.remove_user_coins(target_id, stolen, reason=f"Roubado por {ctx.author.id}")
            EconomyHelper.add_user_coins(user_id, stolen, reason=f"Roubou {target_id}")
            balance = EconomyHelper.get_user_coins(user_id)
            await ctx.reply(
                f"🥷 Você roubou **{target.display_name}** e levou **{stolen:,}** {cur}! "
                f"({pct*100:.1f}% do saldo)\n"
                f"-# Saldo atual: {balance:,}"
            )
        else:
            # Falha
            fine_pct = cfg.get("fine_percent", 25) / 100
            fine = max(1, int(EconomyHelper.get_user_coins(user_id) * fine_pct))
            EconomyHelper.remove_user_coins(user_id, fine, reason="Pego tentando roubar")
            balance = EconomyHelper.get_user_coins(user_id)
            await ctx.reply(
                f"👮 Você foi pego tentando roubar **{target.display_name}** "
                f"e pagou **{fine:,}** {cur} de multa!\n"
                f"-# Saldo atual: {balance:,}"
            )


def setup(bot: commands.Bot):
    bot.add_cog(RobCommand(bot))