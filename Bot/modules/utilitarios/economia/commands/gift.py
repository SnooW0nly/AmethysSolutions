import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class GiftCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="gift", aliases=["presente", "dar", "oferecer"])
    async def gift(self, ctx: commands.Context, target: disnake.Member = None, *, args: str = None):
        """
        Presentes alguém com coins ou itens.
        `gift @user <valor>` — envia coins (sem taxa)
        `gift @user item <item_id> [qtd]` — envia item do inventário
        """
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("gift"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if target is None or args is None:
            await ctx.reply(
                f"{emoji.wrong} Use:\n"
                f"`gift @user <coins>` — ex: `gift @João 500`\n"
                f"`gift @user item <item_id> [qtd]` — ex: `gift @João item peixe 3`"
            )
            return

        if target.id == ctx.author.id:
            await ctx.reply(f"{emoji.wrong} Você não pode se presentear.")
            return

        if target.bot:
            await ctx.reply(f"{emoji.wrong} Bots não precisam de presentes.")
            return

        cur = EconomyHelper.get_currency_display()
        args_parts = args.strip().split()

        # Gift de item
        if args_parts[0].lower() == "item":
            if len(args_parts) < 2:
                await ctx.reply(f"{emoji.wrong} Informe o item: `gift @user item <item_id> [qtd]`")
                return

            item_id = args_parts[1].lower()
            qty = 1
            if len(args_parts) >= 3:
                try:
                    qty = int(args_parts[2])
                    if qty <= 0:
                        raise ValueError
                except ValueError:
                    await ctx.reply(f"{emoji.wrong} Quantidade inválida.")
                    return

            inv = EconomyHelper.get_inventory(ctx.author.id)
            if not inv or inv.get(item_id, 0) < qty:
                await ctx.reply(f"{emoji.wrong} Você não tem `{qty}x {item_id}` no inventário.")
                return

            EconomyHelper.remove_from_inventory(ctx.author.id, item_id, qty)
            EconomyHelper.add_to_inventory(target.id, item_id, qty)

            shop_items = {it["id"]: it for it in EconomyHelper.get_shop_items()}
            shop_item = shop_items.get(item_id)
            name = shop_item["name"] if shop_item else item_id.replace("_", " ").title()
            em = shop_item.get("emoji", "📦") if shop_item else "📦"

            await ctx.reply(
                f"🎁 **{ctx.author.display_name}** presenteou **{target.display_name}** com:\n"
                f"{em} **{qty}x {name}**!\n"
                f"-# Que presente especial! 💝"
            )
            return

        # Gift de coins
        try:
            amount = int(args_parts[0].replace(",", "").replace(".", ""))
            if amount <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Valor inválido. Use: `gift @user <valor>`")
            return

        cfg = EconomyHelper.get_economy_settings().get("gift", {"min": 1, "max": 0})
        min_g = cfg.get("min", 1)
        max_g = cfg.get("max", 0)

        if amount < min_g:
            await ctx.reply(f"{emoji.wrong} Valor mínimo de presente: `{min_g:,}`.")
            return
        if max_g > 0 and amount > max_g:
            await ctx.reply(f"{emoji.wrong} Valor máximo de presente: `{max_g:,}`.")
            return

        user_coins = EconomyHelper.get_user_coins(ctx.author.id)
        if user_coins < amount:
            await ctx.reply(f"{emoji.wrong} Você não tem coins suficientes. Saldo: `{user_coins:,}`.")
            return

        EconomyHelper.remove_user_coins(ctx.author.id, amount, reason=f"Presente para {target.id}")
        EconomyHelper.add_user_coins(target.id, amount, reason=f"Presente de {ctx.author.id}")

        sender_balance = EconomyHelper.get_user_coins(ctx.author.id)
        await ctx.reply(
            f"🎁 **{ctx.author.display_name}** presenteou **{target.display_name}** com "
            f"**{amount:,}** {cur}! 💝\n"
            f"-# Que generosidade! Saldo restante: {sender_balance:,}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(GiftCommand(bot))
