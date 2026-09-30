import disnake
import asyncio
from functions.database import database
from functions.message import message, embed_message

class BackupAutoConfigModal(disnake.ui.Modal):
    def __init__(self, cog, minutos_atuais: int, mode: str):
        self.cog = cog
        self.mode = mode
        components = [
            disnake.ui.TextInput(
                label="Tempo entre backups (minutos)",
                placeholder="Ex: 60",
                value=str(minutos_atuais),
                custom_id="tempo_minutos",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=4
            )
        ]
        super().__init__(title="Configurar Backup Automático", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        tempo = inter.text_values.get("tempo_minutos")
        try:
            minutos = int(tempo)
            if minutos < 1:
                raise ValueError
        except Exception:
            if self.mode == "embed":
                await embed_message.error(inter, "Digite um valor válido (minutos > 0).", send=True)
            else:
                await message.error(inter, "Digite um valor válido (minutos > 0).", send=True)
            return
        
        definicoes = await self.cog.bot.loop.run_in_executor(
            None, database.obter, "database/backup_configs.json"
        )
        definicoes["backup_auto_minutos"] = minutos
        await self.cog.bot.loop.run_in_executor(
            None, database.salvar, "database/backup_configs.json", definicoes
        )
        
        if self.mode == "embed":
            await embed_message.sucesso(inter, f"Tempo do backup automático configurado para {minutos} minutos!", send=True)
        else:
            await message.sucesso(inter, f"Tempo do backup automático configurado para {minutos} minutos!", send=True)
        await asyncio.sleep(1)
        if self.mode == "embed":
            embed, components = self.cog.get_auto_backup_panel_components(embed_mode=True)
            await inter.edit_original_message(embed=embed, components=components)
        else:
            await inter.edit_original_message(components=self.cog.get_auto_backup_panel_components())


class RestoreGuildIDModal(disnake.ui.Modal):
    def __init__(self, cog, arquivo: str, mode: str):
        self.cog = cog
        self.arquivo = arquivo
        self.mode = mode
        components = [
            disnake.ui.TextInput(
                label="ID do Servidor (Opcional)",
                placeholder="Deixe em branco para restaurar no servidor principal.",
                custom_id="server_id",
                style=disnake.TextInputStyle.short,
                required=False,
                max_length=30
            )
        ]
        super().__init__(title="Informar Servidor de Restauração", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        server_id_str = inter.text_values.get("server_id", "").strip()
        target_guild = None

        if server_id_str:
            try:
                server_id = int(server_id_str)
                target_guild = self.cog.bot.get_guild(server_id)
                if not target_guild:
                    if self.mode == "embed":
                        await embed_message.error(inter, "Servidor com o ID fornecido não encontrado ou o bot não está nele.", send=True)
                    else:
                        await message.error(inter, "Servidor com o ID fornecido não encontrado ou o bot não está nele.", send=True)
                    return
            except ValueError:
                if self.mode == "embed":
                    await embed_message.error(inter, "O ID do servidor deve ser um número válido.", send=True)
                else:
                    await message.error(inter, "O ID do servidor deve ser um número válido.", send=True)
                return

        await self.cog.show_wipe_options(inter, self.arquivo, self.mode, target_guild)
