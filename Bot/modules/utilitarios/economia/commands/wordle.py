import random
import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

# Palavras de 5 letras em português
WORDS_5 = [
    "GATOS", "CARRO", "BANCO", "FESTA", "MUNDO", "PEIXE", "OURO",
    "BRAVO", "CALMA", "DADOS", "ELEVO", "FALAR", "GARFO", "HEROI",
    "IDEAL", "JOGAR", "LARGO", "MANTO", "NOBRE", "ONTEM", "PROVA",
    "QUEDA", "RINDO", "SABOR", "TARDE", "UMBRA", "VERDE", "XISTO",
    "ZEBRA", "AMIGO", "BRAÇO", "COISA", "DIZER", "FAZER", "GERAL",
    "HOMEM", "IRMAR", "JOIAS", "LARGO", "MORAR", "NOITE", "OUROS",
    "PULAR", "QUASE", "REINO", "SACOS", "TELAS", "VENTO", "ACASO",
    "BEBER", "CRAVO", "DEVIR", "ENVIO", "FLOCO", "GRAUS", "HOTEL",
    "IMUNE", "JULHO", "KARMA", "LENTO", "MUROS", "NEGRO", "OBRAS",
    "PEÇAS", "RATOS", "SUMIR", "TARDE", "VIVER", "AREIA", "BRISA",
    "COPOS", "DRAMA", "ESTES", "FUNDO", "GRIPE", "HAVIA", "IRMOS",
    "JORNAL", "LADOS", "MARES", "NOTAS", "OBTER",
]
WORDS_5 = [w for w in WORDS_5 if len(w) == 5]

HINT_CORRECT = "🟩"   # Letra certa, posição certa
HINT_WRONG_POS = "🟨"  # Letra certa, posição errada
HINT_ABSENT = "⬛"    # Letra ausente


def get_hints(guess: str, answer: str) -> str:
    result = []
    answer_chars = list(answer)
    guess_chars = list(guess)

    # Primeiro passo: certos
    for i in range(5):
        if guess_chars[i] == answer_chars[i]:
            result.append(HINT_CORRECT)
            answer_chars[i] = None
            guess_chars[i] = None
        else:
            result.append(None)

    # Segundo passo: presentes mas errados
    for i in range(5):
        if result[i] is not None:
            continue
        if guess_chars[i] in answer_chars:
            result[i] = HINT_WRONG_POS
            answer_chars[answer_chars.index(guess_chars[i])] = None
        else:
            result[i] = HINT_ABSENT

    return "".join(result)


class WordleCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_games = {}  # user_id -> game state

    @commands.command(name="wordle", aliases=["palavrinha", "adivinha_palavra"])
    async def wordle(self, ctx: commands.Context):
        """
        Jogue Wordle! Adivinhe a palavra de 5 letras em 6 tentativas.
        🟩 = Letra certa na posição certa
        🟨 = Letra certa na posição errada
        ⬛ = Letra ausente
        """
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("wordle"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if ctx.author.id in self.active_games:
            await ctx.reply(f"{emoji.wrong} Você já tem um jogo ativo! Envie sua tentativa (palavra de 5 letras).")
            return

        answer = random.choice(WORDS_5)
        self.active_games[ctx.author.id] = {
            "answer": answer,
            "attempts": [],
            "channel": ctx.channel.id,
            "max": 6,
        }

        await ctx.reply(
            "📝 **WORDLE!**\n"
            "Adivinhe a palavra de **5 letras** em até **6 tentativas**!\n\n"
            f"{HINT_CORRECT} = Certa posição | {HINT_WRONG_POS} = Letra presente | {HINT_ABSENT} = Ausente\n\n"
            "Envie sua primeira tentativa!"
        )

        def check(m):
            return (
                m.author.id == ctx.author.id
                and m.channel.id == ctx.channel.id
                and len(m.content.strip()) == 5
                and m.content.strip().isalpha()
            )

        import asyncio
        try:
            while True:
                game = self.active_games.get(ctx.author.id)
                if not game:
                    return

                msg = await ctx.bot.wait_for("message", check=check, timeout=120.0)
                guess = msg.content.strip().upper()

                hints = get_hints(guess, game["answer"])
                game["attempts"].append((guess, hints))

                # Mostrar estado atual
                board = "\n".join(
                    f"`{att}` {h}"
                    for att, h in game["attempts"]
                )
                remaining = game["max"] - len(game["attempts"])

                if guess == game["answer"]:
                    del self.active_games[ctx.author.id]
                    tries = len(game["attempts"])
                    reward = max(50, (7 - tries) * 100)  # Mais rápido = mais recompensa
                    if EconomyHelper.is_economy_enabled():
                        EconomyHelper.add_user_coins(ctx.author.id, reward, reason="Wordle ganho")
                    allowed, reason = EconomyGuard.check(ctx)
                    if not allowed:
                        await ctx.reply(reason, delete_after=6)
                        return

                    cur = EconomyHelper.get_currency_display()
                    await ctx.send(
                        f"🎉 **Acertou em {tries} tentativa{'s' if tries > 1 else ''}!**\n\n"
                        f"{board}\n\n"
                        f"💰 +**{reward}** {cur} de recompensa!"
                    )
                    return

                if len(game["attempts"]) >= game["max"]:
                    del self.active_games[ctx.author.id]
                    await ctx.send(
                        f"💔 **Acabou as tentativas!** A palavra era **{game['answer']}**\n\n"
                        f"{board}"
                    )
                    return

                await ctx.send(
                    f"{board}\n\n"
                    f"⬜ Tentativas restantes: **{remaining}**"
                )

        except Exception:
            if ctx.author.id in self.active_games:
                del self.active_games[ctx.author.id]
            await ctx.send(f"⏰ Tempo esgotado! A palavra era **{self.active_games.get(ctx.author.id, {}).get('answer', '?')}**.")


def setup(bot: commands.Bot):
    bot.add_cog(WordleCommand(bot))
