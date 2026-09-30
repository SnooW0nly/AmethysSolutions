import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

SUITS = ["♠️", "♥️", "♦️", "♣️"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
VALUES = {"A": 11, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7,
          "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10}


def new_deck():
    return [(r, s) for s in SUITS for r in RANKS]


def draw_card(deck):
    return deck.pop(random.randint(0, len(deck) - 1))


def hand_value(hand):
    total = sum(VALUES[r] for r, _ in hand)
    aces = sum(1 for r, _ in hand if r == "A")
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total


def format_hand(hand, hide_second=False):
    if hide_second and len(hand) > 1:
        first = f"`{hand[0][0]}{hand[0][1]}`"
        return f"{first} `??`"
    return " ".join(f"`{r}{s}`" for r, s in hand)


class BlackjackCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games = {}  # user_id -> game state

    @commands.command(name="blackjack", aliases=["bj", "vinte1", "21"])
    async def blackjack(self, ctx: commands.Context, bet: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("blackjack"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cfg = EconomyHelper.get_economy_settings().get("blackjack", {"min_bet": 50, "max_bet": 10000})
        min_bet = cfg.get("min_bet", 50)
        max_bet = cfg.get("max_bet", 10000)
        cur = EconomyHelper.get_currency_display()

        if ctx.author.id in self.active_games:
            await ctx.reply(f"{emoji.wrong} Você já tem um jogo em andamento! Use `hit`, `stand` ou `double`.")
            return

        if bet is None:
            await ctx.reply(
                f"{emoji.wrong} Use: `blackjack <aposta>`\n"
                f"Aposta: `{min_bet:,}` a `{max_bet:,}`\n"
                f"Comandos durante o jogo: `hit` (pedir), `stand` (parar), `double` (dobrar)"
            )
            return

        try:
            bet_int = int(bet.replace(",", "").replace(".", ""))
            if bet_int <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Valor inválido.")
            return

        if bet_int < min_bet or bet_int > max_bet:
            await ctx.reply(f"{emoji.wrong} Aposta entre `{min_bet:,}` e `{max_bet:,}`.")
            return

        user_coins = EconomyHelper.get_user_coins(ctx.author.id)
        if user_coins < bet_int:
            await ctx.reply(f"{emoji.wrong} Saldo insuficiente.")
            return

        EconomyHelper.remove_user_coins(ctx.author.id, bet_int)

        deck = new_deck()
        player_hand = [draw_card(deck), draw_card(deck)]
        dealer_hand = [draw_card(deck), draw_card(deck)]

        self.active_games[ctx.author.id] = {
            "deck": deck,
            "player": player_hand,
            "dealer": dealer_hand,
            "bet": bet_int,
            "channel": ctx.channel.id,
        }

        pv = hand_value(player_hand)

        # Blackjack natural
        if pv == 21:
            winnings = int(bet_int * 2.5)
            EconomyHelper.add_user_coins(ctx.author.id, winnings)
            del self.active_games[ctx.author.id]
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"🃏 **Blackjack Natural! 21!**\n"
                f"Sua mão: {format_hand(player_hand)} → **{pv}**\n"
                f"🎉 Você ganhou **{winnings:,}** {cur} (2.5x)!\n"
                f"-# Saldo atual: {balance:,}"
            )
            return

        await ctx.reply(
            f"🃏 **Blackjack** — Aposta: `{bet_int:,}` {cur}\n\n"
            f"🧑 Sua mão: {format_hand(player_hand)} → **{pv}**\n"
            f"🤖 Dealer: {format_hand(dealer_hand, hide_second=True)}\n\n"
            f"-# Digite `hit` (pedir carta), `stand` (parar) ou `double` (dobrar aposta)"
        )

    @commands.command(name="hit", aliases=["pedir", "carta"])
    async def hit(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        game = self.active_games.get(ctx.author.id)
        if not game or game["channel"] != ctx.channel.id:
            await ctx.reply(f"{emoji.wrong} Você não tem um jogo ativo. Use `blackjack <aposta>` para começar.")
            return

        cur = EconomyHelper.get_currency_display()
        game["player"].append(draw_card(game["deck"]))
        pv = hand_value(game["player"])

        if pv > 21:
            del self.active_games[ctx.author.id]
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"🃏 Sua mão: {format_hand(game['player'])} → **{pv}**\n"
                f"💥 **Estourou! Você perdeu {game['bet']:,} {cur}.**\n"
                f"-# Saldo atual: {balance:,}"
            )
        elif pv == 21:
            await self._stand_logic(ctx, game)
        else:
            await ctx.reply(
                f"🃏 Sua mão: {format_hand(game['player'])} → **{pv}**\n"
                f"🤖 Dealer: {format_hand(game['dealer'], hide_second=True)}\n"
                f"-# `hit` para mais uma carta, `stand` para parar"
            )

    @commands.command(name="stand", aliases=["parar", "ficar"])
    async def stand(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        game = self.active_games.get(ctx.author.id)
        if not game or game["channel"] != ctx.channel.id:
            await ctx.reply(f"{emoji.wrong} Você não tem um jogo ativo.")
            return

        await self._stand_logic(ctx, game)

    @commands.command(name="double", aliases=["dobrar"])
    async def double(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        game = self.active_games.get(ctx.author.id)
        if not game or game["channel"] != ctx.channel.id:
            await ctx.reply(f"{emoji.wrong} Você não tem um jogo ativo.")
            return

        if EconomyHelper.get_user_coins(ctx.author.id) < game["bet"]:
            await ctx.reply(f"{emoji.wrong} Sem coins para dobrar a aposta.")
            return

        EconomyHelper.remove_user_coins(ctx.author.id, game["bet"])
        game["bet"] *= 2
        game["player"].append(draw_card(game["deck"]))

        pv = hand_value(game["player"])
        cur = EconomyHelper.get_currency_display()

        if pv > 21:
            del self.active_games[ctx.author.id]
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"🃏 Aposta dobrada! Sua mão: {format_hand(game['player'])} → **{pv}**\n"
                f"💥 **Estourou! Você perdeu {game['bet']:,} {cur}.**\n"
                f"-# Saldo atual: {balance:,}"
            )
        else:
            await self._stand_logic(ctx, game)

    async def _stand_logic(self, ctx, game):
        cur = EconomyHelper.get_currency_display()
        pv = hand_value(game["player"])

        # Dealer joga
        while hand_value(game["dealer"]) < 17:
            game["dealer"].append(draw_card(game["deck"]))

        dv = hand_value(game["dealer"])
        del self.active_games[ctx.author.id]

        result_lines = (
            f"🃏 **Blackjack — Resultado**\n"
            f"🧑 Sua mão: {format_hand(game['player'])} → **{pv}**\n"
            f"🤖 Dealer: {format_hand(game['dealer'])} → **{dv}**\n\n"
        )
        balance = EconomyHelper.get_user_coins(ctx.author.id)

        if dv > 21 or pv > dv:
            winnings = game["bet"] * 2
            EconomyHelper.add_user_coins(ctx.author.id, winnings)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(result_lines + f"🏆 **Você venceu! +{winnings:,}** {cur}\n-# Saldo atual: {balance:,}")
        elif pv == dv:
            EconomyHelper.add_user_coins(ctx.author.id, game["bet"])
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(result_lines + f"🤝 **Empate! Aposta devolvida.**\n-# Saldo atual: {balance:,}")
        else:
            await ctx.reply(result_lines + f"😢 **Dealer venceu! -{game['bet']:,}** {cur}\n-# Saldo atual: {balance:,}")


def setup(bot: commands.Bot):
    bot.add_cog(BlackjackCommand(bot))
