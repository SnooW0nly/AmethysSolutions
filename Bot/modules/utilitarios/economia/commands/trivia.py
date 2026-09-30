import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

TRIVIA_QUESTIONS = [
    {"q": "Qual é o maior planeta do Sistema Solar?", "a": ["jupiter", "júpiter"], "hint": "Começa com J"},
    {"q": "Quantos lados tem um hexágono?", "a": ["6", "seis"], "hint": "Número par entre 5 e 7"},
    {"q": "Qual é o elemento químico de símbolo 'Au'?", "a": ["ouro", "gold"], "hint": "Metal precioso amarelo"},
    {"q": "Em que país fica a Torre Eiffel?", "a": ["franca", "frança", "france"], "hint": "País do vinho e baguete"},
    {"q": "Qual é o animal terrestre mais rápido?", "a": ["guepardo", "cheetah"], "hint": "Felino manchado"},
    {"q": "Quantos continentes tem o planeta Terra?", "a": ["7", "sete"], "hint": "Um número ímpar"},
    {"q": "Qual é o idioma mais falado no mundo?", "a": ["mandarin", "mandarim", "chines", "chinês"], "hint": "Falado na China"},
    {"q": "Quem pintou a Mona Lisa?", "a": ["da vinci", "leonardo", "leonardo da vinci"], "hint": "Leonardo ___"},
    {"q": "Qual é o osso mais longo do corpo humano?", "a": ["femur", "fêmur"], "hint": "Está na coxa"},
    {"q": "Qual país tem a maior população do mundo?", "a": ["india", "índia", "india"], "hint": "País do curry e ioga"},
    {"q": "Quantas horas tem um dia?", "a": ["24", "vinte e quatro"], "hint": "Número par entre 20 e 30"},
    {"q": "Qual é a capital do Brasil?", "a": ["brasilia", "brasília"], "hint": "Começa com 'B'"},
    {"q": "Qual é o maior oceano do mundo?", "a": ["pacifico", "pacífico", "pacific"], "hint": "Indica calma no nome"},
    {"q": "De que material é feito o vidro?", "a": ["areia", "silica", "sílica", "areia de silica"], "hint": "Encontrado na praia"},
    {"q": "Quantas patas tem uma aranha?", "a": ["8", "oito"], "hint": "O dobro de uma mosca"},
    {"q": "Qual é o menor país do mundo?", "a": ["vaticano", "vatican"], "hint": "Fica dentro de Roma"},
    {"q": "Em que ano o homem pisou na Lua pela primeira vez?", "a": ["1969"], "hint": "Década de 60"},
    {"q": "Qual animal é o símbolo do WWF?", "a": ["panda", "urso panda"], "hint": "Urso preto e branco"},
    {"q": "Quantos jogadores tem um time de futebol em campo?", "a": ["11", "onze"], "hint": "Número ímpar entre 10 e 12"},
    {"q": "O que H2O representa?", "a": ["agua", "água", "water"], "hint": "Você bebe todo dia"},
]


class TriviaCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active = {}  # channel_id -> question data

    @commands.command(name="trivia", aliases=["pergunta", "quiz"])
    async def trivia(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("trivia"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if ctx.channel.id in self.active:
            await ctx.reply(f"{emoji.wrong} Já há uma trivia ativa neste canal!")
            return

        cfg = EconomyHelper.get_economy_settings().get("trivia", {"reward": 150, "timeout": 30})
        reward = cfg.get("reward", 150)
        timeout = cfg.get("timeout", 30)
        cur = EconomyHelper.get_currency_display()

        q = random.choice(TRIVIA_QUESTIONS)
        self.active[ctx.channel.id] = q

        await ctx.send(
            f"🧠 **TRIVIA!**\n"
            f"❓ {q['q']}\n\n"
            f"💰 Prêmio: **{reward:,}** {cur}\n"
            f"-# Dica: {q['hint']} | Você tem {timeout}s para responder!"
        )

        def check(m):
            return m.channel.id == ctx.channel.id and not m.author.bot

        import asyncio
        try:
            while True:
                msg = await self.bot.wait_for("message", check=check, timeout=float(timeout))
                if msg.content.lower().strip() in q["a"]:
                    del self.active[ctx.channel.id]
                    final = EconomyHelper.add_user_coins(msg.author.id, reward, reason="Trivia correta", member=msg.author)
                    balance = EconomyHelper.get_user_coins(msg.author.id)
                    await ctx.send(
                        f"✅ **{msg.author.display_name}** acertou!\n"
                        f"Resposta: **{q['a'][0].title()}**\n"
                        f"💰 +**{final:,}** {cur}\n"
                        f"-# Saldo atual: {balance:,}"
                    )
                    return
        except Exception:
            if ctx.channel.id in self.active:
                del self.active[ctx.channel.id]
            await ctx.send(f"⏰ **Tempo esgotado!** A resposta era: **{q['a'][0].title()}**")


def setup(bot: commands.Bot):
    bot.add_cog(TriviaCommand(bot))
