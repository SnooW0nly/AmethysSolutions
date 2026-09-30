from ..guard import EconomyGuard
import asyncio
import disnake
from disnake.ext import commands
from functions.emoji import emoji


class RemindCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="lembrar", aliases=["remind", "reminder", "lembre"])
    async def remind(self, ctx: commands.Context, duration: str = None, *, message: str = None):
        """
        Cria um lembrete para você.
        `lembrar <duração> <mensagem>`
        Ex: `lembrar 30m buscar a pizza`
        Durações: `Ns` (segundos), `Nm` (minutos), `Nh` (horas)
        """
        if duration is None or message is None:
            await ctx.reply(
                f"⏰ Use: `lembrar <duração> <mensagem>`\n"
                f"Ex: `lembrar 30m buscar a pizza`\n"
                f"Ex: `lembrar 2h reunião importante`"
            )
            return

        dur_lower = duration.lower()
        try:
            if dur_lower.endswith("s"):
                seconds = int(dur_lower[:-1])
            elif dur_lower.endswith("m"):
                seconds = int(dur_lower[:-1]) * 60
            elif dur_lower.endswith("h"):
                seconds = int(dur_lower[:-1]) * 3600
            elif dur_lower.endswith("d"):
                seconds = int(dur_lower[:-1]) * 86400
            else:
                seconds = int(dur_lower)
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Duração inválida. Ex: `30s`, `5m`, `2h`, `1d`")
            return

        if seconds < 5:
            await ctx.reply(f"{emoji.wrong} Mínimo de 5 segundos.")
            return
        if seconds > 604800:
            await ctx.reply(f"{emoji.wrong} Máximo de 7 dias.")
            return

        if seconds < 60:
            dur_str = f"{seconds}s"
        elif seconds < 3600:
            dur_str = f"{seconds // 60}min"
        elif seconds < 86400:
            dur_str = f"{seconds // 3600}h"
        else:
            dur_str = f"{seconds // 86400}d"

        await ctx.reply(
            f"⏰ **Lembrete definido!**\n"
            f"Vou te avisar em **{dur_str}**:\n"
            f"> {message}"
        )

        await asyncio.sleep(seconds)

        try:
            await ctx.author.send(
                f"⏰ **LEMBRETE!**\n> {message}\n\n-# Definido em {ctx.guild.name} — #{ctx.channel.name}"
            )
        except disnake.Forbidden:
            await ctx.channel.send(
                f"⏰ {ctx.author.mention} **LEMBRETE!**\n> {message}"
            )

    @commands.command(name="timer", aliases=["cronometro", "conta_regressiva"])
    async def timer(self, ctx: commands.Context, duration: str = None, *, label: str = ""):
        """
        Timer de contagem regressiva público no canal.
        `timer <duração> [label]`
        Ex: `timer 5m votação`
        """
        if not duration:
            await ctx.reply(f"{emoji.wrong} Use: `timer <duração> [descrição]`\nEx: `timer 5m votação`")
            return

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
            await ctx.reply(f"{emoji.wrong} Duração inválida.")
            return

        if seconds < 5 or seconds > 3600:
            await ctx.reply(f"{emoji.wrong} Timer entre 5s e 1h.")
            return

        label_txt = f" — {label}" if label else ""
        msg = await ctx.send(f"⏱️ **Timer{label_txt}** — `{seconds}s` restantes...")

        await asyncio.sleep(seconds)

        try:
            await msg.edit(content=f"⏰ **Timer{label_txt} concluído!** @here")
        except Exception:
            await ctx.send(f"⏰ **Timer{label_txt} concluído!**")


def setup(bot: commands.Bot):
    bot.add_cog(RemindCommand(bot))
