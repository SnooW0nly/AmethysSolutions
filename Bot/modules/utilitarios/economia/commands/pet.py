import random
import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji
from functions.database import database as db
from datetime import datetime, timedelta

PET_DB = "database/utilitarios/economia/pets.json"

PET_TYPES = {
    "gato":      {"emoji": "🐱", "price": 500,  "base_income": 10,  "description": "Independente e carinhoso."},
    "cachorro":  {"emoji": "🐶", "price": 500,  "base_income": 12,  "description": "Fiel e energético."},
    "coelho":    {"emoji": "🐰", "price": 400,  "base_income": 8,   "description": "Fofo e curioso."},
    "hamster":   {"emoji": "🐹", "price": 300,  "base_income": 6,   "description": "Pequeno mas travesso."},
    "papagaio":  {"emoji": "🦜", "price": 800,  "base_income": 18,  "description": "Inteligente e falador."},
    "dragao":    {"emoji": "🐲", "price": 5000, "base_income": 100, "description": "Lendário e poderoso!"},
}

MOODS = ["😊 Feliz", "😐 Normal", "😴 Sonolento", "😢 Triste", "😡 Com Fome", "🤒 Doente"]


def get_pet_data(user_id: int) -> dict | None:
    data = db.obter(PET_DB)
    return data.get(str(user_id))


def save_pet_data(user_id: int, pet: dict):
    data = db.obter(PET_DB)
    data[str(user_id)] = pet
    db.salvar(PET_DB, data)


def get_pet_mood(pet: dict) -> str:
    hunger = pet.get("hunger", 100)
    happiness = pet.get("happiness", 100)
    health = pet.get("health", 100)
    if health < 30:
        return "🤒 Doente"
    if hunger < 20:
        return "😡 Com Fome"
    if happiness < 30:
        return "😢 Triste"
    if happiness < 60:
        return "😐 Normal"
    if happiness >= 80:
        return "😊 Feliz"
    return "😴 Sonolento"


def decay_stats(pet: dict) -> dict:
    """Reduz stats baseado no tempo decorrido."""
    last = pet.get("last_interaction")
    if not last:
        return pet
    try:
        last_dt = datetime.fromisoformat(last)
        hours_passed = (datetime.now() - last_dt).total_seconds() / 3600
        decay = min(50, int(hours_passed * 3))
        pet["hunger"] = max(0, pet.get("hunger", 100) - decay)
        pet["happiness"] = max(0, pet.get("happiness", 100) - int(decay * 0.5))
        if pet["hunger"] < 10:
            pet["health"] = max(0, pet.get("health", 100) - int(decay * 0.3))
    except Exception:
        pass
    return pet


class PetCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="pet", aliases=["mascote", "bicho"], invoke_without_subcommand=True)
    async def pet(self, ctx: commands.Context):
        """Gerencia seu pet virtual."""
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        pet = get_pet_data(ctx.author.id)
        if not pet:
            lines = ["# 🐾 Adote um Pet!\n", f"Use `pet adotar <tipo>` para adotar um pet.\n"]
            for pid, info in PET_TYPES.items():
                lines.append(
                    f"{info['emoji']} **{pid.title()}** — `{info['price']:,}` {EconomyHelper.get_currency_name()}\n"
                    f"-# {info['description']} | Renda base: `+{info['base_income']}`/hora"
                )
            await ctx.reply("\n".join(lines))
            return

        pet = decay_stats(pet)
        save_pet_data(ctx.author.id, pet)

        pet_type = PET_TYPES.get(pet["type"], {})
        mood = get_pet_mood(pet)

        embed = disnake.Embed(
            title=f"{pet_type.get('emoji','🐾')} {pet.get('name', 'Sem Nome')}",
            color=0x2B2D31
        )
        embed.add_field(name="😊 Humor", value=mood, inline=True)
        embed.add_field(name="🍖 Fome", value=f"{pet.get('hunger', 100)}/100", inline=True)
        embed.add_field(name="💖 Felicidade", value=f"{pet.get('happiness', 100)}/100", inline=True)
        embed.add_field(name="❤️ Saúde", value=f"{pet.get('health', 100)}/100", inline=True)
        embed.add_field(name="⭐ Nível", value=f"{pet.get('level', 1)}", inline=True)
        embed.add_field(name="🎂 Idade", value=f"{pet.get('age_days', 0)} dias", inline=True)
        embed.set_footer(text="Use: pet alimentar | pet brincar | pet curar | pet coletar")
        await ctx.reply(embed=embed)

    @pet.command(name="adotar", aliases=["adopt", "comprar"])
    async def pet_adopt(self, ctx: commands.Context, pet_type: str = None, *, name: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        if get_pet_data(ctx.author.id):
            await ctx.reply(f"{emoji.wrong} Você já tem um pet! Use `pet` para ver suas informações.")
            return

        if pet_type is None:
            await ctx.reply(f"{emoji.wrong} Use: `pet adotar <tipo> [nome]`\nTipos: {', '.join(PET_TYPES.keys())}")
            return

        pet_type = pet_type.lower()
        if pet_type not in PET_TYPES:
            await ctx.reply(f"{emoji.wrong} Tipo inválido. Tipos disponíveis: {', '.join(PET_TYPES.keys())}")
            return

        info = PET_TYPES[pet_type]
        user_coins = EconomyHelper.get_user_coins(ctx.author.id)
        if user_coins < info["price"]:
            await ctx.reply(f"{emoji.wrong} Você precisa de `{info['price']:,}` {EconomyHelper.get_currency_name()} para adotar esse pet.")
            return

        EconomyHelper.remove_user_coins(ctx.author.id, info["price"], reason=f"Adoção de pet: {pet_type}")

        pet_name = (name or pet_type.title())[:20]
        pet = {
            "type": pet_type,
            "name": pet_name,
            "hunger": 100,
            "happiness": 100,
            "health": 100,
            "level": 1,
            "xp": 0,
            "age_days": 0,
            "last_interaction": datetime.now().isoformat(),
            "last_collect": datetime.now().isoformat(),
            "adopted_at": datetime.now().isoformat(),
        }
        save_pet_data(ctx.author.id, pet)

        await ctx.reply(
            f"{info['emoji']} **Parabéns! Você adotou um {pet_type}!**\n"
            f"Nome: **{pet_name}**\n"
            f"-# Cuide bem do seu pet! Use `pet alimentar`, `pet brincar` para mantê-lo feliz."
        )

    @pet.command(name="alimentar", aliases=["feed", "comida"])
    async def pet_feed(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        pet = get_pet_data(ctx.author.id)
        if not pet:
            await ctx.reply(f"{emoji.wrong} Você não tem um pet! Use `pet adotar` para adotar um.")
            return

        pet = decay_stats(pet)
        feed_cost = 50
        if EconomyHelper.get_user_coins(ctx.author.id) < feed_cost:
            await ctx.reply(f"{emoji.wrong} Precisa de `{feed_cost}` coins para alimentar o pet.")
            return

        EconomyHelper.remove_user_coins(ctx.author.id, feed_cost, reason="Alimentar pet")
        gain = random.randint(20, 40)
        pet["hunger"] = min(100, pet.get("hunger", 0) + gain)
        pet["xp"] = pet.get("xp", 0) + 5
        pet["last_interaction"] = datetime.now().isoformat()
        _check_level_up(pet)
        save_pet_data(ctx.author.id, pet)

        pet_type = PET_TYPES.get(pet["type"], {})
        await ctx.reply(
            f"{pet_type.get('emoji','🐾')} **{pet['name']}** comeu e está satisfeito!\n"
            f"🍖 Fome: {pet['hunger']}/100 (+{gain})\n"
            f"-# Custou {feed_cost} coins"
        )

    @pet.command(name="brincar", aliases=["play", "jogar"])
    async def pet_play(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        pet = get_pet_data(ctx.author.id)
        if not pet:
            await ctx.reply(f"{emoji.wrong} Você não tem um pet!")
            return

        pet = decay_stats(pet)
        play_msgs = ["brincou com uma bolinha", "correu pelo quintal", "fez uma caminhada", "jogou frisbee", "dormiu no seu colo"]
        gain = random.randint(15, 35)
        pet["happiness"] = min(100, pet.get("happiness", 0) + gain)
        pet["xp"] = pet.get("xp", 0) + 8
        pet["last_interaction"] = datetime.now().isoformat()
        _check_level_up(pet)
        save_pet_data(ctx.author.id, pet)

        msg = random.choice(play_msgs)
        pet_type = PET_TYPES.get(pet["type"], {})
        await ctx.reply(
            f"{pet_type.get('emoji','🐾')} **{pet['name']}** {msg}!\n"
            f"💖 Felicidade: {pet['happiness']}/100 (+{gain})"
        )

    @pet.command(name="coletar", aliases=["collect", "renda"])
    async def pet_collect(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        pet = get_pet_data(ctx.author.id)
        if not pet:
            await ctx.reply(f"{emoji.wrong} Você não tem um pet!")
            return

        pet = decay_stats(pet)
        last_collect = pet.get("last_collect")
        now = datetime.now()

        if last_collect:
            last_dt = datetime.fromisoformat(last_collect)
            hours = (now - last_dt).total_seconds() / 3600
            if hours < 1:
                minutes = int((1 - hours) * 60)
                await ctx.reply(f"{emoji.wrong} Aguarde **{minutes}min** para coletar novamente.")
                save_pet_data(ctx.author.id, pet)
                return
            hours = min(hours, 24)  # máx 24h acumulado
        else:
            hours = 1

        info = PET_TYPES.get(pet["type"], {"base_income": 10})
        level_mult = 1 + (pet.get("level", 1) - 1) * 0.1
        mood = get_pet_mood(pet)
        mood_mult = 1.5 if "Feliz" in mood else (0.5 if "Triste" in mood or "Com Fome" in mood else 1.0)

        earned = int(info["base_income"] * hours * level_mult * mood_mult)
        EconomyHelper.add_user_coins(ctx.author.id, earned, reason=f"Renda do pet {pet['name']}")
        pet["last_collect"] = now.isoformat()
        save_pet_data(ctx.author.id, pet)

        cur = EconomyHelper.get_currency_display()
        balance = EconomyHelper.get_user_coins(ctx.author.id)
        pet_type = PET_TYPES.get(pet["type"], {})
        await ctx.reply(
            f"{pet_type.get('emoji','🐾')} **{pet['name']}** trabalhou por `{hours:.1f}h`!\n"
            f"💰 **+{earned:,}** {cur} coletado!\n"
            f"-# Humor: {mood} | Saldo atual: {balance:,}"
        )

    @pet.command(name="renomear", aliases=["rename", "nome"])
    async def pet_rename(self, ctx: commands.Context, *, new_name: str = None):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        pet = get_pet_data(ctx.author.id)
        if not pet:
            await ctx.reply(f"{emoji.wrong} Você não tem um pet!")
            return
        if not new_name:
            await ctx.reply(f"{emoji.wrong} Use: `pet renomear <nome>`")
            return
        old_name = pet["name"]
        pet["name"] = new_name[:20]
        save_pet_data(ctx.author.id, pet)
        await ctx.reply(f"✅ Pet renomeado de **{old_name}** para **{pet['name']}**!")

    @pet.command(name="largar", aliases=["release", "abandonar"])
    async def pet_release(self, ctx: commands.Context):
        if not EconomyHelper.is_economy_enabled():
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return
        pet = get_pet_data(ctx.author.id)
        if not pet:
            await ctx.reply(f"{emoji.wrong} Você não tem um pet!")
            return

        pet_type = PET_TYPES.get(pet["type"], {})
        await ctx.reply(
            f"{emoji.wrong} Tem certeza que quer largar **{pet_type.get('emoji','')} {pet['name']}**?\n"
            f"Digite `sim` em 15s para confirmar."
        )

        def check(m):
            return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id and m.content.lower() in ["sim", "yes"]

        try:
            await ctx.bot.wait_for("message", check=check, timeout=15.0)
            data = db.obter(PET_DB)
            if str(ctx.author.id) in data:
                del data[str(ctx.author.id)]
                db.salvar(PET_DB, data)
            await ctx.reply(f"💔 Você soltou **{pet['name']}** em liberdade. Que triste...")
        except Exception:
            await ctx.reply("Ação cancelada.")


def _check_level_up(pet: dict):
    xp = pet.get("xp", 0)
    level = pet.get("level", 1)
    xp_needed = level * 100
    if xp >= xp_needed:
        pet["level"] = level + 1
        pet["xp"] = xp - xp_needed


def setup(bot: commands.Bot):
    bot.add_cog(PetCommand(bot))
