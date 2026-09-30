import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class BalanceCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="balance", aliases=["saldo", "bal", "coins", "carteira"])
    async def balance(self, ctx: commands.Context, member: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("balance"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        target = member or ctx.author
        coins = EconomyHelper.get_user_coins(target.id)
        bank = EconomyHelper.get_user_bank(target.id)
        cur = EconomyHelper.get_currency_display()

        # Social Info
        partner_id = EconomyHelper.get_partner(target.id)
        partner_str = ""
        if partner_id:
            partner = self.bot.get_user(partner_id) or await self.bot.fetch_user(partner_id)
            partner_str = f"\n💍 **Casado(a) com:** {partner.mention if partner else f'ID: {partner_id}'}"

        # Streak info
        streak_line = ""
        streak = EconomyHelper.get_streak(target.id, "daily")
        count = streak.get("count", 0)
        if count > 0:
            streak_line = f"\n🔥 **Streak Daily:** {count} {'dia' if count == 1 else 'dias'}"

        embed = disnake.Embed(
            title=f"💰 Saldo de {target.display_name}",
            color=0x2B2D31
        )
        embed.add_field(name="💵 Carteira", value=f"**{coins:,}** {cur}", inline=True)
        embed.add_field(name="🏦 Banco", value=f"**{bank:,}** {cur}", inline=True)
        embed.add_field(name="📊 Total", value=f"**{coins + bank:,}** {cur}", inline=False)
        
        # Reputação e Interações
        social_data = EconomyHelper.get_social_data(target.id)
        reps = social_data.get("reps", 0)
        
        extra_info = f"{streak_line}{partner_str}\n⭐ **Reputação:** {reps}"
        
        # Pais/Filhos simplificado
        parent_id = social_data.get("parent")
        if parent_id:
            extra_info += f"\n👴 **Filho(a) de:** <@{parent_id}>"
            
        children = social_data.get("children", [])
        if children:
            extra_info += f"\n👶 **Filhos:** {len(children)}"

        if extra_info:
            embed.description = extra_info

        await ctx.reply(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(BalanceCommand(bot))