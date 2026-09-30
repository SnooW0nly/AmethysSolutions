import disnake
from functions.emoji import emoji
from functions.database import database as db
from .update_api import get_websocket_manager

class DeleteGiftModal(disnake.ui.Modal):
    def __init__(self, bot=None, gift_id: str = None):
        self.bot = bot
        self.gift_id = gift_id
        
        components = [
            disnake.ui.TextInput(
                label="Confirmação",
                placeholder="Digite 'SIM' para confirmar a deleção do gift",
                custom_id="confirmation",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=10
            ),
        ]

        super().__init__(
            title="Confirmar Deleção do Gift",
            components=components
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            confirmation = inter.text_values.get("confirmation", "").strip().upper()
            
            # Verificar confirmação
            if confirmation != "SIM":
                await inter.response.send_message(f"{emoji.wrong} Confirmação inválida! Digite 'SIM' para confirmar a deleção.", ephemeral=True)
                return
            
            # Enviar mensagem de loading
            await inter.response.send_message(f"{emoji.loading} Deletando gift...", ephemeral=True)
            
            # Deletar o gift
            await self._delete_gift(inter)
            
        except Exception as e:
            print(f"Erro ao processar deleção de gift: {e}")
            await inter.edit_original_message(f"{emoji.wrong} Erro ao processar deleção de gift: {str(e)}")

    async def _delete_gift(self, inter: disnake.ModalInteraction):
        """Deleta o gift"""
        try:
            # Criar dados para deleção
            delete_data = {
                "gift_id": self.gift_id,
                "deleted_by": {
                    "id": str(inter.user.id),
                    "name": inter.user.display_name
                }
            }
            
            # Enviar via WebSocket
            ws_manager = get_websocket_manager()
            response = await ws_manager.delete_gift(delete_data)
            
            if not response.get("success"):
                await inter.edit_original_message(f"{emoji.wrong} Erro ao deletar gift: {response.get('message', 'Erro desconhecido')}")
                return
            
            # Mostrar sucesso
            success_message = f"{emoji.correct} **Gift deletado com sucesso!**\n\n"
            success_message += f"**ID do Gift:** `{self.gift_id}`\n\n"
            success_message += f"O gift foi removido permanentemente!"
            
            await inter.edit_original_message(success_message)
            
        except Exception as e:
            print(f"Erro ao deletar gift: {e}")
            await inter.edit_original_message(f"{emoji.wrong} Erro ao deletar gift: {str(e)}")

class DeleteGiftByCodeModal(disnake.ui.Modal):
    def __init__(self, bot=None):
        self.bot = bot
        components = [
            disnake.ui.TextInput(
                label="ID do Gift",
                placeholder="Cole o ID do gift que você deseja deletar",
                custom_id="gift_id",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=50
            ),
        ]
        super().__init__(title="Deletar Gift por Código", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            gift_id = inter.text_values["gift_id"].strip()
            if not gift_id:
                await inter.response.send_message("O ID do gift não pode estar vazio.", ephemeral=True)
                return

            await inter.response.send_message(f"{emoji.loading} Deletando gift...", ephemeral=True)

            delete_data = {
                "gift_id": gift_id,
                "deleted_by": {
                    "id": str(inter.user.id),
                    "name": inter.user.display_name
                }
            }

            ws_manager = get_websocket_manager()
            if not ws_manager.is_connected():
                await inter.edit_original_message(f"{emoji.wrong} WebSocket não conectado.")
                return

            response = await ws_manager.delete_gift(delete_data)

            if not response.get("success"):
                await inter.edit_original_message(f"{emoji.wrong} Erro ao deletar gift: {response.get('message', 'ID não encontrado ou erro interno')}")
                return

            success_message = f"{emoji.correct} **Gift deletado com sucesso!**\n\n**ID:** `{gift_id}`"
            await inter.edit_original_message(success_message)

        except Exception as e:
            print(f"Erro ao processar deleção de gift por código: {e}")
            await inter.edit_original_message(f"{emoji.wrong} Erro ao processar a deleção.")

class DeleteAllGiftsModal(disnake.ui.Modal):
    def __init__(self, bot=None):
        self.bot = bot
        components = [
            disnake.ui.TextInput(
                label="Confirmação",
                placeholder="Digite 'DELETAR TUDO' para confirmar",
                custom_id="confirmation",
                style=disnake.TextInputStyle.short,
                required=True
            ),
        ]
        super().__init__(title="DELETAR TODOS OS GIFTS", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            confirmation = inter.text_values["confirmation"].strip()
            if confirmation != "DELETAR TUDO":
                await inter.response.send_message("Confirmação incorreta. A operação foi cancelada.", ephemeral=True)
                return

            await inter.response.send_message(f"{emoji.loading} Deletando TODOS os gifts...", ephemeral=True)

            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")

            if not bot_id:
                await inter.edit_original_message(f"{emoji.wrong} Bot não configurado.")
                return

            delete_data = {
                "bot_id": bot_id,
                "deleted_by": {
                    "id": str(inter.user.id),
                    "name": inter.user.display_name
                }
            }

            ws_manager = get_websocket_manager()
            if not ws_manager.is_connected():
                await inter.edit_original_message(f"{emoji.wrong} WebSocket não conectado.")
                return

            response = await ws_manager.delete_all_gifts(delete_data)

            if not response.get("success"):
                await inter.edit_original_message(f"{emoji.wrong} Erro ao deletar gifts: {response.get('message', 'Erro desconhecido')}")
                return

            count = response.get("data", {}).get("deleted_count", "Todos")
            success_message = f"{emoji.correct} **Operação concluída!**\n\n`{count}` gifts foram deletados com sucesso."
            await inter.edit_original_message(success_message)

        except Exception as e:
            print(f"Erro ao processar deleção de todos os gifts: {e}")
            await inter.edit_original_message(f"{emoji.wrong} Erro ao processar a deleção em massa.")
