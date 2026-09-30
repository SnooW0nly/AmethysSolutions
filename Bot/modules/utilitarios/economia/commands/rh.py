import random
from disnake.ext import commands
import disnake
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji


class RHCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── rh (sem subcomando = ver emprego atual) ───────────────────────────────

    @commands.group(name="rh", aliases=["emprego", "trabalhos"], invoke_without_command=True)
    async def rh(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("work"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        job = EconomyHelper.get_user_job(ctx.author.id)
        cur_name = EconomyHelper.get_currency_name()

        if not job:
            await ctx.reply(
                f"💼 Você está **desempregado**.\n\n"
                f"Use `rh empregos` para ver as vagas disponíveis.\n"
                f"Use `rh candidatar <emprego>` para se candidatar."
            )
            return

        cd = EconomyHelper.check_cooldown(ctx.author.id, "work")
        cd_str = f"`{EconomyHelper.format_cooldown(cd)}`" if cd > 0 else "`Disponível agora`"

        await ctx.reply(
            f"## {job['emoji']} {job['name']}\n"
            f"{job['description']}\n\n"
            f"💰 **Salário:** `{job['min_pay']:,}`–`{job['max_pay']:,}` {cur_name}\n"
            f"🎲 **Chance de ser contratado:** `{job['accept_chance']}%`\n"
            f"⏱️ **Próximo trabalho:** {cd_str}\n\n"
            f"-# Use `rh empregos` para ver outras vagas. `rh candidatar <emprego>` para trocar."
        )

    # ── rh empregos ───────────────────────────────────────────────────────────

    @rh.command(name="empregos", aliases=["vagas", "lista", "jobs"])
    async def rh_empregos(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        all_jobs = EconomyHelper.get_all_jobs()
        cur_name = EconomyHelper.get_currency_name()
        cur_job  = EconomyHelper.get_user_job(ctx.author.id)
        cur_id   = cur_job["id"] if cur_job else None

        lines = [f"# 💼 Empregos Disponíveis\n"]
        for jid, job in sorted(all_jobs.items(), key=lambda x: x[1]["accept_chance"], reverse=True):
            tag = " ← **(atual)**" if jid == cur_id else ""
            lines.append(
                f"{job['emoji']} **{job['name']}**{tag}\n"
                f"-# {job['description']}\n"
                f"-# 💰 `{job['min_pay']:,}`–`{job['max_pay']:,}` {cur_name} · "
                f"🎲 `{job['accept_chance']}%` de chance\n"
                f"-# `rh candidatar {jid}`"
            )

        await ctx.reply("\n\n".join(lines))

    # ── rh candidatar <emprego> ───────────────────────────────────────────────

    @rh.command(name="candidatar", aliases=["aplicar", "apply", "contratar"])
    async def rh_candidatar(self, ctx: commands.Context, emprego: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("work"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if not emprego:
            await ctx.reply(
                f"{emoji.wrong} Informe o emprego: `rh candidatar <id_do_emprego>`\n"
                f"Use `rh empregos` para ver os IDs disponíveis."
            )
            return

        emprego = emprego.lower().strip()
        job = EconomyHelper.get_job(emprego)
        if not job:
            await ctx.reply(
                f"{emoji.wrong} Emprego `{emprego}` não encontrado.\n"
                f"Use `rh empregos` para ver as opções disponíveis."
            )
            return

        current = EconomyHelper.get_user_job(ctx.author.id)
        if current and current["id"] == emprego:
            await ctx.reply(f"{emoji.wrong} Você já trabalha como **{job['emoji']} {job['name']}**!")
            return

        # Rolar a chance de contratação
        roll = random.randint(1, 100)
        if roll <= job["accept_chance"]:
            # Contratado!
            old_job = current
            EconomyHelper.set_user_job(ctx.author.id, emprego)

            if old_job:
                demissao = f"\n-# Você saiu de **{old_job['emoji']} {old_job['name']}** para assumir a nova vaga."
            else:
                demissao = ""

            await ctx.reply(
                f"🎉 **Parabéns! Você foi contratado como {job['emoji']} {job['name']}!**\n"
                f"{job['description']}\n\n"
                f"💰 Salário: `{job['min_pay']:,}`–`{job['max_pay']:,}` {EconomyHelper.get_currency_name()}{demissao}"
            )
        else:
            # Rejeitado
            rejections = [
                "Você não passou na entrevista.",
                "O RH disse que vai te ligar... (vai não).",
                "A vaga foi preenchida por outro candidato.",
                "Você não tinha experiência suficiente.",
                "O gerente não gostou do seu currículo.",
            ]
            await ctx.reply(
                f"😔 **Candidatura para {job['emoji']} {job['name']} rejeitada.**\n"
                f"{random.choice(rejections)}\n"
                f"-# Chance era `{job['accept_chance']}%`. Tente novamente mais tarde!"
            )

    # ── rh demitir ────────────────────────────────────────────────────────────

    @rh.command(name="demitir", aliases=["sair", "quit", "resign"])
    async def rh_demitir(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        job = EconomyHelper.get_user_job(ctx.author.id)
        if not job:
            await ctx.reply(f"{emoji.wrong} Você já está desempregado.")
            return

        EconomyHelper.remove_user_job(ctx.author.id)
        await ctx.reply(
            f"👋 Você pediu demissão de **{job['emoji']} {job['name']}**.\n"
            f"-# Use `rh candidatar <emprego>` para conseguir um novo emprego."
        )

    # ── rh info <emprego> ─────────────────────────────────────────────────────

    @rh.command(name="info", aliases=["detalhes", "ver"])
    async def rh_info(self, ctx: commands.Context, emprego: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if not emprego:
            await ctx.reply(f"{emoji.wrong} Use: `rh info <id_do_emprego>`")
            return

        job = EconomyHelper.get_job(emprego.lower())
        if not job:
            await ctx.reply(f"{emoji.wrong} Emprego `{emprego}` não encontrado.")
            return

        cur_name  = EconomyHelper.get_currency_name()
        cur_job   = EconomyHelper.get_user_job(ctx.author.id)
        tag = " ← **(seu emprego atual)**" if cur_job and cur_job["id"] == emprego else ""

        await ctx.reply(
            f"## {job['emoji']} {job['name']}{tag}\n"
            f"{job['description']}\n\n"
            f"💰 **Faixa salarial:** `{job['min_pay']:,}`–`{job['max_pay']:,}` {cur_name}\n"
            f"🎲 **Chance de ser contratado:** `{job['accept_chance']}%`\n\n"
            f"-# Para se candidatar: `rh candidatar {emprego}`"
        )


def setup(bot: commands.Bot):
    bot.add_cog(RHCommand(bot))