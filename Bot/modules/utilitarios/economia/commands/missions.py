import random
import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji
from functions.database import database as db
from datetime import date, datetime

MISSIONS_DB = "database/utilitarios/economia/missions.json"

DAILY_MISSIONS_POOL = [
    {"id": "work_3",    "name": "Workaholic",       "desc": "Trabalhe 3 vezes",            "type": "work",    "target": 3,    "reward": 300,  "emoji": "💼"},
    {"id": "fish_2",    "name": "Pescador",          "desc": "Pesque 2 vezes",              "type": "fish",    "target": 2,    "reward": 200,  "emoji": "🎣"},
    {"id": "crime_1",   "name": "Do Crime",          "desc": "Cometa 1 crime",              "type": "crime",   "target": 1,    "reward": 250,  "emoji": "🔫"},
    {"id": "mine_2",    "name": "Minerador",         "desc": "Minere 2 vezes",              "type": "mine",    "target": 2,    "reward": 220,  "emoji": "⛏️"},
    {"id": "hunt_2",    "name": "Caçador",           "desc": "Caçe 2 vezes",                "type": "hunt",    "target": 2,    "reward": 200,  "emoji": "🏹"},
    {"id": "rep_1",     "name": "Generoso",          "desc": "Dê 1 reputação a alguém",     "type": "rep",     "target": 1,    "reward": 150,  "emoji": "⭐"},
    {"id": "pay_1",     "name": "Doador",            "desc": "Envie coins para alguém",     "type": "pay",     "target": 1,    "reward": 180,  "emoji": "💸"},
    {"id": "slots_3",   "name": "Cassino",           "desc": "Jogue slots 3 vezes",         "type": "slots",   "target": 3,    "reward": 280,  "emoji": "🎰"},
    {"id": "rob_1",     "name": "Ladrão Novato",     "desc": "Tente roubar alguém",         "type": "rob",     "target": 1,    "reward": 200,  "emoji": "🥷"},
    {"id": "interact_3","name": "Social Butterfly",  "desc": "Interaja 3x com alguém",      "type": "interact","target": 3,    "reward": 200,  "emoji": "💕"},
]


def get_missions_data(user_id: int) -> dict:
    data = db.obter(MISSIONS_DB)
    return data.get(str(user_id), {})


def save_missions_data(user_id: int, mdata: dict):
    data = db.obter(MISSIONS_DB)
    data[str(user_id)] = mdata
    db.salvar(MISSIONS_DB, data)


def get_or_create_daily_missions(user_id: int) -> list:
    """Retorna as missões do dia, gerando novas se necessário."""
    today = str(date.today())
    mdata = get_missions_data(user_id)

    if mdata.get("date") == today:
        return mdata.get("missions", [])

    # Gerar 3 missões aleatórias do dia
    chosen = random.sample(DAILY_MISSIONS_POOL, 3)
    missions = [
        {**m, "progress": 0, "completed": False, "claimed": False}
        for m in chosen
    ]
    mdata = {"date": today, "missions": missions}
    save_missions_data(user_id, mdata)
    return missions


def increment_mission_progress(user_id: int, mission_type: str, amount: int = 1):
    """Incrementa o progresso de missões do tipo dado."""
    today = str(date.today())
    mdata = get_missions_data(user_id)
    if mdata.get("date") != today:
        return

    missions = mdata.get("missions", [])
    changed = False
    for m in missions:
        if m["type"] == mission_type and not m["completed"]:
            m["progress"] = min(m["target"], m["progress"] + amount)
            if m["progress"] >= m["target"]:
                m["completed"] = True
            changed = True

    if changed:
        mdata["missions"] = missions
        save_missions_data(user_id, mdata)


class MissionsCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="missoes", aliases=["missions", "tarefas", "missões"])
    async def missions(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("missions"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        missions = get_or_create_daily_missions(ctx.author.id)
        cur_name = EconomyHelper.get_currency_name()

        embed = disnake.Embed(
            title="📋 Missões Diárias",
            description="Complete missões para ganhar recompensas extras!",
            color=0x9B59B6
        )

        for m in missions:
            status = ""
            if m["claimed"]:
                status = "✅ **RESGATADO**"
            elif m["completed"]:
                status = "🎁 **COMPLETO** — use `missoes resgatar`"
            else:
                bar_filled = int((m["progress"] / m["target"]) * 5)
                bar = "🟣" * bar_filled + "⚫" * (5 - bar_filled)
                status = f"`{m['progress']}/{m['target']}` {bar}"

            embed.add_field(
                name=f"{m['emoji']} {m['name']}",
                value=f"{m['desc']}\n{status}\n💰 Recompensa: `{m['reward']:,}` {cur_name}",
                inline=False
            )

        embed.set_footer(text="Missões renovam à meia-noite!")
        await ctx.reply(embed=embed)

    @commands.command(name="missoes_resgatar", aliases=["claim_mission", "missoes_claim"])
    async def claim_missions(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        missions = get_or_create_daily_missions(ctx.author.id)
        mdata = get_missions_data(ctx.author.id)
        cur = EconomyHelper.get_currency_display()

        total_earned = 0
        claimed_names = []

        for m in missions:
            if m["completed"] and not m["claimed"]:
                m["claimed"] = True
                total_earned += m["reward"]
                claimed_names.append(f"{m['emoji']} {m['name']}")

        if total_earned == 0:
            await ctx.reply(f"{emoji.wrong} Nenhuma missão completa para resgatar.")
            return

        mdata["missions"] = missions
        save_missions_data(ctx.author.id, mdata)
        EconomyHelper.add_user_coins(ctx.author.id, total_earned, reason="Missões Diárias", member=ctx.author)

        balance = EconomyHelper.get_user_coins(ctx.author.id)
        await ctx.reply(
            f"🎁 **Recompensas resgatadas!**\n"
            + "\n".join(claimed_names) +
            f"\n\n💰 **+{total_earned:,}** {cur}\n"
            f"-# Saldo atual: {balance:,}"
        )


def setup(bot: commands.Bot):
    bot.add_cog(MissionsCommand(bot))
