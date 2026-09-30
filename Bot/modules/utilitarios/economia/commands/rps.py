import random
import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

CHOICES = {
    "pedra": "🪨", "papel": "📄", "tesoura": "✂️",
    "rock": "🪨", "paper": "📄", "scissors": "✂️",
    "p": "🪨", "pa": "📄", "t": "✂️",
}
NORMALIZE = {
    "pedra": "pedra", "rock": "pedra", "p": "pedra",
    "papel": "papel", "paper": "papel", "pa": "papel",
    "tesoura": "tesoura", "scissors": "tesoura", "t": "tesoura",
}
WINS = {"pedra": "tesoura", "papel": "pedra", "tesoura": "papel"}
EMOJIS = {"pedra": "🪨", "papel": "📄", "tesoura": "✂️"}


class RPSCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="rps", aliases=["jokenpo", "pedrapapeltesoura", "ppt"])
    async def rps(self, ctx: commands.Context, choice: str = None, bet: str = None):
        """
        Pedra Papel Tesoura contra o bot!
        `rps <pedra/papel/tesoura> [aposta]`
        """
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("rps"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cur = EconomyHelper.get_currency_display()

        if choice is None:
            await ctx.reply(
                f"✂️ **Pedra Papel Tesoura!**\n"
                f"Use: `rps <pedra/papel/tesoura> [aposta]`\n"
                f"Ex: `rps pedra 200`"
            )
            return

        choice_lower = choice.lower()
        if choice_lower not in NORMALIZE:
            await ctx.reply(f"{emoji.wrong} Escolha válida: `pedra`, `papel` ou `tesoura`.")
            return

        player_choice = NORMALIZE[choice_lower]
        bot_choice = random.choice(["pedra", "papel", "tesoura"])

        pe = EMOJIS[player_choice]
        be = EMOJIS[bot_choice]

        # Sem aposta
        if bet is None:
            if player_choice == bot_choice:
                result = "🤝 **Empate!**"
            elif WINS[player_choice] == bot_choice:
                result = "🏆 **Você venceu!**"
            else:
                result = "😢 **Você perdeu!**"

            await ctx.reply(
                f"{pe} vs {be}\n"
                f"Você: **{player_choice}** | Bot: **{bot_choice}**\n"
                f"{result}"
            )
            return

        # Com aposta
        cfg = EconomyHelper.get_economy_settings().get("rps", {"min_bet": 10, "max_bet": 5000})
        try:
            bet_int = int(bet.replace(",", "").replace(".", ""))
            if bet_int <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Aposta inválida.")
            return

        min_bet = cfg.get("min_bet", 10)
        max_bet = cfg.get("max_bet", 5000)
        if bet_int < min_bet or bet_int > max_bet:
            await ctx.reply(f"{emoji.wrong} Aposta entre `{min_bet:,}` e `{max_bet:,}`.")
            return

        user_coins = EconomyHelper.get_user_coins(ctx.author.id)
        if user_coins < bet_int:
            await ctx.reply(f"{emoji.wrong} Saldo insuficiente.")
            return

        if player_choice == bot_choice:
            result = f"🤝 **Empate!** Aposta devolvida."
        elif WINS[player_choice] == bot_choice:
            EconomyHelper.add_user_coins(ctx.author.id, bet_int)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            result = f"🏆 **Você venceu! +{bet_int:,}** {cur}\n-# Saldo atual: {balance:,}"
        else:
            EconomyHelper.remove_user_coins(ctx.author.id, bet_int)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            result = f"😢 **Você perdeu! -{bet_int:,}** {cur}\n-# Saldo atual: {balance:,}"

        await ctx.reply(
            f"{pe} vs {be}\n"
            f"Você: **{player_choice}** | Bot: **{bot_choice}**\n"
            f"{result}"
        )


class RPSDuelCommand(commands.Cog):
    """RPS entre dois usuários."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.pending = {}  # (user1, user2, channel, bet, choice1)

    @commands.command(name="rpsduel", aliases=["duelrps", "pptvs"])
    async def rpsduel(self, ctx: commands.Context, target: disnake.Member = None, bet: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if target is None or bet is None:
            await ctx.reply(f"{emoji.wrong} Use: `rpsduel @usuário <aposta>`")
            return

        if target.id == ctx.author.id or target.bot:
            await ctx.reply(f"{emoji.wrong} Alvo inválido.")
            return

        try:
            bet_int = int(bet.replace(",", "").replace(".", ""))
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Aposta inválida.")
            return

        cur = EconomyHelper.get_currency_display()

        if EconomyHelper.get_user_coins(ctx.author.id) < bet_int:
            await ctx.reply(f"{emoji.wrong} Você não tem coins suficientes.")
            return
        if EconomyHelper.get_user_coins(target.id) < bet_int:
            await ctx.reply(f"{emoji.wrong} **{target.display_name}** não tem coins suficientes.")
            return

        await ctx.reply(
            f"✂️ **RPS Duelo!** {ctx.author.mention} vs {target.mention}\n"
            f"Aposta: **{bet_int:,}** {cur}\n\n"
            f"Ambos enviem suas jogadas via DM ou digitem aqui:\n"
            f"**{ctx.author.display_name}** escolha: `pedra`, `papel` ou `tesoura`"
        )

        def check1(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content.lower() in NORMALIZE

        def check2(m):
            return m.author.id == target.id and m.channel.id == ctx.channel.id and m.content.lower() in NORMALIZE

        import asyncio
        try:
            msg1 = await self.bot.wait_for("message", check=check1, timeout=30.0)
            await ctx.send(f"✅ **{ctx.author.display_name}** escolheu! Agora **{target.display_name}**, sua vez:")
            msg2 = await self.bot.wait_for("message", check=check2, timeout=30.0)
        except Exception:
            await ctx.send(f"⏰ Tempo esgotado! Duelo cancelado.")
            return

        c1 = NORMALIZE[msg1.content.lower()]
        c2 = NORMALIZE[msg2.content.lower()]
        e1 = EMOJIS[c1]
        e2 = EMOJIS[c2]

        if c1 == c2:
            result = "🤝 **Empate! Apostas devolvidas.**"
        elif WINS[c1] == c2:
            EconomyHelper.remove_user_coins(target.id, bet_int)
            EconomyHelper.add_user_coins(ctx.author.id, bet_int)
            result = f"🏆 **{ctx.author.display_name}** venceu **{bet_int:,}** {cur}!"
        else:
            EconomyHelper.remove_user_coins(ctx.author.id, bet_int)
            EconomyHelper.add_user_coins(target.id, bet_int)
            result = f"🏆 **{target.display_name}** venceu **{bet_int:,}** {cur}!"

        await ctx.send(
            f"✂️ **Resultado do Duelo!**\n"
            f"{ctx.author.display_name}: {e1} **{c1}**\n"
            f"{target.display_name}: {e2} **{c2}**\n\n"
            f"{result}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(RPSCommand(bot))
    bot.add_cog(RPSDuelCommand(bot))
