import disnake
from functions.emoji import emoji
from functions.database import database as db
from .update_api import get_websocket_manager

class EditGiftModal(disnake.ui.Modal):
    def __init__(self, bot=None, gift_id: str = None):
        self.bot = bot
        self.gift_id = gift_id
        
        components = [
            disnake.ui.TextInput(
                label="Nova Quantidade de Membros",
                placeholder="Digite a nova quantidade de membros para o gift",
                custom_id="new_members_count",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=10
            ),
        ]

        super().__init__(
            title="Editar Gift",
            components=components
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            new_members_count_str = inter.text_values.get("new_members_count", "").strip()
            
            # Validar entrada
            try:
                new_members_count = int(new_members_count_str)
                if new_members_count <= 0:
                    await inter.response.send_message(f"{emoji.wrong} A quantidade de membros deve ser maior que zero!", ephemeral=True)
                    return
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Por favor, digite um número válido para a quantidade de membros!", ephemeral=True)
                return
            
            # Enviar mensagem de loading
            await inter.response.send_message(f"{emoji.loading} Atualizando gift...", ephemeral=True)
            
            # Obter configuração do cloud
            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")
            
            if not bot_id:
                await inter.edit_original_message(f"{emoji.wrong} Bot não configurado.")
                return
            
            ws_manager = get_websocket_manager()
            if not ws_manager.is_connected():
                await inter.edit_original_message(f"{emoji.wrong} WebSocket não conectado.")
                return

            # Obter gift atual para saber a contagem de membros antiga
            response = await ws_manager.get_gifts(bot_id)
            if not response.get("success"):
                await inter.edit_original_message(f"{emoji.wrong} Erro ao buscar dados do gift: {response.get('message', 'Erro desconhecido')}")
                return
            
            gifts = response.get("data", {}).get("gifts", [])
            current_gift = next((g for g in gifts if g.get("id") == self.gift_id), None)
            
            if not current_gift:
                await inter.edit_original_message(f"{emoji.wrong} Gift com ID `{self.gift_id}` não encontrado.")
                return
                
            old_members_count = current_gift.get("members_count", 0)
            members_needed = new_members_count - old_members_count

            # Fazer requisição para verificar membros disponíveis
            response = await ws_manager.list_members(bot_id)
            
            if not response.get("success"):
                await inter.edit_original_message(f"{emoji.wrong} Erro ao verificar membros: {response.get('message', 'Erro desconhecido')}")
                return
            
            # Verificar se tem membros suficientes
            available_members = response.get("data", {}).get("total", 0)

            if members_needed > 0 and available_members < members_needed:
                await inter.edit_original_message(
                    f"{emoji.wrong} **Membros insuficientes!**\n\n"
                    f"**Alteração:** de `{old_members_count}` para `{new_members_count}` membros\n"
                    f"**Necessário:** `{members_needed}` membros adicionais\n"
                    f"**Disponível:** `{available_members}` membros\n\n"
                    f"Você precisa de mais `{members_needed - available_members}` membros para atualizar este gift."
                )
                return
            
            # Atualizar o gift
            await self._update_gift(inter, new_members_count)
            
        except Exception as e:
            print(f"Erro ao processar edição de gift: {e}")
            await inter.edit_original_message(f"{emoji.wrong} Erro ao processar edição de gift: {str(e)}")

    async def _update_gift(self, inter: disnake.ModalInteraction, new_members_count: int):
        """Atualiza o gift"""
        try:
            # Criar dados para atualização
            update_data = {
                "gift_id": self.gift_id,
                "new_members_count": new_members_count,
                "updated_by": {
                    "id": str(inter.user.id),
                    "name": inter.user.display_name
                }
            }
            
            # Enviar via WebSocket
            ws_manager = get_websocket_manager()
            response = await ws_manager.update_gift(update_data)
            
            if not response.get("success"):
                await inter.edit_original_message(f"{emoji.wrong} Erro ao atualizar gift: {response.get('message', 'Erro desconhecido')}")
                return
            
            # Mostrar sucesso
            success_message = f"{emoji.correct} **Gift atualizado com sucesso!**\n\n"
            success_message += f"**ID do Gift:** `{self.gift_id}`\n"
            success_message += f"**Nova quantidade de membros:** `{new_members_count}`\n\n"
            success_message += f"O gift foi atualizado e está pronto para uso!"
            
            await inter.edit_original_message(success_message)
            
        except Exception as e:
            print(f"Erro ao atualizar gift: {e}")
            await inter.edit_original_message(f"{emoji.wrong} Erro ao atualizar gift: {str(e)}")
