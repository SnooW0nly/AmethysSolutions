import disnake
from disnake.ext import commands
import json

from functions.message import message
from functions.perms import perms
from functions.database import database
from functions.server_check import exclude_from_check


class BackupCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.owner_id = self._load_owner_id()  # Carrega só uma vez

    def _load_owner_id(self):
        """Carrega o ID do owner direto do config.json"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                config = json.load(f)
            return int(config.get("bot", {}).get("owner", 0))
        except Exception as e:
            print(f"❌ Erro ao carregar owner do config.json: {e}")
            return 0

    @commands.slash_command(
        name="backup",
        description="Gerencie os backups do servidor.",
    )
    @exclude_from_check
    async def backup(self, inter: disnake.ApplicationCommandInteraction):
        # ✅ Permite o owner do config.json OU quem já passava no perms.check_owner
        if inter.user.id != self.owner_id and not await perms.check_owner(inter.user.id):
            return await message.missing_perms(inter)
        
        backup_cog = self.bot.get_cog("Backup")
        if backup_cog:
            await backup_cog.display_backup_panel(inter)
        else:
            await message.error(inter, "O módulo de backup não está carregado.", send=True)


def setup(bot: commands.Bot):
    bot.add_cog(BackupCommand(bot))