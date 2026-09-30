import random
import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

JOKES = [
    ("Por que o matemático não conseguiu dormir?", "Porque tinha muitos problemas para resolver!"),
    ("O que o zero disse para o oito?", "Belo cinto!"),
    ("Por que os polvos são tão inteligentes?", "Porque eles têm oito braços para pensar!"),
    ("O que é um peixe sem olho?", "Pxe!"),
    ("Por que o livro de matemática está sempre triste?", "Porque tem muitos problemas!"),
    ("O que o oceano disse para a praia?", "Nada, só deu uma onda!"),
    ("Por que o espantalho ganhou um prêmio?", "Porque era o melhor no ramo!"),
    ("O que é um quarto de laranja?", "Uma laranjinha que fez bagunça e ficou de castigo!"),
    ("Por que o sol não vai à escola?", "Porque ele já tem um milhão de graus!"),
    ("Por que o sorvete foi ao médico?", "Porque estava derretendo de amor!"),
    ("O que o pato disse para a pata?", "Nada, os patos não falam."),
    ("Por que o computador foi ao psicólogo?", "Porque tinha muitos vírus na cabeça!"),
    ("Qual é o animal que vive no telhado?", "O goto (gato)!"),
    ("O que diz o 1 para o 10?", "Pra que esse zero?"),
    ("Por que o ciclista não consegue dormir?", "Porque fica pedindo!"),
]

EIGHT_BALL_RESPONSES = [
    ("✅", "Com certeza!"),
    ("✅", "Definitivamente sim!"),
    ("✅", "Pode contar com isso!"),
    ("✅", "Sim, sem dúvidas!"),
    ("✅", "Os sinais apontam que sim."),
    ("🤔", "Não tenho certeza..."),
    ("🤔", "Pergunte novamente mais tarde."),
    ("🤔", "É difícil dizer agora."),
    ("🤔", "Concentre-se e tente de novo."),
    ("❌", "Não conte com isso."),
    ("❌", "Minha resposta é não."),
    ("❌", "Perspectivas não muito boas."),
    ("❌", "Muito duvidoso."),
]

TRUTHS = [
    "Qual foi a coisa mais estranha que você já comeu?",
    "Qual é o seu maior segredo que você nunca contou a ninguém?",
    "Qual foi a mentira mais descarada que você já disse?",
    "Você já teve um crush em alguém do servidor?",
    "Qual é a coisa mais embaraçosa que já te aconteceu?",
    "Você já fingiu estar doente para não fazer algo?",
    "Qual foi o presente mais decepcionante que você já recebeu?",
    "Você já bisbilhotou o celular de alguém?",
    "Qual é o seu mau hábito mais feio?",
    "Você já xingou seu chefe/professor na sua cabeça?",
    "Qual foi a decisão mais arrependida da sua vida?",
    "Você já riu de algo inapropriado em um momento sério?",
]

DARES = [
    "Mande uma mensagem aleatória para o último contato do seu celular.",
    "Escreva uma confissão de amor para alguém do servidor.",
    "Mude seu nick para algo constrangedor por 10 minutos.",
    "Escreva um poema para o próximo usuário que falar no chat.",
    "Fale como um robô por 5 mensagens.",
    "Mande uma mensagem em outra língua e veja se alguém entende.",
    "Escreva algo com os olhos fechados.",
    "Diga 3 coisas positivas sobre cada pessoa que responder essa mensagem.",
    "Imite um animal por 3 mensagens.",
    "Fale na terceira pessoa por 5 minutos.",
    "Escreva 'Sou um(a) pinguim gigante' no chat principal.",
    "Mande uma figurinha de algo que te envergonha.",
]

COMPLIMENTS = [
    "Você ilumina o servidor só com sua presença! ✨",
    "Sua personalidade é rara e preciosa como um diamante! 💎",
    "O mundo é definitivamente melhor com você nele! 🌍",
    "Você tem um talento incrível para fazer as pessoas sorrirem! 😊",
    "Sua criatividade não tem limites! 🎨",
    "Você é a pessoa mais incrível que já vi hoje! 🌟",
    "Sua voz é mais doce que mel! 🍯",
    "Você tornaria qualquer equipe melhor só por estar nela! 🏆",
    "A inteligência que você tem é impressionante! 🧠",
    "Você é uma inspiração para todos aqui! 🚀",
]

INSULTS_PLAYFUL = [
    "Você é mais lerdo que download de 56k! 🐢",
    "Eu já vi pedras com mais personalidade! 🪨",
    "Você é tão quente quanto sorvete na Antártida! 🥶",
    "Eu diria algo, mas minha mãe me ensinou a não mentir! 😇",
    "Você é a razão de existirem avisos como 'não beba xampu'! 🧴",
    "Se a burrice doesse, você viveria em uma farmácia! 💊",
    "Você é como wi-fi no metrô: pouco confiável! 📡",
    "Eu já vi cachorros resolver labirintos mais rápido que você! 🐕",
    "Sua conta bancária e seu QI têm um número em comum! 💸",
    "Você é a prova viva de que o café ainda não chegou pra todo mundo! ☕",
]

DARES_MSG_SEND = [
    "Você desafiou alguém! Agora aguenta! 😈",
]


class FunCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="piada", aliases=["joke", "humor"])
    async def joke(self, ctx: commands.Context):
        """Conta uma piada aleatória."""
        q, a = random.choice(JOKES)
        embed = disnake.Embed(
            title="😂 Piada do Dia",
            description=f"**{q}**\n\n||{a}||",
            color=0xFFD700
        )
        embed.set_footer(text="Clique no spoiler para ver a resposta!")
        await ctx.reply(embed=embed)

    @commands.command(name="8ball", aliases=["bola8", "magicball", "oraculo"])
    async def eight_ball(self, ctx: commands.Context, *, question: str = None):
        """Consulte a bola mágica."""
        if not question:
            await ctx.reply(f"{emoji.wrong} Faça uma pergunta! Ex: `8ball Vou ficar rico?`")
            return

        em, resp = random.choice(EIGHT_BALL_RESPONSES)
        embed = disnake.Embed(
            title="🎱 A Bola Mágica Responde...",
            color=0x2B2D31
        )
        embed.add_field(name="❓ Pergunta", value=question, inline=False)
        embed.add_field(name=f"{em} Resposta", value=f"**{resp}**", inline=False)
        await ctx.reply(embed=embed)

    @commands.command(name="verdade", aliases=["truth", "tod_verdade"])
    async def truth(self, ctx: commands.Context, target: disnake.Member = None):
        """Receba uma verdade ou desafie alguém."""
        t = target or ctx.author
        question = random.choice(TRUTHS)
        embed = disnake.Embed(
            title="🕵️ VERDADE!",
            description=f"{t.mention}, você precisa responder:\n\n**{question}**",
            color=0x3498DB
        )
        await ctx.reply(embed=embed)

    @commands.command(name="desafio", aliases=["dare", "tod_desafio"])
    async def dare(self, ctx: commands.Context, target: disnake.Member = None):
        """Receba um desafio ou desafie alguém."""
        t = target or ctx.author
        challenge = random.choice(DARES)
        embed = disnake.Embed(
            title="🔥 DESAFIO!",
            description=f"{t.mention}, seu desafio é:\n\n**{challenge}**",
            color=0xFF4500
        )
        await ctx.reply(embed=embed)

    @commands.command(name="elogio", aliases=["compliment", "elogiar"])
    async def compliment(self, ctx: commands.Context, target: disnake.Member = None):
        """Elogie alguém (ou a si mesmo)."""
        t = target or ctx.author
        msg = random.choice(COMPLIMENTS)
        embed = disnake.Embed(
            title="💖 Elogio Especial!",
            description=f"{t.mention}\n\n{msg}",
            color=0xFF69B4
        )
        await ctx.reply(embed=embed)

    @commands.command(name="zoar", aliases=["xingar", "insultar", "roast"])
    async def roast(self, ctx: commands.Context, target: disnake.Member = None):
        """Zoação carinhosa (sem offensa real!)."""
        if target is None:
            await ctx.reply(f"{emoji.wrong} Mencione alguém para zoar!")
            return
        if target.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Se auto-zoar é muito triste, não faça isso!")
            return
        msg = random.choice(INSULTS_PLAYFUL)
        embed = disnake.Embed(
            title="😈 Zoação Carinhosa",
            description=f"{target.mention}... {msg}",
            color=0x8B0000
        )
        embed.set_footer(text="Apenas uma brincadeira! 💕")
        await ctx.reply(embed=embed)

    @commands.command(name="cara_ou_coroa", aliases=["flipcoin", "moedinha"])
    async def simple_flip(self, ctx: commands.Context):
        """Lança uma moeda simples, sem apostas."""
        result = random.choice(["Cara", "Coroa"])
        em = "🪙" if result == "Cara" else "👑"
        await ctx.reply(f"{em} **{result}!**")

    @commands.command(name="dado_rpg", aliases=["rpg_dice", "d20", "rolar_dado"])
    async def rpg_dice(self, ctx: commands.Context, sides: int = 20):
        """Rola um dado com N lados (padrão: d20)."""
        if sides < 2 or sides > 1000:
            await ctx.reply(f"{emoji.wrong} O dado precisa ter entre 2 e 1000 lados.")
            return
        result = random.randint(1, sides)
        crit = ""
        if sides == 20:
            if result == 20:
                crit = " 🎉 **CRÍTICO!**"
            elif result == 1:
                crit = " 💀 **FALHA CRÍTICA!**"
        await ctx.reply(f"🎲 Dado d{sides}: **{result}**{crit}")

    @commands.command(name="escolher", aliases=["choose", "sortear_opcao"])
    async def choose(self, ctx: commands.Context, *, options: str = None):
        """Escolhe aleatoriamente entre as opções dadas.
        Ex: `escolher pizza | hamburguer | sushi`
        """
        if not options:
            await ctx.reply(f"{emoji.wrong} Use: `escolher opção1 | opção2 | opção3`")
            return
        choices = [o.strip() for o in options.split("|") if o.strip()]
        if len(choices) < 2:
            await ctx.reply(f"{emoji.wrong} Dê pelo menos 2 opções separadas por `|`.")
            return
        chosen = random.choice(choices)
        await ctx.reply(f"🎯 Eu escolho: **{chosen}**!")

    @commands.command(name="numero", aliases=["guessnumber", "adivinhar_numero"])
    async def guess_number(self, ctx: commands.Context, maximo: int = 10):
        """Mini-jogo: adivinhe o número."""
        if maximo < 2 or maximo > 100:
            await ctx.reply(f"{emoji.wrong} Máximo entre 2 e 100.")
            return

        number = random.randint(1, maximo)
        await ctx.reply(f"🔢 Pensei em um número entre **1** e **{maximo}**! Você tem 3 tentativas!")

        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id

        attempts = 3
        for i in range(attempts):
            try:
                msg = await ctx.bot.wait_for("message", check=check, timeout=20.0)
                try:
                    guess = int(msg.content.strip())
                except ValueError:
                    await ctx.send(f"{emoji.wrong} Digite apenas um número!")
                    continue

                if guess == number:
                    reward = 0
                    if EconomyHelper.is_economy_enabled():
                        allowed, reason = EconomyGuard.check(ctx)
                        if not allowed:
                            await ctx.reply(reason, delete_after=6)
                            return
                        reward = (attempts - i) * 30
                        EconomyHelper.add_user_coins(ctx.author.id, reward, reason="Acertou número")
                    bonus = f" +**{reward}** coins! 💰" if reward > 0 else ""
                    await ctx.send(f"🎉 **Acertou! Era {number}!**{bonus}")
                    return
                elif guess < number:
                    await ctx.send(f"📈 Muito baixo! Tentativas restantes: {attempts - i - 1}")
                else:
                    await ctx.send(f"📉 Muito alto! Tentativas restantes: {attempts - i - 1}")
            except Exception:
                await ctx.send(f"⏰ Tempo esgotado! Era **{number}**.")
                return

        await ctx.send(f"💔 Acabou as tentativas! Era **{number}**.")


def setup(bot: commands.Bot):
    bot.add_cog(FunCommand(bot))
