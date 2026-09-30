import random
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class WorkCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="work", aliases=["trabalhar", "trabalho"])
    async def work(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("work"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        user_id = ctx.author.id
        remaining = EconomyHelper.check_cooldown(user_id, "work")
        if remaining > 0:
            await ctx.reply(
                f"{emoji.wrong} Você já trabalhou recentemente! "
                f"Descanse por `{EconomyHelper.format_cooldown(remaining)}`."
            )
            return

        cfg = EconomyHelper.get_economy_settings().get("work", {})
        use_jobs = cfg.get("use_jobs", True)
        cur = EconomyHelper.get_currency_display()

        if use_jobs:
            job = EconomyHelper.get_user_job(user_id)
            if not job:
                await ctx.reply(
                    f"{emoji.wrong} Você está **desempregado**!\n"
                    f"Use `rh empregos` para ver as vagas disponíveis e `rh candidatar <emprego>` para se candidatar."
                )
                return

            # Verificar cooldown
            EconomyHelper.set_cooldown(user_id, "work")

            # Calcular salário com base no emprego
            reward_raw = random.randint(job["min_pay"], job["max_pay"])
            reward = EconomyHelper.add_user_coins(user_id, reward_raw, reason=f"Trabalho: {job['name']}", member=ctx.author)

            # Detectar multiplicador efetivo para mostrar ao usuário
            mult = EconomyHelper.get_effective_multiplier(user_id, ctx.author, target="work")
            mult_line = f"\n-# 📈 Multiplicador: `{mult}x`" if mult != 1.0 else ""

            # Verificar evento ativo
            ev_mult = EconomyHelper.get_active_event_multiplier("work")
            event_line = f"\n-# 🎉 Evento ativo: `{ev_mult}x` em trabalho!" if ev_mult != 1.0 else ""

            balance = EconomyHelper.get_user_coins(user_id)
            await ctx.reply(
                f"{job['emoji']} **{job['name']}**\n"
                f"Você trabalhou e recebeu **{reward:,}** {cur}!{mult_line}{event_line}\n"
                f"-# Saldo atual: {balance:,}"
            )
        else:
            # Modo legado: mensagens genéricas sem emprego
            messages = [
                "Você trabalhou como programador",
                "Você fez entregas pelo bairro",
                "Você vendeu coisas na feira",
                "Você lavou carros na rua",
                "Você deu aulas particulares",
                "Você trabalhou num restaurante",
            ]
            min_r = cfg.get("min_reward", 50)
            max_r = cfg.get("max_reward", 200)
            reward_raw = random.randint(min_r, max_r)
            reward = EconomyHelper.add_user_coins(user_id, reward_raw, reason="Trabalho", member=ctx.author)
            job_msg = random.choice(messages)
            EconomyHelper.set_cooldown(user_id, "work")
            balance = EconomyHelper.get_user_coins(user_id)
            await ctx.reply(
                f"💼 **{job_msg}** e ganhou **{reward:,}** {cur}!\n"
                f"-# Saldo atual: {balance:,}"
            )


def setup(bot: commands.Bot):
    bot.add_cog(WorkCommand(bot))