import random
import disnake
from disnake.ext import commands
from ..helper import EconomyHelper
from ..guard import EconomyGuard
from functions.emoji import emoji

ADVENTURES = [
    {
        "name": "Floresta Sombria",
        "emoji": "🌲",
        "events": [
            {"desc": "Você encontrou um baú escondido entre as árvores!", "type": "treasure", "reward_mult": 1.5},
            {"desc": "Um goblin te ataca! Você conseguiu fugir, mas perdeu alguns itens.", "type": "loss", "loss_mult": 0.3},
            {"desc": "Você encontrou um vilarejo e ajudou os moradores. Eles recompensaram você.", "type": "reward", "reward_mult": 1.0},
            {"desc": "Você se perdeu na floresta e voltou sem nada.", "type": "nothing"},
            {"desc": "Um dragão adormecido! Você roubou uma gema do seu tesouro.", "type": "treasure", "reward_mult": 2.0},
            {"desc": "Uma armadilha! Você caiu em um buraco e perdeu moedas.", "type": "loss", "loss_mult": 0.2},
        ]
    },
    {
        "name": "Ruínas Antigas",
        "emoji": "🏛️",
        "events": [
            {"desc": "Você decifrou um enigma e abriu um cofre milenar!", "type": "treasure", "reward_mult": 2.0},
            {"desc": "Uma maldição antiga! Suas moedas se transformam em pó por um instante.", "type": "loss", "loss_mult": 0.4},
            {"desc": "Você encontrou um artefato valioso e vendeu por bom preço.", "type": "reward", "reward_mult": 1.2},
            {"desc": "As ruínas estavam vazias. Você voltou para casa.", "type": "nothing"},
            {"desc": "Um cultista generoso te deu suas economias antes de fugir!", "type": "treasure", "reward_mult": 1.8},
        ]
    },
    {
        "name": "Mar Profundo",
        "emoji": "🌊",
        "events": [
            {"desc": "Você mergulhou e encontrou um naufrágio repleto de ouro!", "type": "treasure", "reward_mult": 2.5},
            {"desc": "Uma tempestade! Você jogou moedas ao mar para acalmar as águas.", "type": "loss", "loss_mult": 0.35},
            {"desc": "Uma sereia te presenteou com pérolas raras.", "type": "reward", "reward_mult": 1.3},
            {"desc": "O mar estava calmo e não havia nada para explorar.", "type": "nothing"},
            {"desc": "Piratas! Você lutou e tomou o tesouro deles.", "type": "treasure", "reward_mult": 1.7},
        ]
    },
    {
        "name": "Montanha Gelada",
        "emoji": "🏔️",
        "events": [
            {"desc": "Você escalou até o topo e encontrou o covil de um gigante!", "type": "treasure", "reward_mult": 2.2},
            {"desc": "Avalanche! Você correu mas perdeu sua mochila cheia de moedas.", "type": "loss", "loss_mult": 0.4},
            {"desc": "Um eremita sábio te ensinou segredos de investimento.", "type": "reward", "reward_mult": 1.1},
            {"desc": "A montanha era apenas pedra e neve. Nada de especial.", "type": "nothing"},
            {"desc": "Uma fênix caída! Você a curou e ela te presenteou com ouro.", "type": "treasure", "reward_mult": 2.0},
        ]
    },
]


class AdventureCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="aventura", aliases=["adventure", "explorar", "quest"])
    async def adventure(self, ctx: commands.Context, bet: str = None):
        """
        Embarque em uma aventura e arrisque seus coins!
        `aventura <aposta>` — aposte para ganhar mais
        `aventura` — aventura gratuita (sem recompensa em coins)
        """
        if not EconomyHelper.is_economy_enabled():
            return
        if not EconomyHelper.get_command_status("adventure"):
            return
        allowed, reason = EconomyGuard.check(ctx)
        if not allowed:
            await ctx.reply(reason, delete_after=6)
            return

        cfg = EconomyHelper.get_economy_settings().get("adventure", {"min_bet": 50, "max_bet": 2000})
        cur = EconomyHelper.get_currency_display()

        location = random.choice(ADVENTURES)
        event = random.choice(location["events"])

        # Aventura gratuita
        if bet is None:
            embed = disnake.Embed(
                title=f"{location['emoji']} Aventura em {location['name']}",
                description=event["desc"],
                color=0x8B4513
            )
            if event["type"] == "nothing":
                embed.add_field(name="📦 Resultado", value="Você voltou com as mãos vazias.", inline=False)
            elif event["type"] == "loss":
                embed.add_field(name="📦 Resultado", value="Você escapou sem perder nada (aventura gratuita).", inline=False)
            else:
                embed.add_field(name="📦 Resultado", value="Que aventura incrível! Mas sem aposta, sem recompensa.", inline=False)
            embed.set_footer(text=f"Dica: use `aventura <aposta>` para ganhar coins!")
            await ctx.reply(embed=embed)
            return

        # Aventura com aposta
        try:
            bet_int = int(bet.replace(",", "").replace(".", ""))
            if bet_int <= 0:
                raise ValueError
        except ValueError:
            await ctx.reply(f"{emoji.wrong} Aposta inválida.")
            return

        min_bet = cfg.get("min_bet", 50)
        max_bet = cfg.get("max_bet", 2000)
        if bet_int < min_bet or bet_int > max_bet:
            await ctx.reply(f"{emoji.wrong} Aposta entre `{min_bet:,}` e `{max_bet:,}`.")
            return

        user_coins = EconomyHelper.get_user_coins(ctx.author.id)
        if user_coins < bet_int:
            await ctx.reply(f"{emoji.wrong} Saldo insuficiente. Você tem `{user_coins:,}`.")
            return

        embed = disnake.Embed(
            title=f"{location['emoji']} Aventura em {location['name']}",
            description=event["desc"],
            color=0x8B4513
        )

        if event["type"] == "treasure":
            mult = event.get("reward_mult", 1.5)
            reward = int(bet_int * mult)
            EconomyHelper.add_user_coins(ctx.author.id, reward)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            embed.color = 0xFFD700
            embed.add_field(name="💰 Resultado", value=f"**+{reward:,}** {cur} (`{mult}x`!)", inline=False)
            embed.add_field(name="📊 Saldo", value=f"`{balance:,}`", inline=True)

        elif event["type"] == "reward":
            mult = event.get("reward_mult", 1.0)
            reward = int(bet_int * (mult + 0.3))
            EconomyHelper.add_user_coins(ctx.author.id, reward)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            embed.color = 0x2ECC71
            embed.add_field(name="💰 Resultado", value=f"**+{reward:,}** {cur}", inline=False)
            embed.add_field(name="📊 Saldo", value=f"`{balance:,}`", inline=True)

        elif event["type"] == "loss":
            mult = event.get("loss_mult", 0.3)
            loss = int(bet_int * mult)
            EconomyHelper.remove_user_coins(ctx.author.id, loss)
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            embed.color = 0xFF4500
            embed.add_field(name="💸 Resultado", value=f"**-{loss:,}** {cur}", inline=False)
            embed.add_field(name="📊 Saldo", value=f"`{balance:,}`", inline=True)

        else:  # nothing
            balance = EconomyHelper.get_user_coins(ctx.author.id)
            embed.add_field(name="📦 Resultado", value=f"Aposta de `{bet_int:,}` devolvida (sem eventos).", inline=False)
            embed.add_field(name="📊 Saldo", value=f"`{balance:,}`", inline=True)

        await ctx.reply(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(AdventureCommand(bot))
