import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


# ─── LOJA ─────────────────────────────────────────────────────────────────────

class ShopCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="shop", aliases=["loja", "store"])
    async def shop(self, ctx: commands.Context, page: int = 1):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("shop"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        items = EconomyHelper.get_shop_items()
        cur_name = EconomyHelper.get_currency_name()
        cur_em = EconomyHelper.get_currency_emoji()

        if not items:
            await ctx.reply(f"🛒 A loja está vazia no momento.")
            return

        per_page = 8
        pages = (len(items) + per_page - 1) // per_page
        page = max(1, min(page, pages))
        start = (page - 1) * per_page
        chunk = items[start:start + per_page]

        lines = [f"# 🛒 Loja — {cur_em} {cur_name}", f"-# Página {page}/{pages}\n"]
        for item in chunk:
            role_tag = f" *(dá cargo)*" if item.get("role_id") else ""
            lines.append(
                f"{item.get('emoji','📦')} **{item['name']}** — `{item['price']:,}` {cur_name}\n"
                f"  └ {item['description']}{role_tag}"
            )
        lines.append(f"\n-# Use `buy <id_do_item>` para comprar. Ex: `buy {items[0]['id']}`")

        await ctx.reply("\n".join(lines))


# ─── COMPRAR ──────────────────────────────────────────────────────────────────

class BuyCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="buy", aliases=["comprar", "adquirir"])
    async def buy(self, ctx: commands.Context, item_id: str = None, quantity: int = 1):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("buy"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if item_id is None:
            await ctx.reply(f"{emoji.wrong} Use: `buy <id_do_item> [quantidade]`")
            return

        item = EconomyHelper.get_shop_item(item_id.lower())
        if not item:
            await ctx.reply(f"{emoji.wrong} Item `{item_id}` não encontrado na loja.")
            return

        if quantity < 1:
            await ctx.reply(f"{emoji.wrong} Quantidade inválida.")
            return

        total = item["price"] * quantity
        user_coins = EconomyHelper.get_user_coins(ctx.author.id)
        cur = EconomyHelper.get_currency_display()

        if user_coins < total:
            await ctx.reply(
                f"{emoji.wrong} Coins insuficientes.\n"
                f"Preço total: `{total:,}` | Seu saldo: `{user_coins:,}`"
            )
            return

        EconomyHelper.remove_user_coins(ctx.author.id, total, reason=f"Compra: {item['name']}")
        EconomyHelper.add_to_inventory(ctx.author.id, item_id.lower(), quantity)

        # Se tiver role_id configurado, tentar dar cargo
        if item.get("role_id"):
            try:
                role = ctx.guild.get_role(item["role_id"])
                if role:
                    await ctx.author.add_roles(role, reason=f"Comprou {item['name']} na loja")
            except Exception:
                pass

        balance = EconomyHelper.get_user_coins(ctx.author.id)
        qty_txt = f"x{quantity} " if quantity > 1 else ""
        await ctx.reply(
            f"{emoji.success} Você comprou {qty_txt}**{item.get('emoji','')} {item['name']}** "
            f"por `{total:,}` {cur}!\n"
            f"-# Saldo atual: {balance:,}"
        )


# ─── INVENTÁRIO ───────────────────────────────────────────────────────────────

class InventoryCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="inventory", aliases=["inventario", "inv", "bag", "mochila"])
    async def inventory(self, ctx: commands.Context, member: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("inventory"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        target = member or ctx.author
        inv = EconomyHelper.get_inventory(target.id)

        if not inv:
            who = "Você não tem" if target.id == ctx.author.id else f"{target.display_name} não tem"
            await ctx.reply(f"🎒 {who} nada no inventário.")
            return

        shop_items = {it["id"]: it for it in EconomyHelper.get_shop_items()}
        lines = [f"# 🎒 Inventário de {target.display_name}\n"]

        for item_id, qty in sorted(inv.items(), key=lambda x: x[0]):
            shop_item = shop_items.get(item_id)
            if shop_item:
                em = shop_item.get("emoji", "📦")
                name = shop_item["name"]
            else:
                # Itens de gather (fish_, mine_, hunt_)
                parts = item_id.split("_", 1)
                em = {"fish": "🐟", "mine": "💎", "hunt": "🏹"}.get(parts[0], "📦")
                name = parts[1].replace("_", " ").title() if len(parts) > 1 else item_id
            lines.append(f"{em} **{name}** × `{qty}`")

        await ctx.reply("\n".join(lines))


def setup(bot: commands.Bot):
    bot.add_cog(ShopCommand(bot))
    bot.add_cog(BuyCommand(bot))
    bot.add_cog(InventoryCommand(bot))