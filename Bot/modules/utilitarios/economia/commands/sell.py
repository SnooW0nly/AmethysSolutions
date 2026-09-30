import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


# Preços base para itens de gather (fish, mine, hunt)
SELL_PRICES = {
    # Fish
    "fish_peixinho_pequeno": 15,
    "fish_peixe_medio": 50,
    "fish_peixe_médio": 50,
    "fish_peixão": 120,
    "fish_peixao": 120,
    "fish_tesouro_submerso": 400,
    # Mine
    "mine_pedra_comum": 15,
    "mine_carvão": 45,
    "mine_carvao": 45,
    "mine_ferro": 90,
    "mine_diamante": 280,
    "mine_cristal_raro": 700,
    # Hunt
    "hunt_coelho": 25,
    "hunt_veado": 70,
    "hunt_javali": 110,
    "hunt_lobo_raro": 260,
    "hunt_dragão_lendário": 650,
    "hunt_dragao_lendario": 650,
}


def get_sell_price(item_id: str, shop_price: int = 0) -> int:
    if item_id in SELL_PRICES:
        return SELL_PRICES[item_id]
    if shop_price > 0:
        return max(1, int(shop_price * 0.5))  # 50% do preço da loja
    return 0


class SellCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sell", aliases=["vender", "venda"])
    async def sell(self, ctx: commands.Context, item_id: str = None, quantity: str = None):
        """
        Vende itens do seu inventário.
        `sell <item_id> [quantidade]`
        `sell all` — vende TODOS os itens vendáveis
        """
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("sell"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cur = EconomyHelper.get_currency_display()
        inv = EconomyHelper.get_inventory(ctx.author.id)

        if not inv:
            await ctx.reply(f"{emoji.wrong} Seu inventário está vazio.")
            return

        if item_id is None:
            await ctx.reply(
                f"{emoji.wrong} Use: `sell <item_id> [qtd]` ou `sell all`\n"
                f"Veja seu inventário com `inv`."
            )
            return

        shop_items = {it["id"]: it for it in EconomyHelper.get_shop_items()}

        # Vender tudo
        if item_id.lower() == "all":
            total_earned = 0
            sold_items = []

            for iid, qty in list(inv.items()):
                shop_item = shop_items.get(iid)
                shop_price = shop_item["price"] if shop_item else 0
                price = get_sell_price(iid, shop_price)
                if price > 0:
                    earned = price * qty
                    total_earned += earned
                    name = shop_item["name"] if shop_item else iid.replace("_", " ").title()
                    sold_items.append(f"`{qty}x {name}` → {earned:,}")
                    EconomyHelper.remove_from_inventory(ctx.author.id, iid, qty)

            if total_earned == 0:
                await ctx.reply(f"{emoji.wrong} Nenhum item vendável no inventário.")
                return

            EconomyHelper.add_user_coins(ctx.author.id, total_earned, reason="Venda de itens")
            balance = EconomyHelper.get_user_coins(ctx.author.id)

            lines = "\n".join(sold_items[:10])
            if len(sold_items) > 10:
                lines += f"\n... e mais {len(sold_items) - 10} itens"

            await ctx.reply(
                f"💰 **Vendeu tudo!**\n{lines}\n\n"
                f"💵 **Total recebido:** {total_earned:,} {cur}\n"
                f"-# Saldo atual: {balance:,}"
            )
            return

        # Vender item específico
        iid = item_id.lower()
        if iid not in inv or inv[iid] <= 0:
            await ctx.reply(f"{emoji.wrong} Item `{item_id}` não encontrado no seu inventário.")
            return

        qty_available = inv[iid]
        if quantity is None or quantity.lower() == "all":
            qty_to_sell = qty_available
        else:
            try:
                qty_to_sell = int(quantity)
                if qty_to_sell <= 0:
                    raise ValueError
            except ValueError:
                await ctx.reply(f"{emoji.wrong} Quantidade inválida.")
                return

        if qty_to_sell > qty_available:
            await ctx.reply(f"{emoji.wrong} Você tem apenas `{qty_available}` desse item.")
            return

        shop_item = shop_items.get(iid)
        shop_price = shop_item["price"] if shop_item else 0
        price = get_sell_price(iid, shop_price)

        if price == 0:
            await ctx.reply(f"{emoji.wrong} Esse item não pode ser vendido.")
            return

        total_earned = price * qty_to_sell
        EconomyHelper.remove_from_inventory(ctx.author.id, iid, qty_to_sell)
        EconomyHelper.add_user_coins(ctx.author.id, total_earned, reason=f"Venda: {iid}")

        name = shop_item["name"] if shop_item else iid.replace("_", " ").title()
        balance = EconomyHelper.get_user_coins(ctx.author.id)

        await ctx.reply(
            f"💰 Você vendeu **{qty_to_sell}x {name}** por **{total_earned:,}** {cur}!\n"
            f"-# Preço unitário: {price:,} | Saldo atual: {balance:,}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(SellCommand(bot))
