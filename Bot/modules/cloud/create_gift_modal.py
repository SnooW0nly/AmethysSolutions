import disnake
import uuid
import platform
import hashlib
import io
from functions.emoji import emoji
from functions.database import database as db
from .update_api import get_websocket_manager

class CreateGiftModal(disnake.ui.Modal):
    def __init__(self, bot=None):
        self.bot = bot
        components = [
            disnake.ui.TextInput(
                label="Quantidade de Membros",
                placeholder="Digite a quantidade de membros por gift (ex: 10)",
                custom_id="members_count",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=10
            ),
            disnake.ui.TextInput(
                label="Quantidade de Gifts (Opcional)",
                placeholder="Digite a quantidade de gifts a serem criados (padrão: 1)",
                custom_id="quantity",
                style=disnake.TextInputStyle.short,
                required=False,
                max_length=3
            ),
        ]

        super().__init__(
            title="Criar Gift",
            components=components
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            members_count_str = inter.text_values.get("members_count", "").strip()
            quantity_str = inter.text_values.get("quantity", "1").strip()
            
            # Validar entradas
            try:
                members_count = int(members_count_str)
                if members_count <= 0:
                    await inter.response.send_message(f"{emoji.wrong} A quantidade de membros deve ser maior que zero!", ephemeral=True)
                    return
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Por favor, digite um número válido para a quantidade de membros!", ephemeral=True)
                return

            try:
                quantity = int(quantity_str) if quantity_str else 1
                if quantity <= 0:
                    await inter.response.send_message(f"{emoji.wrong} A quantidade de gifts deve ser maior que zero!", ephemeral=True)
                    return
            except ValueError:
                await inter.response.send_message(f"{emoji.wrong} Por favor, digite um número válido para a quantidade de gifts!", ephemeral=True)
                return
            
            await inter.response.send_message(f"{emoji.loading} Criando {quantity} gift(s)...", ephemeral=True)
            
            # Obter configuração do cloud
            cloud_config = db.get_document("cloud_data") or {}
            bot_id = cloud_config.get("client_id")
            
            if not bot_id:
                await inter.edit_original_message(f"{emoji.wrong} Bot não configurado. Configure as credenciais primeiro.")
                return
            
            # Verificar conexão com o WebSocket
            ws_manager = get_websocket_manager()
            if not ws_manager.is_connected():
                await inter.edit_original_message(f"{emoji.wrong} WebSocket não está conectado. Verifique a conexão.")
                return
            
            # Verificar se há membros suficientes para criar pelo menos 1 gift
            # (os mesmos membros serão reutilizados em todos os gifts)
            response = await ws_manager.list_members(bot_id)
            
            if not response.get("success"):
                await inter.edit_original_message(f"{emoji.wrong} Erro ao verificar membros disponíveis: {response.get('message', 'Erro desconhecido')}")
                return
            
            available_members = response.get("data", {}).get("total", 0)
            
            # Verificar se há pelo menos a quantidade de membros necessária para 1 gift
            if available_members < members_count:
                await inter.edit_original_message(
                    f"{emoji.wrong} **Membros insuficientes!**\n\n"
                    f"**Membros por Gift:** `{members_count}`\n"
                    f"**Membros Disponíveis:** `{available_members}`\n\n"
                    f"Você precisa de pelo menos `{members_count}` membros para criar um gift."
                )
                return
            
            # Criar todos os gifts solicitados (os mesmos membros serão reutilizados em todos)
            await inter.edit_original_message(f"{emoji.loading} Criando {quantity} gift(s)...")

            gift_urls = []
            gift_ids = []
            failed_count = 0
            
            for i in range(quantity):
                gift_url, gift_id = await self._create_gift(inter, members_count, bot_id)
                if not gift_url:
                    failed_count += 1
                    # Continuar tentando criar os outros gifts mesmo se um falhar
                    continue
                gift_urls.append(gift_url)
                gift_ids.append(gift_id)

            if not gift_urls:
                await inter.edit_original_message(f"{emoji.wrong} Nenhum gift foi criado devido a erros.")
                return

            # Montar mensagem de sucesso
            created_count = len(gift_urls)
            
            if created_count == 1:
                success_message = f"{emoji.correct} **Gift criado com sucesso!**\n\n"
                success_message += f"**ID do Gift:** `{gift_ids[0]}`\n"
                success_message += f"**Membros:** `{members_count}`\n"
                success_message += f"**Link:** {gift_urls[0]}\n\n"
                success_message += "Compartilhe este link para que outros possam resgatar o gift!"
                
                await inter.edit_original_message(content=success_message, attachments=[])
            else:
                gift_lines = [f"{i+1}: {url}" for i, url in enumerate(gift_urls)]
                file_content = "\n".join(gift_lines)
                file_bytes = io.BytesIO(file_content.encode('utf-8'))
                file = disnake.File(file_bytes, filename="gifts.txt")

                success_message = f"{emoji.correct} **{created_count} gift(s) criado(s) com sucesso!**\n\n"
                success_message += f"**Membros por Gift:** `{members_count}`\n"
                
                if failed_count > 0:
                    success_message += f"{emoji.wrong} **Aviso:** `{failed_count}` gift(s) falharam ao ser criado(s).\n\n"
                
                success_message += "Os links dos gifts estão no arquivo anexado."
                
                await inter.edit_original_message(content=success_message, file=file)

        except Exception as e:
            print(f"Erro ao processar criação de gift: {e}")
            await inter.edit_original_message(f"{emoji.wrong} Erro ao processar criação de gift: {str(e)}")

    async def _create_gift(self, inter: disnake.ModalInteraction, members_count: int, bot_id: str) -> tuple[str, str] | tuple[None, None]:
        """Cria o gift e retorna o link e o id"""
        try:
            # Gerar ID único para o gift
            gift_id = self._generate_gift_id()
            
            # Criar dados do gift
            gift_data = {
                "id": gift_id,
                "bot_id": bot_id,
                "members_count": members_count,
                "created_by": {
                    "id": str(inter.user.id),
                    "name": inter.user.display_name
                },
                "created_at": disnake.utils.utcnow().isoformat(),
                "status": "active",
                "used_count": 0,
                "max_uses": 1  # Por enquanto, 1 uso por gift
            }
            
            # Salvar gift via WebSocket
            ws_manager = get_websocket_manager()
            response = await ws_manager.create_gift(bot_id, gift_data)
            
            if not response.get("success"):
                print(f"Erro ao criar gift via WebSocket: {response.get('message', 'Erro desconhecido')}")
                return None, None
            
            # Gerar link do gift
            from .cloud_config import get_gifts_url
            gift_url = get_gifts_url(gift_id)
            return gift_url, gift_id
            
        except Exception as e:
            print(f"Erro na função _create_gift: {e}")
            return None, None

    def _generate_gift_id(self) -> str:
        """Gera um ID único para o gift baseado no hardware"""
        try:
            # Obter informações do sistema
            system_info = f"{platform.system()}_{platform.machine()}_{platform.processor()}"
            
            # Gerar hash único
            unique_string = f"{system_info}_{uuid.uuid4()}_{disnake.utils.utcnow().timestamp()}"
            gift_id = hashlib.md5(unique_string.encode()).hexdigest()[:12]
            
            return gift_id
        except Exception as e:
            print(f"Erro ao gerar ID do gift: {e}")
            # Fallback para UUID simples
            return str(uuid.uuid4())[:12]
