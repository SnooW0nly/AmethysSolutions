import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.message import message
import uuid

class TopicsDB:
    @staticmethod
    def carregar_config() -> dict:
        data = db.get_document("automations_topics")
        if "ativado" not in data:
            data["ativado"] = False
        if "topicos" not in data:
            data["topicos"] = []
        return data

    @staticmethod
    def salvar_config(data: dict) -> None:
        db.save_document("automations_topics", {}, data)

class TopicoModal(disnake.ui.Modal):
    def __init__(self, channel_id: int):
        self.channel_id = channel_id
        components = [
            disnake.ui.TextInput(
                label="Nome do Tópico",
                custom_id="nome_topico",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
            ),
            disnake.ui.TextInput(
                label="Conteúdo do Tópico",
                custom_id="conteudo_topico",
                style=disnake.TextInputStyle.paragraph,
                required=True,
                max_length=4000,
                placeholder="Use {user} para mencionar quem enviou a mensagem",
            ),
            disnake.ui.TextInput(
                label="Trancado (sim/não)",
                custom_id="trancado",
                style=disnake.TextInputStyle.short,
                required=True,
                placeholder="Digite 'sim' para trancar o tópico",
                max_length=3,
            ),
        ]
        super().__init__(title="Criar Tópico Automático", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(with_message=False)
        
        nome = inter.text_values["nome_topico"]
        conteudo = inter.text_values["conteudo_topico"]
        trancado_str = inter.text_values["trancado"].lower()
        trancado = trancado_str == "sim"
        try:
            channel = inter.guild.get_channel(self.channel_id)
            if not channel or not isinstance(channel, disnake.TextChannel):
                await inter.followup.send("Selecione um canal de texto válido para tópicos automáticos.", ephemeral=True)
                return
            config = TopicsDB.carregar_config()
            novo_topico = {
                "id": str(uuid.uuid4()),
                "channel_id": self.channel_id,
                "name": nome,
                "content": conteudo,
                "locked": trancado,
            }
            config["topicos"].append(novo_topico)
            TopicsDB.salvar_config(config)

            from .cog import TopicsCog

            await message.wait(inter, send=False)
            await inter.edit_original_message(components=TopicsCog(inter.bot).Painel(inter.guild))
        except Exception as e:
            await inter.followup.send(f"Ocorreu um erro ao salvar: {e}", ephemeral=True)
