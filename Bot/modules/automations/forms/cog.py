import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils
from . import helpers
from .edit_form import EditFormView_components, EditFormView_embed, SpecificFormView_components, SpecificFormView_embed

class CreateFormModal(disnake.ui.Modal):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        components = [
            disnake.ui.TextInput(
                label="Nome do Formulário",
                placeholder="Ex: Aplicação para Staff",
                custom_id="form_name",
                max_length=50,
            ),
        ]
        super().__init__(title="Criar Novo Formulário", components=components, custom_id="create_form_modal")

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        
        form_id = utils.gerar_id()
        form_name = inter.text_values["form_name"]

        config = helpers.carregar_config()
        if "forms" not in config:
            config["forms"] = {}
            
        config["forms"][form_id] = {
            "name": form_name
        }
        helpers.salvar_config(config)
        
        # After creating, refresh the main panel
        if mode == "components":
            await inter.edit_original_message(components=FormsCog.Painel())
        else:
            embed, components = FormsCog.PainelEmbed()
            await inter.edit_original_message(content=None, embed=embed, components=components)

class FormsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @staticmethod
    def Painel() -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        forms = config.get("forms", {})
        form_count = len(forms)
        
        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.receipt} **Formulários Criados:** `{form_count}`\n"
        )

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Forms_ToggleAtivo"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Forms_Adicionar", disabled=not ativado),
            disnake.ui.Button(label="Editar", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Forms_Editar", disabled=form_count == 0 or not ativado),
        ]
        
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > **Formulários**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("Crie formulários personalizados para os membros preencherem."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(*botoes_principais),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        forms = config.get("forms", {})
        form_count = len(forms)

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.receipt} **Formulários Criados:** `{form_count}`\n"
        )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Formulários",
            description="Crie formulários personalizados para os membros preencherem."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        embed.add_field(name="Configurações", value=resumo, inline=False)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Forms_ToggleAtivo"),
                disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Forms_Adicionar", disabled=not ativado),
                disnake.ui.Button(label="Editar", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Forms_Editar", disabled=form_count == 0 or not ativado),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def Forms_Button_Listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "Forms_ToggleAtivo":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            config = helpers.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            helpers.salvar_config(config)
            
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.response.edit_message(content=None, embed=embed, components=components)
            else:
                await inter.response.edit_message(components=self.Painel())

        elif custom_id == "Forms_Adicionar":
            await inter.response.send_modal(CreateFormModal(self.bot))

        elif custom_id == "Forms_Editar":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
                embed, components = EditFormView_embed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter)
                components = EditFormView_components()
                await inter.edit_original_message(components=components)
        
        elif custom_id == "Forms_Painel":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter)
                await inter.edit_original_message(components=self.Painel())

        elif custom_id.startswith("FormEdit_"):
            action = custom_id.split("_")[1]
            
            # NOTE: Placeholder for future implementation
            if action == "SetMessage":
                await inter.response.edit_message(content="Funcionalidade 'Definir Mensagem' ainda não implementada.")
            elif action == "SetQuestions":
                await inter.response.edit_message(content="Funcionalidade 'Definir Perguntas' ainda não implementada.")
            elif action == "Advanced":
                await inter.response.edit_message(content="Funcionalidade 'Configurações Avançadas' ainda não implementada.")
            elif action == "Stats":
                await inter.response.edit_message(content="Funcionalidade 'Estatísticas' ainda não implementada.")


    @commands.Cog.listener("on_dropdown")
    async def Forms_Dropdown_Listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id.startswith("select_form_to_edit_"):
            form_id = inter.values[0]
            if form_id == "disabled":
                await inter.response.defer()
                return

            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
                embed, components = SpecificFormView_embed(form_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter)
                components = SpecificFormView_components(form_id)
                await inter.edit_original_message(components=components)


def setup(bot: commands.Bot):
    bot.add_cog(FormsCog(bot))
