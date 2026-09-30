import random
from disnake.ext import commands
import disnake
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class DiceCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="dice", aliases=["dado", "rolar", "d6"])
    async def dice(self, ctx: commands.Context, bet: str = None, prediction: str = None):
        """
        Rola um dado de 6 lados.
        Sem aposta: apenas rola.
        Com aposta: `dice <valor> <alto/baixo/exato:N>` 
          - alto = resultado 4-6 (paga 2x)
          - baixo = resultado 1-3 (paga 2x)
          - exato:N = resultado exato (paga 5x)
        """
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("dice"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cur = EconomyHelper.get_currency_display()

        # Rolar sem aposta
        if bet is None:
            result = random.randint(1, 6)
            dice_faces = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
            await ctx.reply(f"🎲 Você rolou: **{dice_faces[result]} {result}**")
            return

        # Rolar com aposta
        cfg = EconomyHelper.get_economy_settings().get("dice", {"min_bet": 10, "max_bet": 5000})
        min_bet = cfg.get("min_bet", 10)
        max_bet = cfg.get("max_bet", 5000)

        try:
            bet_int = int(bet.replace(",", "").replace(".", ""))
            if bet_int <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Valor de aposta inválido.")
            return

        if bet_int < min_bet or bet_int > max_bet:
            await ctx.reply(f"{emoji.wrong} Aposta entre `{min_bet:,}` e `{max_bet:,}`.")
            return

        if prediction is None:
            await ctx.reply(
                f"{emoji.wrong} Informe sua previsão: `alto`, `baixo` ou `exato:N`\n"
                f"Ex: `dice 200 alto` | `dice 200 exato:6`"
            )
            return

        user_coins = EconomyHelper.get_user_coins(ctx.author.id)
        if user_coins < bet_int:
            await ctx.reply(f"{emoji.wrong} Saldo insuficiente. Você tem `{user_coins:,}`.")
            return

        result = random.randint(1, 6)
        dice_faces = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]
        pred_lower = prediction.lower()

        win = False
        mult = 1
        pred_desc = ""

        if pred_lower == "alto":
            win = result >= 4
            mult = 2
            pred_desc = "Alto (4-6)"
        elif pred_lower == "baixo":
            win = result <= 3
            mult = 2
            pred_desc = "Baixo (1-3)"
        elif pred_lower.startswith("exato:"):
            try:
                exact = int(pred_lower.split(":")[1])
                if not 1 <= exact <= 6:
                    raise ValueError
                win = result == exact
                mult = 5
                pred_desc = f"Exato: {exact}"
            except (ValueError, IndexError):
                await ctx.reply(f"{emoji.wrong} Use `exato:N` onde N é 1-6. Ex: `exato:4`")
                return
        else:
            await ctx.reply(f"{emoji.wrong} Previsão inválida. Use: `alto`, `baixo` ou `exato:N`")
            return

        EconomyHelper.remove_user_coins(ctx.author.id, bet_int)
        if win:
            winnings = bet_int * mult
            EconomyHelper.add_user_coins(ctx.author.id, winnings)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"🎲 Você rolou **{dice_faces[result]} {result}**!\n"
                f"✅ Previsão **{pred_desc}** correta! Você ganhou **{winnings:,}** {cur} (`{mult}x`)!\n"
                f"-# Saldo atual: {balance:,}"
            )
        else:
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"🎲 Você rolou **{dice_faces[result]} {result}**!\n"
                f"❌ Previsão **{pred_desc}** errada! Você perdeu **{bet_int:,}** {cur}.\n"
                f"-# Saldo atual: {balance:,}"
            )


class DuelDiceCommand(commands.Cog):
    """Duelo de dado entre dois usuários."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="dueldice", aliases=["dadoduel", "duelo_dado"])
    async def dueldice(self, ctx: commands.Context, target: disnake.Member = None, bet: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if target is None or bet is None:
            await ctx.reply(f"{emoji.wrong} Use: `dueldice @usuário <aposta>`")
            return

        if target.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Você não pode duelar consigo mesmo.")
            return

        if target.bot:
            await ctx.reply(f"{emoji.wrong} Você não pode duelar com um bot.")
            return

        try:
            bet_int = int(bet.replace(",", "").replace(".", ""))
            if bet_int <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Valor inválido.")
            return

        cur = EconomyHelper.get_currency_display()

        if EconomyHelper.get_user_coins(ctx.author.id) < bet_int:
            await ctx.reply(f"{emoji.wrong} Você não tem coins suficientes.")
            return
        if EconomyHelper.get_user_coins(target.id) < bet_int:
            await ctx.reply(f"{emoji.wrong} **{target.display_name}** não tem coins suficientes.")
            return

        # Aceite
        msg = await ctx.reply(
            f"🎲 **{target.mention}**, **{ctx.author.display_name}** te desafia para um duelo de dados!\n"
            f"Aposta: **{bet_int:,}** {cur}\n"
            f"Responda `aceito` em 30s para jogar!"
        )

        def check(m):
            return m.author.id == target.id and m.channel.id == ctx.channel.id and m.content.lower() in ["aceito", "sim", "yes"]

        try:
            await ctx.bot.wait_for("message", check=check, timeout=30.0)
        except Exception:
            await msg.edit(content=f"⏰ **{target.display_name}** não aceitou o duelo a tempo.")
            return

        r1 = random.randint(1, 6)
        r2 = random.randint(1, 6)
        dice_faces = ["", "⚀", "⚁", "⚂", "⚃", "⚄", "⚅"]

        if r1 > r2:
            EconomyHelper.remove_user_coins(target.id, bet_int)
            EconomyHelper.add_user_coins(ctx.author.id, bet_int)
            result_txt = f"🏆 **{ctx.author.display_name}** venceu!"
        elif r2 > r1:
            EconomyHelper.remove_user_coins(ctx.author.id, bet_int)
            EconomyHelper.add_user_coins(target.id, bet_int)
            result_txt = f"🏆 **{target.display_name}** venceu!"
        else:
            result_txt = f"🤝 **Empate!** Ninguém ganhou nem perdeu."

        await ctx.reply(
            f"🎲 **Duelo de Dados!**\n"
            f"{ctx.author.display_name}: **{dice_faces[r1]} {r1}**\n"
            f"{target.display_name}: **{dice_faces[r2]} {r2}**\n\n"
            f"{result_txt}\n"
            f"-# Prêmio em jogo: {bet_int:,} {cur}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(DiceCommand(bot))
    bot.add_cog(DuelDiceCommand(bot))
