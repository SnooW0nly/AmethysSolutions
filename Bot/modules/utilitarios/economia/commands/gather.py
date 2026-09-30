import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


def _gather(user_id: int, cmd: str, action_emoji: str, action_verb: str, ctx):
    pass  # helper abaixo


class FishCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="fish", aliases=["pescar", "pesca"])
    async def fish(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("fish"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        user_id = ctx.author.id
        remaining = EconomyHelper.check_cooldown(user_id, "fish")
        if remaining > 0:
            await ctx.reply(f"🎣 Aguarde `{EconomyHelper.format_cooldown(remaining)}` para pescar novamente.")
            return

        cfg = EconomyHelper.get_economy_settings().get("fish", {})
        item = _roll_item(cfg.get("items", []), cfg.get("min_reward", 20), cfg.get("max_reward", 150))
        EconomyHelper.add_user_coins(user_id, item["reward"], reason="Pesca")
        EconomyHelper.set_cooldown(user_id, "fish")
        EconomyHelper.add_to_inventory(user_id, f"fish_{item['name'].lower().replace(' ','_')}")

        balance = EconomyHelper.get_user_coins(user_id)
        cur = EconomyHelper.get_currency_display()
        await ctx.reply(
            f"🎣 Você pescou um **{item['name']}** e vendeu por **{item['reward']:,}** {cur}!\n"
            f"-# Saldo atual: {balance:,}"
        )


class MineCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="mine", aliases=["minerar", "minar"])
    async def mine(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("mine"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        user_id = ctx.author.id
        remaining = EconomyHelper.check_cooldown(user_id, "mine")
        if remaining > 0:
            await ctx.reply(f"⛏️ Aguarde `{EconomyHelper.format_cooldown(remaining)}` para minerar novamente.")
            return

        cfg = EconomyHelper.get_economy_settings().get("mine", {})
        item = _roll_item(cfg.get("items", []), cfg.get("min_reward", 30), cfg.get("max_reward", 200))
        EconomyHelper.add_user_coins(user_id, item["reward"], reason="Mineração")
        EconomyHelper.set_cooldown(user_id, "mine")
        EconomyHelper.add_to_inventory(user_id, f"mine_{item['name'].lower().replace(' ','_')}")

        balance = EconomyHelper.get_user_coins(user_id)
        cur = EconomyHelper.get_currency_display()
        await ctx.reply(
            f"⛏️ Você minerou **{item['name']}** e vendeu por **{item['reward']:,}** {cur}!\n"
            f"-# Saldo atual: {balance:,}"
        )


class HuntCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="hunt", aliases=["cacar", "caçar", "caca"])
    async def hunt(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("hunt"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        user_id = ctx.author.id
        remaining = EconomyHelper.check_cooldown(user_id, "hunt")
        if remaining > 0:
            await ctx.reply(f"🏹 Aguarde `{EconomyHelper.format_cooldown(remaining)}` para caçar novamente.")
            return

        cfg = EconomyHelper.get_economy_settings().get("hunt", {})
        item = _roll_item(cfg.get("items", []), cfg.get("min_reward", 25), cfg.get("max_reward", 175))
        EconomyHelper.add_user_coins(user_id, item["reward"], reason="Caça")
        EconomyHelper.set_cooldown(user_id, "hunt")
        EconomyHelper.add_to_inventory(user_id, f"hunt_{item['name'].lower().replace(' ','_')}")

        balance = EconomyHelper.get_user_coins(user_id)
        cur = EconomyHelper.get_currency_display()
        await ctx.reply(
            f"🏹 Você caçou um **{item['name']}** e vendeu por **{item['reward']:,}** {cur}!\n"
            f"-# Saldo atual: {balance:,}"
        )


def _roll_item(items: list, fallback_min: int, fallback_max: int) -> dict:
    """Rola um item com base nas chances configuradas."""
    if not items:
        return {"name": "Item Genérico", "reward": random.randint(fallback_min, fallback_max)}

    roll = random.randint(1, 100)
    cumulative = 0
    for item in sorted(items, key=lambda x: x["chance"], reverse=True):
        cumulative += item["chance"]
        if roll <= cumulative:
            reward = random.randint(item["min"], item["max"])
            return {"name": item["name"], "reward": reward}

    # Fallback para o último item
    last = items[-1]
    return {"name": last["name"], "reward": random.randint(last["min"], last["max"])}


def setup(bot: commands.Bot):
    bot.add_cog(FishCommand(bot))
    bot.add_cog(MineCommand(bot))
    bot.add_cog(HuntCommand(bot))