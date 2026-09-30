from disnake.ext import commands

PROTECTION_MONITORS = [
    "tasks.protection.mon_persistencia_canais",
    "tasks.protection.mon_priv_apps",
    "tasks.protection.mon_priv_canais",
    "tasks.protection.mon_priv_cargos",
    "tasks.protection.mon_priv_mencoes",
    "tasks.protection.mon_priv_perms",
    "tasks.protection.mon_priv_urls",
    "tasks.protection.mon_prot_banimentos",
    "tasks.protection.mon_prot_cargos",
    "tasks.protection.mon_prot_comandos_ext",
    "tasks.protection.mon_prot_expulsoes",
    "tasks.protection.mon_prot_webhooks",
    "tasks.protection.mon_prot_comandos_canais",
    "tasks.protection.mon_prot_url",
    "tasks.protection.mon_prot_incident_actions",
    #"tasks.protection.mon_prot_imagens_mrbeast",
]

class ProtectionTasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        for monitor in PROTECTION_MONITORS:
            try:
                self.bot.load_extension(monitor)
            except Exception as e:
                print(f"Falha ao carregar o monitor de proteção '{monitor}': {e}")

def setup(bot: commands.Bot):
    bot.add_cog(ProtectionTasksCog(bot))
