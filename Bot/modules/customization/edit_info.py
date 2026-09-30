import base64
import requests
import disnake
from disnake import *

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message

class edit_info_bot_modal(disnake.ui.Modal):
    token = db.obter("config.json")["bot"]["token"]

    def __init__(self, default_name=None):
        bot_nome = default_name or "Bot"

        components = [
            disnake.ui.TextInput(
                label="Nome do Bot",
                placeholder="Digite o novo nome do bot",
                value=bot_nome,
                custom_id="nome_bot",
                style=disnake.TextInputStyle.short,
                required=False,
            ),
            disnake.ui.TextInput(
                label="URL do Avatar do Bot",
                placeholder="Digite a URL do novo avatar do bot",
                custom_id="avatar_bot",
                style=disnake.TextInputStyle.short,
                required=False,
            ),
            disnake.ui.TextInput(
                label="URL do Banner do Bot",
                placeholder="Digite a URL do novo banner do bot",
                custom_id="banner_bot",
                style=disnake.TextInputStyle.short,
                required=False,
            ),
        ]
        super().__init__(title="Editar Informações do Bot", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        nome_bot   = inter.text_values.get("nome_bot")
        avatar_url = inter.text_values.get("avatar_bot")
        banner_url = inter.text_values.get("banner_bot")

        mode = db.get_document("custom_mode").get("mode")

        if mode == "embed":
            await embed_message.wait(inter, send=True, ephemeral=True)
        else:
            await message.wait(inter, send=True, ephemeral=True)

        # Salva o username novo só se realmente mudou
        if nome_bot:
            bot_info = db.get_document("custom_bot_info") or {}
            if bot_info.get("username") != nome_bot:
                bot_info["username"] = nome_bot
                db.save_document("custom_bot_info", {}, bot_info)

        url = "https://discord.com/api/v9/users/@me"
        headers = {"Authorization": f"Bot {self.token}"}

        payload = {}
        if nome_bot:
            payload["username"] = nome_bot
        if avatar_url:
            avatar_data = requests.get(avatar_url).content
            payload["avatar"] = f"data:image/png;base64,{base64.b64encode(avatar_data).decode()}"
        if banner_url:
            banner_data = requests.get(banner_url).content
            payload["banner"] = f"data:image/png;base64,{base64.b64encode(banner_data).decode()}"

        response = requests.patch(url, headers=headers, json=payload)

        if response.status_code == 200:
            if mode == "embed":
                await embed_message.success(inter, "As alterações foram salvas com sucesso.", send=False)
            else:
                await message.success(inter, "As alterações foram salvas com sucesso.", send=False)
        else:
            if mode == "embed":
                await embed_message.error(inter, f"Não foi possível atualizar as informações do bot: `{response.status_code}`\n```{response.text}```", send=False)
            else:
                await message.error(inter, f"Não foi possível atualizar as informações do bot: `{response.status_code}`\n```{response.text}```", send=False)