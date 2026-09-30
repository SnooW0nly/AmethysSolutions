from ..guard import EconomyGuard
import random
import disnake
from disnake.ext import commands
from functions.emoji import emoji

# Formatos de memes em texto
MEME_FORMATS = [
    # (template, slots)
    ("**Ninguém:**\n**{user}:** {text}", 1),
    ("Me: vai dormir cedo hoje\nAlso me às 3am: {text}", 1),
    ("**{user}:** {text}\n**Todo mundo:**\nhttps://tenor.com/search/surprised-pikachu-gifs", 1),
    ("expectativa: {text1}\nrealidade: {text2}", 2),
    ("quando {text}: 😭😭😭", 1),
    ("**{user}** entrando no servidor depois de {text}:", 1),
    ("oi pode me ajudar com {text1}?\n*resolve o problema*\nobrigado!\n*nunca mais aparece*", 1),
    ("🤓☝️ na verdade {text}", 1),
    ("Eu: {text1}\nMeu cérebro às 3am: {text2}", 2),
    ("Como eu acho que sou:\n{text1}\nComo eu realmente sou:\n{text2}", 2),
    ("quando você diz {text1} mas a pessoa entende {text2}", 2),
    ("**{text}** na minha frente:\n😇 😇 😇\n**{text}** quando minha mãe sai:\n😈 😈 😈", 1),
    ("eu: não vou gastar dinheiro hoje\nesse servidor: {text}", 1),
]


class MemegenCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="meme", aliases=["memegen", "criarMeme"])
    async def meme(self, ctx: commands.Context, *, text: str = None):
        """
        Cria um meme de texto aleatório!
        `meme <texto>` — 1 slot
        `meme <texto1> | <texto2>` — 2 slots (se o template precisar)
        """
        if text is None:
            await ctx.reply(
                f"{emoji.wrong} Use: `meme <texto>`\n"
                f"Para 2 textos: `meme <texto1> | <texto2>`"
            )
            return

        parts = [p.strip() for p in text.split("|")]
        text1 = parts[0] if parts else text
        text2 = parts[1] if len(parts) > 1 else "..."

        # Filtrar templates por número de slots
        if len(parts) >= 2:
            options = [f for f in MEME_FORMATS if f[1] == 2]
            if not options:
                options = MEME_FORMATS
        else:
            options = [f for f in MEME_FORMATS if f[1] == 1]

        template, slots = random.choice(options)
        meme_text = template.replace("{user}", ctx.author.display_name)
        meme_text = meme_text.replace("{text1}", text1).replace("{text2}", text2)
        meme_text = meme_text.replace("{text}", text1)

        embed = disnake.Embed(
            description=meme_text,
            color=random.randint(0x000000, 0xFFFFFF)
        )
        embed.set_footer(text=f"Meme gerado por {ctx.author.display_name}")
        await ctx.reply(embed=embed)

    @commands.command(name="quote", aliases=["citacao", "citação", "frase"])
    async def quote(self, ctx: commands.Context, *, text: str = None):
        """Transforma seu texto em uma citação épica."""
        if not text:
            await ctx.reply(f"{emoji.wrong} Use: `quote <sua frase>`")
            return

        embed = disnake.Embed(
            description=f"*\"{text}\"*",
            color=0x2B2D31
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Uma frase para os livros de história.")
        await ctx.reply(embed=embed)

    @commands.command(name="ascii", aliases=["emojify", "texto_emoji"])
    async def ascii_art(self, ctx: commands.Context, *, text: str = None):
        """Converte texto em emojis de letras."""
        if not text:
            await ctx.reply(f"{emoji.wrong} Use: `ascii <texto>`")
            return

        if len(text) > 20:
            await ctx.reply(f"{emoji.wrong} Máximo de 20 caracteres.")
            return

        LETTER_MAP = {c: f":regional_indicator_{c}: " for c in "abcdefghijklmnopqrstuvwxyz"}
        DIGIT_MAP = {
            "0": "0️⃣ ", "1": "1️⃣ ", "2": "2️⃣ ", "3": "3️⃣ ", "4": "4️⃣ ",
            "5": "5️⃣ ", "6": "6️⃣ ", "7": "7️⃣ ", "8": "8️⃣ ", "9": "9️⃣ ",
            " ": "  "
        }
        result = ""
        for c in text.lower():
            if c in LETTER_MAP:
                result += LETTER_MAP[c]
            elif c in DIGIT_MAP:
                result += DIGIT_MAP[c]
            else:
                result += "❓ "

        await ctx.reply(result[:500])

    @commands.command(name="owoify", aliases=["owo", "uwu"])
    async def owoify(self, ctx: commands.Context, *, text: str = None):
        """Transforma seu texto em owo."""
        if not text:
            await ctx.reply(f"{emoji.wrong} Use: `owoify <texto>`")
            return

        replacements = {
            "r": "w", "l": "w", "R": "W", "L": "W",
            "n": "ny", "N": "NY", "ove": "uv",
        }
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)

        faces = ["owo", "uwu", ">w<", "^w^", "UwU", "ÙwÚ"]
        result += f" {random.choice(faces)}"
        await ctx.reply(result[:500])

    @commands.command(name="vaporwave", aliases=["fullwidth", "vaporizar"])
    async def vaporwave(self, ctx: commands.Context, *, text: str = None):
        """Transforma texto em v a p o r w a v e."""
        if not text:
            await ctx.reply(f"{emoji.wrong} Use: `vaporwave <texto>`")
            return
        result = " ".join(c.upper() for c in text)
        await ctx.reply(result[:400])


def setup(bot: commands.Bot):
    bot.add_cog(MemegenCommand(bot))
