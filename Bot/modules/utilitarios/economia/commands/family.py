import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

class FamilyCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="adotar", aliases=["adopt"])
    async def adopt(self, ctx: commands.Context, target: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        if target is None:
            await ctx.reply(f"{emoji.wrong} Mencione quem você deseja adotar!")
            return

        if target.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Você não pode adotar a si mesmo.")
            return

        if target.bot:
            await ctx.reply(f"{emoji.wrong} Bots não podem ser adotados.")
            return

        # Verificar se o alvo já tem pai/mãe
        child_data = EconomyHelper.get_social_data(target.id)
        if child_data.get("parent"):
            parent_id = child_data["parent"]
            parent = self.bot.get_user(parent_id) or await self.bot.fetch_user(parent_id)
            await ctx.reply(f"{emoji.wrong} **{target.display_name}** já foi adotado(a) por **{parent.display_name if parent else f'ID: {parent_id}'}**!")
            return

        # Pedido de adoção
        msg = await ctx.reply(
            f"👪 **{target.mention}**, **{ctx.author.display_name}** deseja te adotar!\n"
            f"Você aceita ser filho(a) dele(a)? (Responda com `sim` ou `não` em 60s)"
        )

        def check(m):
            return m.author.id == target.id and m.channel.id == ctx.channel.id and m.content.lower() in ["sim", "não", "nao", "aceito"]

        try:
            res = await self.bot.wait_for("message", check=check, timeout=60.0)
            if res.content.lower() in ["sim", "aceito"]:
                EconomyHelper.adopt(ctx.author.id, target.id)
                await ctx.reply(f"👪 Parabéns! **{target.mention}** agora é oficialmente filho(a) de **{ctx.author.mention}**! ❤️")
            else:
                await ctx.reply(f"💔 **{target.display_name}** recusou a adoção. Que triste...")
        except TimeoutError:
            await msg.edit(content=f"⏰ O tempo acabou e **{target.display_name}** não respondeu ao pedido de adoção.")

    @commands.command(name="abandonar", aliases=["abandon"])
    async def abandon(self, ctx: commands.Context, target: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        user_data = EconomyHelper.get_social_data(ctx.author.id)
        
        # Se não mencionou ninguém, tenta abandonar o pai
        if target is None:
            parent_id = user_data.get("parent")
            if not parent_id:
                await ctx.reply(f"{emoji.wrong} Você não tem pais para abandonar ou filhos para mencionar.")
                return
            
            EconomyHelper.abandon(parent_id, ctx.author.id)
            await ctx.reply(f"💔 Você abandonou sua família e não é mais filho(a) de **ID: {parent_id}**.")
            return

        # Se mencionou alguém, tenta abandonar o filho
        if target.id not in user_data.get("children", []):
            await ctx.reply(f"{emoji.wrong} **{target.display_name}** não é seu filho(a).")
            return

        EconomyHelper.abandon(ctx.author.id, target.id)
        await ctx.reply(f"💔 Você abandonou **{target.display_name}**. Ele(a) não é mais seu filho(a).")

    @commands.command(name="familia", aliases=["family", "parentes"])
    async def family(self, ctx: commands.Context, target: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled(): return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        
        target = target or ctx.author
        data = EconomyHelper.get_social_data(target.id)
        
        parent_id = data.get("parent")
        children_ids = data.get("children", [])
        partner_id = data.get("partner")

        embed = disnake.Embed(
            title=f"👪 Família de {target.display_name}",
            color=0x3498DB
        )

        # Cônjuge
        if partner_id:
            partner = self.bot.get_user(partner_id) or await self.bot.fetch_user(partner_id)
            embed.add_field(name="💍 Cônjuge", value=partner.mention if partner else f"ID: {partner_id}", inline=False)
        
        # Pais
        if parent_id:
            parent = self.bot.get_user(parent_id) or await self.bot.fetch_user(parent_id)
            embed.add_field(name="👴 Pai/Mãe", value=parent.mention if parent else f"ID: {parent_id}", inline=False)

        # Filhos
        if children_ids:
            children_list = []
            for cid in children_ids:
                child = self.bot.get_user(cid) or await self.bot.fetch_user(cid)
                children_list.append(child.mention if child else f"ID: {cid}")
            embed.add_field(name="👶 Filhos", value=", ".join(children_list), inline=False)

        if not any([partner_id, parent_id, children_ids]):
            embed.description = "Este usuário ainda não tem uma família formada."

        await ctx.reply(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(FamilyCommand(bot))
