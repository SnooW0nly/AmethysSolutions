from ..guard import EconomyGuard
import asyncio
import disnake
from disnake.ext import commands
from functions.emoji import emoji

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


class PollCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_polls = {}

    @commands.command(name="poll", aliases=["enquete", "votacao", "votação"])
    async def poll(self, ctx: commands.Context, duration: str = None, *, question_and_options: str = None):
        """
        Cria uma enquete no canal.
        `poll <duração> <pergunta> | <opção1> | <opção2> ...`
        Ex: `poll 1m Qual melhor cor? | Azul | Verde | Vermelho`
        Duração: `30s`, `5m`, `1h`
        """
        if duration is None or question_and_options is None:
            await ctx.reply(
                f"{emoji.wrong} Use: `poll <duração> <pergunta> | <op1> | <op2> ...`\n"
                f"Ex: `poll 1m Qual cor preferida? | Azul | Verde | Vermelho`"
            )
            return

        # Parse duração
        dur_lower = duration.lower()
        try:
            if dur_lower.endswith("s"):
                seconds = int(dur_lower[:-1])
            elif dur_lower.endswith("m"):
                seconds = int(dur_lower[:-1]) * 60
            elif dur_lower.endswith("h"):
                seconds = int(dur_lower[:-1]) * 3600
            else:
                seconds = int(dur_lower)
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Duração inválida. Use: `30s`, `5m`, `1h`")
            return

        if seconds < 10 or seconds > 86400:
            await ctx.reply(f"{emoji.wrong} Duração entre 10s e 24h.")
            return

        parts = [p.strip() for p in question_and_options.split("|")]
        question = parts[0]
        options = parts[1:]

        if len(options) < 2:
            await ctx.reply(f"{emoji.wrong} Dê pelo menos 2 opções separadas por `|`.")
            return
        if len(options) > 10:
            await ctx.reply(f"{emoji.wrong} Máximo de 10 opções.")
            return

        dur_display = f"{seconds}s" if seconds < 60 else f"{seconds//60}m" if seconds < 3600 else f"{seconds//3600}h"

        description_lines = [f"**{question}**\n"]
        for i, opt in enumerate(options):
            description_lines.append(f"{NUMBER_EMOJIS[i]} {opt}")
        description_lines.append(f"\n⏱️ Duração: **{dur_display}**")

        embed = disnake.Embed(
            title="📊 Enquete!",
            description="\n".join(description_lines),
            color=0x3498DB
        )
        embed.set_footer(text=f"Criada por {ctx.author.display_name}")

        msg = await ctx.send(embed=embed)

        for i in range(len(options)):
            await msg.add_reaction(NUMBER_EMOJIS[i])

        await asyncio.sleep(seconds)

        # Resultados
        try:
            msg = await ctx.channel.fetch_message(msg.id)
        except Exception:
            return

        results = []
        total_votes = 0
        for i, opt in enumerate(options):
            reaction = next((r for r in msg.reactions if str(r.emoji) == NUMBER_EMOJIS[i]), None)
            count = (reaction.count - 1) if reaction else 0  # -1 para remover voto do bot
            total_votes += count
            results.append((opt, count))

        results.sort(key=lambda x: x[1], reverse=True)

        result_lines = [f"**{question}**\n"]
        for i, (opt, count) in enumerate(results):
            pct = (count / total_votes * 100) if total_votes > 0 else 0
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "  "
            result_lines.append(f"{medal} **{opt}** — `{count}` votos ({pct:.1f}%)\n`{bar}`")

        result_lines.append(f"\n👥 Total de votos: **{total_votes}**")

        embed_result = disnake.Embed(
            title="📊 Resultado da Enquete!",
            description="\n".join(result_lines),
            color=0xFFD700
        )
        await ctx.send(embed=embed_result)

    @commands.command(name="yesno", aliases=["simnao", "simnão", "votorapido"])
    async def yesno_poll(self, ctx: commands.Context, *, question: str = None):
        """Enquete rápida de Sim/Não."""
        if not question:
            await ctx.reply(f"{emoji.wrong} Use: `yesno <pergunta>`")
            return

        embed = disnake.Embed(
            title="🗳️ Votação Rápida",
            description=f"**{question}**",
            color=0x2ECC71
        )
        embed.set_footer(text=f"Por {ctx.author.display_name}")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")


def setup(bot: commands.Bot):
    bot.add_cog(PollCommand(bot))
