import asyncio
import disnake
from functions.database import database
from functions.emoji import emoji
from .sync import Sincronizacao
import os


class BackupAutomatico:
    @staticmethod
    async def AutoBackupLoop(bot: disnake.Client):
        await bot.wait_until_ready()

        caminho_restore = "database/backup_configs.json"
        if not os.path.exists(caminho_restore):
            os.makedirs(os.path.dirname(caminho_restore), exist_ok=True)
            database.salvar(caminho_restore, {"backup_auto_ativo": False, "backup_auto_minutos": 360})

        while not bot.is_closed():
            try:
                definicoes = database.obter(caminho_restore)
                auto_ativo = definicoes.get("backup_auto_ativo", False)
                auto_minutos = definicoes.get("backup_auto_minutos", 0)

                if auto_ativo and auto_minutos > 0:
                    await asyncio.sleep(auto_minutos * 60)
                    config = database.obter("config.json")
                    server_id = int(config["bot"]["server"])
                    guild = bot.get_guild(server_id)

                    if guild:
                        try:
                            await Sincronizacao.BackupGuild(guild, bot, auto=True)
                        except Exception as e:
                            print(f"[AutoBackup] Erro ao executar backup automático: {e}")
                    else:
                        print("[AutoBackup] Servidor principal não encontrado para backup automático.")
                else:
                    await asyncio.sleep(60)

            except Exception as e:
                print(f"[AutoBackup] Erro no loop de backup automático: {e}")
                await asyncio.sleep(60)

    @staticmethod
    async def RealizarBackupInicial(bot: disnake.Client):
        await bot.wait_until_ready()
        try:
            config = database.obter("config.json")
            if not config.get("startOnBackup", False):
                return

            server_id = int(config["bot"]["server"])
            guild = bot.get_guild(server_id)

            if guild:
                try:
                    await Sincronizacao.BackupGuild(guild, bot, auto=True)
                except Exception as e:
                    print(f"[AutoBackup] Erro ao executar backup inicial: {e}")
            else:
                print("[AutoBackup] Servidor principal não encontrado para backup inicial.")
        except Exception as e:
            print(f"[AutoBackup] Erro no backup inicial: {e}")