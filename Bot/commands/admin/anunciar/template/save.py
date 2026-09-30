import disnake
import time

from functions.database import database
from functions.message import message
from functions.utils import utils
from ..anunciar import Anunciar
from .db_helper import save_template


class SaveTemplateModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Salvar template",
            custom_id="Anunciar_SalvarTemplateModal",
            components=[
                disnake.ui.TextInput(
                    label="Nome do template",
                    custom_id="template_name",
                    placeholder="Meu template",
                    required=True,
                    max_length=64,
                    style=disnake.TextInputStyle.short,
                ),
            ],
        )

    async def callback(self, inter: disnake.ModalInteraction):
        await message.wait(inter, send=False)
        name = (inter.text_values.get("template_name") or "").strip()
        if not name:
            await message.error(inter, "Informe um nome para o template.", send=False)
            return

        if Anunciar.is_empty():
            await message.error(inter, "O anúncio atual está vazio.", send=False)
            return

        cfg = database.get_document("messages_anunciar") or {}
        template = {
            "id": utils.gerar_id(),
            "name": name,
            "data": cfg,
            "savedAt": int(time.time()),
        }
        save_template(template)
        from .templates import Templates  # local import to avoid cycle
        await inter.edit_original_message(components=Templates.create_buttons())


def modal() -> SaveTemplateModal:
    return SaveTemplateModal()

