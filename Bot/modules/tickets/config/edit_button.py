import disnake
from functions.database import database as db
from functions.message import message
from .edit_message import MessageEditView_components, MessageEditView_embed
from functions.utils import utils

class EditButtonModal(disnake.ui.Modal):
    def __init__(self, panel_id: str, data: dict):
        self.panel_id = panel_id
        
        color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
        current_style_en = data.get("style", "green")
        current_style_pt = next((pt for pt, en in color_map_pt_to_en.items() if en == current_style_en), "verde")

        components = [
            disnake.ui.TextInput(label="Texto do Botão", custom_id="label", value=data.get("label"), max_length=30, required=True, placeholder="Clique para abrir um ticket"),
            disnake.ui.TextInput(label="Emoji do Botão (Opcional)", custom_id="emoji", value=data.get("emoji"), required=False, max_length=100, placeholder="🎟️ ou <:nome:ID>"),
            disnake.ui.TextInput(label="Estilo (verde, cinza, vermelho, azul)", custom_id="style", value=current_style_pt, max_length=10, required=True, placeholder="Ex: verde"),
        ]
        super().__init__(title="Editar Botão do Painel", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        config = db.get_document("tickets_config") or {}
        if self.panel_id in config.get("panels", {}):
            
            # Garante que a chave 'button' exista para painéis antigos
            if "button" not in config["panels"][self.panel_id]:
                config["panels"][self.panel_id]["button"] = {}

            option_emoji = inter.text_values["emoji"]
            if option_emoji:
                validation = utils.validate_emoji_for_components(option_emoji)
                if not validation["valid"]:
                    error_msg = validation.get("error", "Emoji inválido")
                    return await message.error(inter, f"O emoji fornecido não é válido para uso em componentes. {error_msg}\n\nUse um emoji unicode (ex: ✅) ou um emoji customizado no formato <:nome:id>.")
                # Converter para string apropriada
                if isinstance(validation["emoji"], disnake.PartialEmoji):
                    option_emoji = str(validation["emoji"])
                else:
                    option_emoji = validation["emoji"]

            color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
            style_pt = inter.text_values.get("style", "verde").lower()
            style_en = color_map_pt_to_en.get(style_pt, "green")
            
            config["panels"][self.panel_id]["button"]["label"] = inter.text_values["label"]
            config["panels"][self.panel_id]["button"]["emoji"] = option_emoji
            config["panels"][self.panel_id]["button"]["style"] = style_en
            config["panels"][self.panel_id]["has_pending_changes"] = True
            db.save_document("tickets_config", config)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.response.edit_message(components=MessageEditView_components(inter, self.panel_id))
        else:
            embed, components = MessageEditView_embed(inter, self.panel_id)
            await inter.response.edit_message(embed=embed, components=components)
