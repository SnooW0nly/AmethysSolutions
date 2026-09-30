import disnake
from disnake.ext import commands
from typing import Any, Dict, Tuple

from ..anunciar import Anunciar
from functions.database import database
from functions.message import message

CID_MODAL = "Anunciar_ImagesModal"
CID_DEFINE = "Anunciar_DefinirImagem"
CID_DELETE = "Anunciar_ApagarImagem"

ID_IMAGE_OUTER = "Anunciar_ImageFora"
ID_IMAGE_BANNER = "Anunciar_ImageBanner"
ID_IMAGE_THUMB = "Anunciar_ImageThumbnail"

class Images(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def _load_config() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        cfg: Dict[str, Any] = database.get_document("messages_anunciar") or {}
        message_cfg: Dict[str, Any] = cfg.setdefault("message", {}) or {}
        embed_cfg: Dict[str, Any] = message_cfg.get("embed")

        if not isinstance(embed_cfg, dict):
            embed_cfg = {}
            message_cfg["embed"] = embed_cfg

        message_cfg.setdefault("externalImage", None)
        embed_cfg.setdefault("banner", None)
        embed_cfg.setdefault("thumbnail", None)
        return cfg, message_cfg, embed_cfg

    @staticmethod
    def _has_embed(cfg: Dict[str, Any]) -> bool:
        return any(
            [
                Anunciar._safe_get(cfg, "message.embed.title"),
                Anunciar._safe_get(cfg, "message.embed.description"),
                Anunciar._safe_get(cfg, "message.embed.color"),
                Anunciar._safe_get(cfg, "message.embed.footer"),
            ]
        )

    @staticmethod
    def _save_config(cfg: Dict[str, Any]) -> None:
        database.save_document("messages_anunciar", {}, cfg)

    class DefinirImagesModal(disnake.ui.Modal):
        def __init__(self):
            cfg, message_cfg, embed_cfg = Images._load_config()
            self.cfg = cfg
            self.message_cfg = message_cfg
            self.embed_cfg = embed_cfg

            components: list[disnake.ui.TextInput] = [
                disnake.ui.TextInput(
                    label="URL da imagem por fora",
                    custom_id=ID_IMAGE_OUTER,
                    style=disnake.TextInputStyle.short,
                    placeholder="Digite a URL da imagem por fora",
                    value=message_cfg.get("externalImage") or "",
                    required=False,
                ),
            ]

            if Images._has_embed(cfg):
                components.extend(
                    [
                        disnake.ui.TextInput(
                            label="URL do Banner do Embed",
                            custom_id=ID_IMAGE_BANNER,
                            style=disnake.TextInputStyle.short,
                            placeholder="Digite a URL do banner do embed",
                            value=embed_cfg.get("banner") or "",
                            required=False,
                        ),
                        disnake.ui.TextInput(
                            label="URL do Thumbnail do Embed",
                            custom_id=ID_IMAGE_THUMB,
                            style=disnake.TextInputStyle.short,
                            placeholder="Digite a URL da Thumbnail do embed",
                            value=embed_cfg.get("thumbnail") or "",
                            required=False,
                        ),
                    ]
                )

            super().__init__(title="Definir Imagens", custom_id=CID_MODAL, components=components)

        async def callback(self, inter: disnake.ModalInteraction):
            await message.wait(inter, send=False)

            cfg, message_cfg, embed_cfg = Images._load_config()

            message_cfg["externalImage"] = inter.text_values.get(ID_IMAGE_OUTER) or None
            if ID_IMAGE_BANNER in inter.text_values:
                embed_cfg["banner"] = inter.text_values.get(ID_IMAGE_BANNER) or None
            if ID_IMAGE_THUMB in inter.text_values:
                embed_cfg["thumbnail"] = inter.text_values.get(ID_IMAGE_THUMB) or None

            Images._save_config(cfg)
            await inter.edit_original_message(components=Anunciar.create_buttons())

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == CID_DEFINE:
            await inter.response.send_modal(self.DefinirImagesModal())
            return

        if inter.component.custom_id == CID_DELETE:
            await message.wait(inter, send=False)

            cfg, message_cfg, embed_cfg = Images._load_config()
            message_cfg["externalImage"] = None
            embed_cfg["banner"] = None
            embed_cfg["thumbnail"] = None

            Images._save_config(cfg)
            await inter.edit_original_message(components=Anunciar.create_buttons())