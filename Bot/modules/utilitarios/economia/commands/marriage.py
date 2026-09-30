import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji
from datetime import datetime

class MarriageCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="casar", aliases=["marry"])
    async def marry(self, ctx: commands.Context, target: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        if target is None:
            await ctx.reply(f"{emoji.wrong} Mencione quem você deseja pedir em casamento!")
            return

        if target.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Você não pode casar consigo mesmo.")
            return

        if target.bot:
            await ctx.reply(f"{emoji.wrong} Você não pode casar com um bot.")
            return

        # Verificar se algum já é casado
        if EconomyHelper.get_partner(ctx.author.id):
            await ctx.reply(f"{emoji.wrong} Você já é casado!")
            return

        if EconomyHelper.get_partner(target.id):
            await ctx.reply(f"{emoji.wrong} **{target.display_name}** já é casado!")
            return

        # Pedido de casamento
        msg = await ctx.reply(
            f"💍 **{target.mention}**, **{ctx.author.display_name}** está te pedindo em casamento!\n"
            f"Você aceita? (Responda com `sim` ou `não` em 60s)"
        )

        def check(m):
            return m.author.id == target.id and m.channel.id == ctx.channel.id and m.content.lower() in ["sim", "não", "nao", "aceito"]

        try:
            res = await self.bot.wait_for("message", check=check, timeout=60.0)
            if res.content.lower() in ["sim", "aceito"]:
                EconomyHelper.set_marriage(ctx.author.id, target.id)
                await ctx.reply(f"🎉 **{ctx.author.mention}** e **{target.mention}** agora estão oficialmente casados! 💍❤️")
            else:
                await ctx.reply(f"💔 **{target.display_name}** recusou o pedido. Que triste...")
        except TimeoutError:
            await msg.edit(content=f"⏰ O tempo acabou e **{target.display_name}** não respondeu ao pedido.")

    @commands.command(name="divorciar", aliases=["divorce"])
    async def divorce(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        partner_id = EconomyHelper.get_partner(ctx.author.id)
        if not partner_id:
            await ctx.reply(f"{emoji.wrong} Você não é casado.")
            return

        partner = self.bot.get_user(partner_id) or await self.bot.fetch_user(partner_id)
        partner_name = partner.display_name if partner else f"ID: {partner_id}"

        EconomyHelper.divorce(ctx.author.id)
        await ctx.reply(f"💔 Você se divorciou de **{partner_name}**. O amor acabou...")

def setup(bot: commands.Bot):
    bot.add_cog(MarriageCommand(bot))
