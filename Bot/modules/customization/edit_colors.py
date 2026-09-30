import disnake
from disnake.ext import commands
import re

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.utils import utils

class EditColorsModal(disnake.ui.Modal):
    def __init__(self):
        self.colors = db.get_document("custom_colors")
        components = [
            disnake.ui.TextInput(
                label="Cor Primária",
                custom_id="primary",
                value=self.colors.get("primary"),
                placeholder="Ex: #ffffff",
                required=True,
                max_length=7,
                min_length=7,
            ),
            disnake.ui.TextInput(
                label="Cor Secundária",
                custom_id="secondary",
                value=self.colors.get("secondary"),
                placeholder="Ex: #6c757d",
                required=True,
                max_length=7,
                min_length=7,
            ),
            disnake.ui.TextInput(
                label="Cor de Sucesso",
                custom_id="success",
                value=self.colors.get("success"),
                placeholder="Ex: #28a745",
                required=True,
                max_length=7,
                min_length=7,
            ),
            disnake.ui.TextInput(
                label="Cor de Perigo",
                custom_id="danger",
                value=self.colors.get("danger"),
                placeholder="Ex: #dc3545",
                required=True,
                max_length=7,   
                min_length=7,
            ),
            disnake.ui.TextInput(
                label="Cor de Aviso",
                custom_id="warning",
                value=self.colors.get("warning"),
                placeholder="Ex: #ffc107",
                required=True,
                max_length=7,
                min_length=7,
            ),
        ]
        super().__init__(title="Editor de Cores", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        
        # Hex color validation regex
        hex_pattern = re.compile(r'^#?([0-9a-fA-F]{6})$')
        
        new_colors = {}
        for key, value in inter.text_values.items():
            if not value or not hex_pattern.match(value):
                error_message = f"O valor `{value}` para a cor **{key.capitalize()}** é obrigatório e deve estar no formato hexadecimal #RRGGBB."
                if not inter.response.is_done():
                    await inter.response.send_message(
                        content=error_message, ephemeral=True
                    )
                else:
                    await inter.edit_original_message(
                        content=error_message, embed=None, components=[]
                    )
                return
            normalized = utils.normalize_hex_color(value)
            if not normalized:
                error_message = f"A cor informada para **{key.capitalize()}** é inválida. Use o formato #RRGGBB."
                if not inter.response.is_done():
                    await inter.response.send_message(
                        content=error_message, ephemeral=True
                    )
                else:
                    await inter.edit_original_message(
                        content=error_message, embed=None, components=[]
                    )
                return
            new_colors[key] = normalized
        db.save_document("custom_colors", {}, new_colors)
        # Responda ao modal editando a mensagem original
        if mode == "embed":
            embed, components = EditColorsCog.get_panel_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)
        else:
            await inter.response.edit_message(components=EditColorsCog.get_panel_components(inter))

class EditColorsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def get_panel_components(inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        color_previews = "\n".join([f"- **{name.capitalize()}:** `{code}`" for name, code in colors.items() if code])

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Personalização > **Cores**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure as cores utilizadas pelo seu Zenity Pro."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(    
                    f"**Cores Atuais:**\n{color_previews}"
                ),    
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Editar Cores", style=disnake.ButtonStyle.grey,
                                      emoji=emoji.edit, custom_id="Personalizacao_EditarCores_Modal"),
                    disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey,
                                      emoji=emoji.arrow, custom_id="Personalizacao_VisualizarCores"),
                    disnake.ui.Button(label="Paleta de Cores", style=disnake.ButtonStyle.link,
                                      url="https://htmlcolorcodes.com/"),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                                  emoji=emoji.back, custom_id="Painel_Personalizacao"),
            )
        ]

    @staticmethod
    def get_panel_embed(inter: disnake.MessageInteraction):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        color_previews = "\n".join([f"- **{name.capitalize()}:** `{code}`" for name, code in colors.items() if code])

        embed = disnake.Embed(
            title=f"Editor de Cores",
            description="Configure as cores utilizadas pelo seu Zenity Pro.",
            # timestamp=disnake.utils.utcnow()
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color
            
        embed.add_field(name="Cores Atuais:", value=color_previews or "Nenhuma cor definida.")
        # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Editar Cores", style=disnake.ButtonStyle.grey,
                                    emoji=emoji.edit, custom_id="Personalizacao_EditarCores_Modal"),
                disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey,
                                    emoji=emoji.arrow, custom_id="Personalizacao_VisualizarCores"),
                disnake.ui.Button(label="Paleta de Cores", style=disnake.ButtonStyle.link,
                                    url="https://htmlcolorcodes.com/"),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                                    emoji=emoji.back, custom_id="Painel_Personalizacao"),
            )
        ]
        return embed, components

    @staticmethod
    def get_preview_components(inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        
        components = []
        for name, code in colors.items():
            if not code:
                continue
            color_int = int(code.replace("#", ""), 16)
            container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"Esta é a cor **{name.capitalize()}** (`{code}`)"),
                accent_colour=disnake.Colour(color_int)
            )
            components.append(container)
        components.append(
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Personalizacao_VisualizarCores_Voltar")
            )
        )
        return components

    @staticmethod
    def get_preview_embed(inter: disnake.MessageInteraction):
        colors = db.get_document("custom_colors")
        
        embeds = []
        for name, code in colors.items():
            if not code:
                continue
            color_int = int(code.replace("#", ""), 16)
            embed = disnake.Embed(
                title=f"Cor {name.capitalize()}",
                description=f"Esta é a cor **{name.capitalize()}** (`{code}`)",
                color=color_int,
                # timestamp=disnake.utils.utcnow()
            )
            # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)
            embeds.append(embed)
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Personalizacao_VisualizarCores_Voltar")
            )
        ]
        return embeds, components
