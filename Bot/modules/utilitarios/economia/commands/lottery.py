import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji
from functions.database import database as db

LOTTERY_DB = "database/utilitarios/economia/lottery.json"


def get_lottery_data() -> dict:
    data = db.obter(LOTTERY_DB)
    if not data:
        data = {"jackpot": 5000, "tickets": {}, "last_winner": None}
    return data


def save_lottery_data(data: dict):
    db.salvar(LOTTERY_DB, data)


class LotteryCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="lottery", aliases=["loteria", "loto"])
    async def lottery(self, ctx: commands.Context, action: str = None, amount: str = None):
        """
        `lottery` — ver jackpot atual
        `lottery buy [qtd]` — comprar tickets
        `lottery tickets` — ver seus tickets
        `lottery draw` (admin) — realizar o sorteio
        """
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("lottery"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cur = EconomyHelper.get_currency_display()
        cfg = EconomyHelper.get_economy_settings().get("lottery", {
            "ticket_price": 100,
            "jackpot_seed": 5000,
            "min_participants": 2,
        })
        ticket_price = cfg.get("ticket_price", 100)
        data = get_lottery_data()

        # Sem ação = mostrar jackpot
        if action is None:
            total_tickets = sum(data.get("tickets", {}).values())
            user_tickets = data["tickets"].get(str(ctx.author.id), 0)
            await ctx.reply(
                f"🎰 **Loteria do Servidor**\n\n"
                f"💰 **Jackpot atual:** `{data['jackpot']:,}` {cur}\n"
                f"🎟️ **Tickets vendidos:** `{total_tickets}`\n"
                f"🎫 **Seus tickets:** `{user_tickets}`\n\n"
                f"-# Use `lottery buy [qtd]` para comprar tickets (preço: `{ticket_price:,}` cada)\n"
                f"-# Mais tickets = mais chances de ganhar!"
            )
            return

        action = action.lower()

        if action in ["buy", "comprar"]:
            qty = 1
            if amount:
                try:
                    qty = int(amount)
                    if qty <= 0:
                        raise ValueError
                except ValueError:
                    await ctx.reply(f"{emoji.wrong} Quantidade inválida.")
                    return

            total_cost = ticket_price * qty
            user_coins = EconomyHelper.get_user_coins(ctx.author.id)
            if user_coins < total_cost:
                await ctx.reply(
                    f"{emoji.wrong} Saldo insuficiente.\n"
                    f"Necessário: `{total_cost:,}` | Seu saldo: `{user_coins:,}`"
                )
                return

            EconomyHelper.remove_user_coins(ctx.author.id, total_cost, reason="Compra de tickets")
            uid = str(ctx.author.id)
            data["tickets"][uid] = data["tickets"].get(uid, 0) + qty
            data["jackpot"] += int(total_cost * 0.8)  # 80% vai pro jackpot
            save_lottery_data(data)

            balance = EconomyHelper.get_user_coins(ctx.author.id)
            await ctx.reply(
                f"🎟️ Você comprou **{qty} ticket{'s' if qty > 1 else ''}** por `{total_cost:,}` {cur}!\n"
                f"💰 Jackpot atual: `{data['jackpot']:,}` {cur}\n"
                f"🎫 Total de tickets seus: `{data['tickets'][uid]}`\n"
                f"-# Saldo atual: {balance:,}"
            )

        elif action in ["tickets", "meus"]:
            user_tickets = data["tickets"].get(str(ctx.author.id), 0)
            total_tickets = sum(data["tickets"].values())
            if total_tickets > 0:
                chance = (user_tickets / total_tickets) * 100
                chance_str = f"**{chance:.1f}%** de chance de ganhar"
            else:
                chance_str = "Sem participantes ainda"
            await ctx.reply(
                f"🎫 **Seus tickets:** `{user_tickets}`\n"
                f"📊 {chance_str}\n"
                f"💰 Jackpot: `{data['jackpot']:,}` {cur}"
            )

        elif action in ["draw", "sortear"]:
            # Verificar admin
            if not ctx.author.guild_permissions.administrator:
                await ctx.reply(f"{emoji.wrong} Apenas administradores podem realizar o sorteio.")
                return

            tickets = data.get("tickets", {})
            min_p = cfg.get("min_participants", 2)
            if len(tickets) < min_p:
                await ctx.reply(f"{emoji.wrong} Precisam de pelo menos **{min_p}** participantes.")
                return

            # Sortear por peso de tickets
            pool = []
            for uid, qty in tickets.items():
                pool.extend([uid] * qty)

            winner_id = int(random.choice(pool))
            winner = ctx.guild.get_member(winner_id) or await ctx.guild.fetch_member(winner_id)
            jackpot = data["jackpot"]

            EconomyHelper.add_user_coins(winner_id, jackpot, reason="Loteria - Jackpot!")
            balance = EconomyHelper.get_user_coins(winner_id)

            # Reset
            data["tickets"] = {}
            data["jackpot"] = cfg.get("jackpot_seed", 5000)
            data["last_winner"] = str(winner_id)
            save_lottery_data(data)

            await ctx.reply(
                f"🎉🎰 **SORTEIO DA LOTERIA!** 🎰🎉\n\n"
                f"🏆 **VENCEDOR:** {winner.mention if winner else f'<@{winner_id}>'}\n"
                f"💰 **Prêmio:** `{jackpot:,}` {cur}\n\n"
                f"-# Novo jackpot começa em `{data['jackpot']:,}`! Compre seus tickets com `lottery buy`"
            )

        else:
            await ctx.reply(f"{emoji.wrong} Ação inválida. Use: `lottery`, `lottery buy [qtd]`, `lottery tickets`")


def setup(bot: commands.Bot):
    bot.add_cog(LotteryCommand(bot))
