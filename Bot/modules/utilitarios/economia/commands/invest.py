import random
import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji
from functions.database import database as db
from datetime import datetime, timedelta

INVEST_DB = "database/utilitarios/economia/investments.json"

INVESTMENT_OPTIONS = {
    "poupanca": {
        "name": "Poupança",
        "emoji": "🏦",
        "description": "Seguro e estável. Rendimento garantido.",
        "min_return": 0.02,
        "max_return": 0.05,
        "risk": 0,  # 0% de perda
        "duration_hours": 6,
        "min_amount": 100,
    },
    "acoes": {
        "name": "Ações",
        "emoji": "📈",
        "description": "Risco moderado. Pode render bem ou mal.",
        "min_return": -0.15,
        "max_return": 0.30,
        "risk": 30,  # 30% chance de perda
        "duration_hours": 12,
        "min_amount": 500,
    },
    "crypto": {
        "name": "Criptomoedas",
        "emoji": "₿",
        "description": "Alto risco, alto retorno. Pode ir à lua ou ao abismo.",
        "min_return": -0.50,
        "max_return": 1.50,
        "risk": 50,  # 50% chance de perda
        "duration_hours": 24,
        "min_amount": 200,
    },
    "imovel": {
        "name": "Imóvel",
        "emoji": "🏠",
        "description": "Baixo risco, retorno moderado a longo prazo.",
        "min_return": 0.05,
        "max_return": 0.20,
        "risk": 5,
        "duration_hours": 48,
        "min_amount": 2000,
    },
}


def get_investments(user_id: int) -> list:
    data = db.obter(INVEST_DB)
    return data.get(str(user_id), [])


def save_investments(user_id: int, investments: list):
    data = db.obter(INVEST_DB)
    data[str(user_id)] = investments
    db.salvar(INVEST_DB, data)


class InvestCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="investir", aliases=["invest", "investimento"], invoke_without_subcommand=True)
    async def invest(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cur_name = EconomyHelper.get_currency_name()
        lines = ["# 💹 Opções de Investimento\n"]
        for key, opt in INVESTMENT_OPTIONS.items():
            risk_bar = "🟢" if opt["risk"] == 0 else "🟡" if opt["risk"] < 30 else "🔴" if opt["risk"] >= 50 else "🟠"
            lines.append(
                f"{opt['emoji']} **{opt['name']}** `{key}`\n"
                f"-# {opt['description']}\n"
                f"-# 📈 Retorno: `{opt['min_return']*100:+.0f}%` a `{opt['max_return']*100:+.0f}%` | "
                f"{risk_bar} Risco: `{opt['risk']}%` | ⏱️ `{opt['duration_hours']}h` | "
                f"Mín: `{opt['min_amount']:,}` {cur_name}\n"
                f"-# `investir aplicar {key} <valor>`"
            )
        await ctx.reply("\n".join(lines))

    @invest.command(name="aplicar", aliases=["apply", "colocar"])
    async def invest_apply(self, ctx: commands.Context, inv_type: str = None, amount: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if inv_type is None or amount is None:
            await ctx.reply(f"{emoji.wrong} Use: `investir aplicar <tipo> <valor>`")
            return

        inv_type = inv_type.lower()
        if inv_type not in INVESTMENT_OPTIONS:
            await ctx.reply(f"{emoji.wrong} Tipo inválido. Use `investir` para ver as opções.")
            return

        opt = INVESTMENT_OPTIONS[inv_type]
        try:
            amt = int(amount.replace(",", "").replace(".", ""))
            if amt <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Valor inválido.")
            return

        cur = EconomyHelper.get_currency_display()
        cur_name = EconomyHelper.get_currency_name()

        if amt < opt["min_amount"]:
            await ctx.reply(f"{emoji.wrong} Mínimo para {opt['name']}: `{opt['min_amount']:,}` {cur_name}.")
            return

        if EconomyHelper.get_user_coins(ctx.author.id) < amt:
            await ctx.reply(f"{emoji.wrong} Saldo insuficiente.")
            return

        EconomyHelper.remove_user_coins(ctx.author.id, amt, reason=f"Investimento: {inv_type}")

        investments = get_investments(ctx.author.id)
        matures_at = (datetime.now() + timedelta(hours=opt["duration_hours"])).isoformat()

        investments.append({
            "type": inv_type,
            "amount": amt,
            "invested_at": datetime.now().isoformat(),
            "matures_at": matures_at,
            "claimed": False,
        })
        save_investments(ctx.author.id, investments)

        balance = EconomyHelper.get_user_coins(ctx.author.id)
        await ctx.reply(
            f"{opt['emoji']} **Investimento realizado!**\n"
            f"Tipo: **{opt['name']}** | Valor: **{amt:,}** {cur}\n"
            f"⏱️ Matura em **{opt['duration_hours']}h**\n"
            f"-# Use `investir resgatar` para coletar quando madurar | Saldo: {balance:,}"
        )

    @invest.command(name="carteira", aliases=["portfolio", "meus"])
    async def invest_portfolio(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        investments = get_investments(ctx.author.id)
        active = [i for i in investments if not i["claimed"]]

        if not active:
            await ctx.reply(f"📭 Você não tem investimentos ativos. Use `investir` para ver as opções.")
            return

        cur_name = EconomyHelper.get_currency_name()
        embed = disnake.Embed(title="💼 Sua Carteira de Investimentos", color=0x2ECC71)
        now = datetime.now()

        for i, inv in enumerate(active):
            opt = INVESTMENT_OPTIONS.get(inv["type"], {})
            matures = datetime.fromisoformat(inv["matures_at"])
            ready = now >= matures
            remaining = max(0, (matures - now).total_seconds())
            status = "✅ **Pronto para resgatar!**" if ready else f"⏳ `{EconomyHelper.format_cooldown(remaining)}`"

            embed.add_field(
                name=f"{opt.get('emoji','💹')} {opt.get('name', inv['type'])} — `{inv['amount']:,}` {cur_name}",
                value=status,
                inline=False
            )

        embed.set_footer(text="Use `investir resgatar` para coletar os maduros.")
        await ctx.reply(embed=embed)

    @invest.command(name="resgatar", aliases=["coletar", "collect"])
    async def invest_collect(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        investments = get_investments(ctx.author.id)
        now = datetime.now()
        cur = EconomyHelper.get_currency_display()
        total_earned = 0
        collected = []
        remaining = []

        for inv in investments:
            if inv["claimed"]:
                continue
            matures = datetime.fromisoformat(inv["matures_at"])
            if now >= matures:
                opt = INVESTMENT_OPTIONS.get(inv["type"], {})
                # Calcular retorno
                roll = random.randint(1, 100)
                if roll <= opt.get("risk", 0):
                    # Perda
                    pct = random.uniform(opt["min_return"], 0)
                else:
                    pct = random.uniform(max(0, opt["min_return"]), opt["max_return"])

                earned = int(inv["amount"] * (1 + pct))
                total_earned += earned
                sign = "+" if pct >= 0 else ""
                collected.append(
                    f"{opt.get('emoji','💹')} {opt.get('name','?')}: **{sign}{pct*100:.1f}%** → `{earned:,}`"
                )
                inv["claimed"] = True
            remaining.append(inv)

        if not collected:
            await ctx.reply(f"{emoji.wrong} Nenhum investimento maduro para resgatar.")
            return

        save_investments(ctx.author.id, remaining)
        EconomyHelper.add_user_coins(ctx.author.id, total_earned, reason="Resgate de investimento")
        balance = EconomyHelper.get_user_coins(ctx.author.id)

        await ctx.reply(
            f"💹 **Investimentos Resgatados!**\n"
            + "\n".join(collected) +
            f"\n\n💰 **Total:** `{total_earned:,}` {cur}\n"
            f"-# Saldo atual: {balance:,}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(InvestCommand(bot))
