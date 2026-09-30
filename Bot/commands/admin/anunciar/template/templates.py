import disnake
import time

from disnake.ext import commands
from functions.database import database
from functions.emoji import emoji
from functions.message import message
from functions.utils import utils
from ..anunciar import Anunciar
from .save import SaveTemplateModal
from .actions import apply_template, preview_template, send_template
from .db_helper import get_all_templates, get_template_by_id, delete_template, delete_all_templates, save_template


class Templates(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def create_buttons():
        templates = get_all_templates()
        options = []

        for template in templates:
            ts = int(template.get("savedAt") or time.time())
            rel = Templates._format_relative_timestamp(ts)
            options.append(
                disnake.SelectOption(
                    label=template.get("name", "Sem nome"),
                    value=template.get("id"),
                    emoji=emoji.save,
                    description=f"Salvo: {rel}"
                )
            )

        if len(options) == 0:
            options.append(
                disnake.SelectOption(label="Nenhum template encontrado", value="none", emoji=emoji.warn)
            )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Anunciar > Templates salvos"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Gerencie e personalize templates de mensagens salvos.\nVocê possui `{len(templates)}` templates salvos."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Salvar template do anúncio atual", style=disnake.ButtonStyle.primary, emoji=emoji.arrow, custom_id="Anunciar_SalvarTemplate", disabled=Anunciar.is_empty()),
                    disnake.ui.Button(label="Apagar templates", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="Anunciar_ApagarTodosTemplates", disabled=True if len(templates) == 0 else False),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(options=options, custom_id="Anunciar_Templates_Select", placeholder="Selecione um template para configurar", disabled=True if len(templates) == 0 else False)
                )
            ),
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.secondary, emoji=emoji.back, custom_id="Anunciar_PainelInicial"),
        ]

    @staticmethod
    def _format_relative_timestamp(ts: int) -> str:
        now = int(time.time())
        diff = now - int(ts)
        if diff < 0:
            diff = 0
        if diff < 60:
            return "agora"
        minutes = diff // 60
        if minutes < 60:
            return f"há {minutes} min"
        hours = minutes // 60
        if hours < 24:
            return f"há {hours} h"
        days = hours // 24
        if days < 30:
            return f"há {days} d"
        months = days // 30
        if months < 12:
            return f"há {months} m"
        years = months // 12
        return f"há {years} a"

    @staticmethod
    def template_actions(tpl: dict) -> list:
        data = tpl.get("data") or {}
        msg = (data.get("message") or {}) if isinstance(data, dict) else {}
        has_message = bool(msg.get("content"))
        has_container = msg.get("container") is not None
        embed_cfg = msg.get("embed") or {}
        has_embed = any([embed_cfg.get("title"), embed_cfg.get("description"), embed_cfg.get("color"), embed_cfg.get("footer")])
        has_image = any([msg.get("externalImage"), (embed_cfg or {}).get("banner"), (embed_cfg or {}).get("thumbnail")])
        buttons = msg.get("buttons") or []
        ts = int(tpl.get("savedAt") or time.time())

        info_lines = [
            f"**Nome do template:** `{tpl.get('name', 'Sem nome')}`",
            f"**Template salvo em:** <t:{ts}:R> (<t:{ts}:F>)",
        ]

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Anunciar > Templates > {tpl.get('name', 'Sem nome')}"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("\n".join(info_lines)),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Aplicar template", style=disnake.ButtonStyle.blurple, emoji=emoji.save, custom_id=f"Anunciar_Templates_Aplicar_{tpl.get('id')}"),
                    disnake.ui.Button(label="Preview", style=disnake.ButtonStyle.secondary, emoji=emoji.search, custom_id=f"Anunciar_Templates_Preview_{tpl.get('id')}"),
                    disnake.ui.Button(label="Apagar template", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"Anunciar_Templates_Apagar_{tpl.get('id')}")
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Substituir com atual", style=disnake.ButtonStyle.secondary, emoji=emoji.edit, custom_id=f"Anunciar_Templates_Substituir_{tpl.get('id')}", disabled=Anunciar.is_empty()),
                    disnake.ui.Button(label="Enviar template no canal atual", style=disnake.ButtonStyle.green, emoji=emoji.arrow, custom_id=f"Anunciar_Templates_Enviar_{tpl.get('id')}", disabled=Anunciar.is_empty()),
                )
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.secondary, emoji=emoji.back, custom_id="Anunciar_Templates")),
        ]

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_Templates":
            await message.wait(inter, send=False)
            components = Templates.create_buttons()
            await inter.edit_original_message(components=components)

        elif inter.component.custom_id == "Anunciar_SalvarTemplate":
            await inter.response.send_modal(SaveTemplateModal())

        elif inter.component.custom_id == "Anunciar_ApagarTodosTemplates":
            await message.wait(inter, send=False)
            delete_all_templates()
            await inter.edit_original_message(components=Templates.create_buttons())

        elif inter.component.custom_id.startswith("Anunciar_Templates_Apagar_"):
            await message.wait(inter, send=False)
            tpl_id = inter.component.custom_id.replace("Anunciar_Templates_Apagar_", "")
            delete_template(tpl_id)
            await inter.edit_original_message(components=Templates.create_buttons())

        elif inter.component.custom_id.startswith("Anunciar_Templates_Aplicar_"):
            await message.wait(inter, send=False)
            tpl_id = inter.component.custom_id.replace("Anunciar_Templates_Aplicar_", "")
            await apply_template(inter, tpl_id)

        elif inter.component.custom_id.startswith("Anunciar_Templates_Substituir_"):
            await message.wait(inter, send=False)
            tpl_id = inter.component.custom_id.replace("Anunciar_Templates_Substituir_", "")
            tpl = get_template_by_id(tpl_id)
            if not tpl:
                await message.error(inter, "Template não encontrado.", send=False)
                return
            current_cfg = database.get_document("messages_anunciar") or {}
            tpl["data"] = current_cfg
            tpl["savedAt"] = int(time.time())
            save_template(tpl)
            await inter.edit_original_message(components=Templates.template_actions(tpl))

        elif inter.component.custom_id.startswith("Anunciar_Templates_Preview_"):
            tpl_id = inter.component.custom_id.replace("Anunciar_Templates_Preview_", "")
            await preview_template(inter, tpl_id)

        elif inter.component.custom_id.startswith("Anunciar_Templates_Enviar_"):
            tpl_id = inter.component.custom_id.replace("Anunciar_Templates_Enviar_", "")
            await send_template(inter, tpl_id)

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Anunciar_Templates_Select":
            await message.wait(inter, send=False)
            
            tpl_id = inter.values[0] if inter.values else None
            if not tpl_id or tpl_id == "none":
                return

            tpl = get_template_by_id(tpl_id)
            if not tpl:
                await message.error(inter, "Template não encontrado.", send=False)
                return
            
            await inter.edit_original_message(components=Templates.template_actions(tpl))