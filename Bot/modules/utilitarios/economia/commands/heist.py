import random
import asyncio
from disnake.ext import commands
import disnake
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji
from functions.database import database as db

HEIST_DB = "database/utilitarios/economia/heist.json"

HEIST_TARGETS = [
    {"name": "Banco Central",       "emoji": "🏦", "min_reward": 2000,  "max_reward": 8000,  "success_chance": 30, "min_players": 3},
    {"name": "Joalheria Royal",     "emoji": "💍", "min_reward": 1000,  "max_reward": 4000,  "success_chance": 45, "min_players": 2},
    {"name": "Cassino Las Vegas",   "emoji": "🎰", "min_reward": 1500,  "max_reward": 6000,  "success_chance": 35, "min_players": 2},
    {"name": "Museu Nacional",      "emoji": "🏛️", "min_reward": 800,   "max_reward": 3000,  "success_chance": 55, "min_players": 2},
    {"name": "Cofre do Prefeito",   "emoji": "🏛️", "min_reward": 500,   "max_reward": 2000,  "success_chance": 65, "min_players": 1},
    {"name": "Conveniência 24h",    "emoji": "🏪", "min_reward": 200,   "max_reward": 600,   "success_chance": 80, "min_players": 1},
]

HEIST_ROLES = ["🔫 Atirador", "🧰 Arrombador", "🚗 Motorista", "💻 Hacker", "🎭 Disfarçado", "🗺️ Estrategista"]


class HeistCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_heists = {}  # channel_id -> heist data

    @commands.command(name="heist", aliases=["assalto", "roubo_grupo"])
    async def heist(self, ctx: commands.Context, target_name: str = None):
        """
        Organiza um assalto em grupo!
        `heist` — ver alvos disponíveis
        `heist <número>` — iniciar assalto
        `heist join` — entrar em assalto ativo
        `heist start` — iniciar o assalto (organizador)
        """
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("heist"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cur = EconomyHelper.get_currency_display()

        # Mostrar alvos
        if target_name is None:
            lines = ["# 🦹 Assaltos Disponíveis\n"]
            for i, t in enumerate(HEIST_TARGETS, 1):
                lines.append(
                    f"{t['emoji']} **{i}. {t['name']}**\n"
                    f"-# 💰 `{t['min_reward']:,}`–`{t['max_reward']:,}` {EconomyHelper.get_currency_name()} | "
                    f"🎲 `{t['success_chance']}%` | 👥 mín. `{t['min_players']}` jogadores\n"
                    f"-# `heist {i}` para organizar"
                )
            await ctx.reply("\n".join(lines))
            return

        # Entrar em assalto ativo
        if target_name.lower() == "join":
            heist = self.active_heists.get(ctx.channel.id)
            if not heist:
                await ctx.reply(f"{emoji.wrong} Não há assalto ativo neste canal. Use `heist <número>` para criar.")
                return
            if ctx.author.id in heist["members"]:
                await ctx.reply(f"{emoji.wrong} Você já está no assalto!")
                return
            if len(heist["members"]) >= 6:
                await ctx.reply(f"{emoji.wrong} O assalto está cheio (máx. 6).")
                return
            heist["members"][ctx.author.id] = random.choice(HEIST_ROLES)
            role = heist["members"][ctx.author.id]
            await ctx.reply(
                f"✅ **{ctx.author.display_name}** entrou no assalto como **{role}**!\n"
                f"👥 Membros: {len(heist['members'])}/{heist['target']['min_players']}+"
            )
            return

        # Iniciar o assalto
        if target_name.lower() == "start":
            heist = self.active_heists.get(ctx.channel.id)
            if not heist:
                await ctx.reply(f"{emoji.wrong} Nenhum assalto ativo para iniciar.")
                return
            if heist["organizer"] != ctx.author.id:
                await ctx.reply(f"{emoji.wrong} Só o organizador pode iniciar o assalto.")
                return
            if len(heist["members"]) < heist["target"]["min_players"]:
                await ctx.reply(
                    f"{emoji.wrong} Precisam de pelo menos **{heist['target']['min_players']}** membros. "
                    f"Atual: {len(heist['members'])}"
                )
                return
            await self._execute_heist(ctx, heist)
            return

        # Criar novo assalto
        if ctx.channel.id in self.active_heists:
            await ctx.reply(f"{emoji.wrong} Já há um assalto ativo neste canal! Use `heist join` para entrar.")
            return

        try:
            idx = int(target_name) - 1
            if not 0 <= idx < len(HEIST_TARGETS):
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Número inválido. Use `heist` para ver os alvos disponíveis.")
            return

        target = HEIST_TARGETS[idx]
        role = random.choice(HEIST_ROLES)

        heist = {
            "target": target,
            "organizer": ctx.author.id,
            "members": {ctx.author.id: role},
            "channel": ctx.channel.id,
        }
        self.active_heists[ctx.channel.id] = heist

        embed = disnake.Embed(
            title=f"🦹 Assalto ao {target['emoji']} {target['name']}",
            description=(
                f"**{ctx.author.display_name}** está organizando um assalto!\n\n"
                f"💰 Recompensa: `{target['min_reward']:,}`–`{target['max_reward']:,}` {EconomyHelper.get_currency_name()}\n"
                f"🎲 Chance de sucesso: `{target['success_chance']}%`\n"
                f"👥 Mínimo de jogadores: `{target['min_players']}`\n\n"
                f"Use `heist join` para entrar!\n"
                f"Use `heist start` para iniciar (organizador)."
            ),
            color=0x8B0000
        )
        embed.add_field(name="👥 Time atual", value=f"• {ctx.author.display_name} — {role}", inline=False)
        await ctx.reply(embed=embed)

        # Auto-cancelar após 5 minutos
        await asyncio.sleep(300)
        if ctx.channel.id in self.active_heists:
            del self.active_heists[ctx.channel.id]
            try:
                await ctx.send(f"⏰ O assalto ao **{target['name']}** foi cancelado por inatividade.")
            except Exception:
                pass

    async def _execute_heist(self, ctx, heist):
        del self.active_heists[ctx.channel.id]
        target = heist["target"]
        members = heist["members"]
        cur = EconomyHelper.get_currency_display()
        cur_name = EconomyHelper.get_currency_name()

        # Calcular chance baseada no número de membros
        bonus = min(20, (len(members) - 1) * 5)
        final_chance = min(95, target["success_chance"] + bonus)

        await ctx.send(
            f"🚨 **ASSALTO INICIADO!** {target['emoji']} {target['name']}\n"
            f"👥 Time de {len(members)} membros | Chance: `{final_chance}%`\n"
            f"⏳ Calculando resultado..."
        )
        await asyncio.sleep(3)

        roll = random.randint(1, 100)

        if roll <= final_chance:
            # Sucesso
            total = random.randint(target["min_reward"], target["max_reward"])
            # Bônus por mais membros
            total = int(total * (1 + (len(members) - 1) * 0.1))
            share = total // len(members)

            result_lines = [f"🎉 **ASSALTO BEM-SUCEDIDO!** {target['emoji']} {target['name']}\n"]
            result_lines.append(f"💰 **Total roubado:** `{total:,}` {cur_name}\n")
            result_lines.append(f"**Distribuição ({share:,} cada):**")

            for uid, role in members.items():
                EconomyHelper.add_user_coins(uid, share, reason=f"Assalto: {target['name']}")
                member = ctx.guild.get_member(uid)
                name = member.display_name if member else f"<@{uid}>"
                result_lines.append(f"• {role} — {name}: +**{share:,}** {cur_name}")

            await ctx.send("\n".join(result_lines))
        else:
            # Falha
            result_lines = [f"🚔 **ASSALTO FRACASSADO!** {target['emoji']} {target['name']}\n"]
            result_lines.append("A polícia chegou e o time foi preso! Todos pagaram fiança:\n")
            fine = random.randint(100, 400)

            for uid, role in members.items():
                EconomyHelper.remove_user_coins(uid, fine, reason=f"Preso no assalto: {target['name']}")
                member = ctx.guild.get_member(uid)
                name = member.display_name if member else f"<@{uid}>"
                result_lines.append(f"• {role} — {name}: -**{fine:,}** {cur_name}")

            await ctx.send("\n".join(result_lines))


def setup(bot: commands.Bot):
    bot.add_cog(HeistCommand(bot))
