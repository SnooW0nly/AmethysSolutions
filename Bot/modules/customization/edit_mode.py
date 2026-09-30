import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message

class EditMode:
    @staticmethod
    def mode_change_components(inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        mode = db.get_document("custom_mode").get("mode")
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > **Personalização**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Selecione o modo de exibição desejado para o bot.\n"
                    "Você pode alterar para **Embeds** ou **Containers.**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**Modo de exibição atual:** {"`Embeds`" if mode == "embed" else "`Containers`"}"),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        placeholder="Selecione o modo de exibição",
                        custom_id="Personalizacao_EditarModoExibicao",
                        options=[
                            disnake.SelectOption(label="Componentes V1", value="embed", description="Modo de exibição antigo ― Embed", default=mode == "embed", emoji=emoji.embed),
                            disnake.SelectOption(label="Componentes V2", value="components", description="Modo de exibição novo ― Containers", default=mode == "components", emoji=emoji.commands),
                        ]
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                                  emoji=emoji.back, custom_id="Painel_Personalizacao"),
            )
        ]

    @staticmethod
    def mode_change_embed(inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        embed = disnake.Embed(
            title=f"Modo de Exibição",
            description="Selecione o modo de exibição desejado para o bot.\nVocê pode alterar para **Embeds** ou **Containers.**",
            # timestamp=disnake.utils.utcnow()
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color

        embed.add_field(
            name="Modo de exibição atual:",
            value=f"{'`Embeds`' if mode == 'embed' else '`Containers`'}"
        )
        # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    placeholder="Selecione o modo de exibição",
                    custom_id="Personalizacao_EditarModoExibicao",
                    options=[
                        disnake.SelectOption(label="Embeds", value="embed", description="Modo de exibição antigo ― Embed", default=mode == "embed", emoji=emoji.embed),
                        disnake.SelectOption(label="Containers", value="components", description="Modo de exibição novo ― Containers", default=mode == "components", emoji=emoji.commands),
                    ]
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey,
                                  emoji=emoji.back, custom_id="Painel_Personalizacao"),
            )
        ]
        return embed, components