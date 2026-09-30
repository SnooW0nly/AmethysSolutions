import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji
from datetime import datetime


TITLE_THRESHOLDS = [
    (100000, "👑 Magnata"),
    (50000,  "💎 Milionário"),
    (20000,  "🏆 Rico"),
    (10000,  "💰 Próspero"),
    (5000,   "📈 Investidor"),
    (1000,   "💵 Trabalhador"),
    (0,      "🌱 Iniciante"),
]

REP_TITLES = [
    (100, "🌟 Lendário"),
    (50,  "⭐ Famoso"),
    (20,  "✨ Conhecido"),
    (5,   "👍 Respeitado"),
    (0,   "😐 Desconhecido"),
]


def get_title(coins: int) -> str:
    for threshold, title in TITLE_THRESHOLDS:
        if coins >= threshold:
            return title
    return "🌱 Iniciante"


def get_rep_title(reps: int) -> str:
    for threshold, title in REP_TITLES:
        if reps >= threshold:
            return title
    return "😐 Desconhecido"


class ProfileCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="perfil", aliases=["profile", "me", "eu"])
    async def profile(self, ctx: commands.Context, member: disnake.Member = None):
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("profile"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        target = member or ctx.author
        cur = EconomyHelper.get_currency_display()
        cur_name = EconomyHelper.get_currency_name()

        coins = EconomyHelper.get_user_coins(target.id)
        bank = EconomyHelper.get_user_bank(target.id)
        total = coins + bank

        social = EconomyHelper.get_social_data(target.id)
        reps = social.get("reps", 0)
        partner_id = social.get("partner")
        parent_id = social.get("parent")
        children = social.get("children", [])

        title = get_title(total)
        rep_title = get_rep_title(reps)

        # Leaderboard position
        lb = EconomyHelper.get_leaderboard(9999)
        pos = next((i + 1 for i, (uid, _) in enumerate(lb) if uid == str(target.id)), None)
        pos_str = f"#{pos}" if pos else "—"

        # Job
        job = EconomyHelper.get_user_job(target.id)
        job_str = f"{job['emoji']} {job['name']}" if job else "😴 Desempregado"

        # Streaks
        daily_streak = EconomyHelper.get_streak(target.id, "daily").get("count", 0)
        work_streak = EconomyHelper.get_streak(target.id, "work").get("count", 0)

        # Inventory count
        inv = EconomyHelper.get_inventory(target.id)
        inv_count = sum(inv.values()) if inv else 0

        embed = disnake.Embed(
            title=f"{title} — {target.display_name}",
            color=0x2B2D31
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        # Finances
        embed.add_field(
            name="💰 Finanças",
            value=(
                f"**Em Mãos:** {coins:,} {cur_name}\n"
                f"**No Banco:** {bank:,} {cur_name}\n"
                f"**Total:** {total:,} {cur_name}\n"
                f"**Ranking:** {pos_str}"
            ),
            inline=True
        )

        # Social
        partner_str = "Solteiro(a) 💔"
        if partner_id:
            partner = ctx.guild.get_member(partner_id)
            partner_str = f"💍 {partner.display_name if partner else f'<@{partner_id}>'}"

        embed.add_field(
            name="👥 Social",
            value=(
                f"**Status:** {partner_str}\n"
                f"**Filhos:** {len(children)}\n"
                f"**Reputação:** ⭐ {reps} ({rep_title})\n"
                f"**Família:** {'Tem pais' if parent_id else 'Sem pais'}"
            ),
            inline=True
        )

        # Trabalho & Atividade
        embed.add_field(
            name="💼 Trabalho & Atividade",
            value=(
                f"**Emprego:** {job_str}\n"
                f"**Streak Daily:** 🔥 {daily_streak} dia(s)\n"
                f"**Streak Work:** ⚡ {work_streak} trabalho(s)\n"
                f"**Itens no Inv.:** 🎒 {inv_count}"
            ),
            inline=False
        )

        # Interações
        interactions = social.get("interactions", {})
        if interactions:
            inter_parts = []
            icons = {"beijar": "💋", "abracar": "🫂", "tapa": "🖐️", "cafune": "💆"}
            for k, v in interactions.items():
                ic = icons.get(k, "🤝")
                inter_parts.append(f"{ic} {v}x")
            embed.add_field(
                name="💕 Interações Totais",
                value=" | ".join(inter_parts[:6]),
                inline=False
            )

        embed.set_footer(text=f"ID: {target.id} • {datetime.now().strftime('%d/%m/%Y')}")
        await ctx.reply(embed=embed)

    @commands.command(name="stats", aliases=["estatisticas", "estatísticas"])
    async def stats(self, ctx: commands.Context, member: disnake.Member = None):
        """Estatísticas de jogo do usuário."""
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        target = member or ctx.author
        social = EconomyHelper.get_social_data(target.id)
        inv = EconomyHelper.get_inventory(target.id) or {}

        # Contar itens por categoria
        fish_count = sum(v for k, v in inv.items() if k.startswith("fish_"))
        mine_count = sum(v for k, v in inv.items() if k.startswith("mine_"))
        hunt_count = sum(v for k, v in inv.items() if k.startswith("hunt_"))

        embed = disnake.Embed(
            title=f"📊 Estatísticas de {target.display_name}",
            color=0x3498DB
        )

        interactions = social.get("interactions", {})
        total_interactions = sum(interactions.values())

        embed.add_field(
            name="🤝 Interações",
            value="\n".join([
                f"💋 Beijos: {interactions.get('beijar', 0)}",
                f"🫂 Abraços: {interactions.get('abracar', 0)}",
                f"🖐️ Tapas: {interactions.get('tapa', 0)}",
                f"💆 Cafunés: {interactions.get('cafune', 0)}",
                f"**Total: {total_interactions}**",
            ]),
            inline=True
        )

        embed.add_field(
            name="🎒 Coleção",
            value="\n".join([
                f"🐟 Peixes pescados: {fish_count}",
                f"💎 Minérios minerados: {mine_count}",
                f"🏹 Caças capturadas: {hunt_count}",
            ]),
            inline=True
        )

        bffs = social.get("bffs", {})
        embed.add_field(
            name="⭐ Social",
            value="\n".join([
                f"⭐ Reputação: {social.get('reps', 0)}",
                f"👫 BFFs registrados: {len(bffs)}",
                f"👶 Filhos: {len(social.get('children', []))}",
            ]),
            inline=False
        )

        await ctx.reply(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(ProfileCommand(bot))
