from disnake.ext import commands
import disnake

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .listar import CARGOS_OPCOES

class ConfigurarCargos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def cargos_components(inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        definicoes = db.get_document("cargos") or {}
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        guild = inter.guild
        options = []

        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        for key, label, emoji_icon in CARGOS_OPCOES:
            nome = "Não definido"
            cargo = None

            cargo_id = definicoes.get(key)
            if guild and cargo_id:
                try:
                    cargo = guild.get_role(int(cargo_id))
                except (TypeError, ValueError):
                    cargo = None

            if cargo:
                base = cargo.name[:25] + ("..." if len(cargo.name) > 25 else "")
                nome = f"{base} ({cargo.id})"

            options.append(
                disnake.SelectOption(
                    label=label,
                    value=key,
                    emoji=emoji_icon,
                    description=f"Cargo atual: {nome}",
                )
            )

        def chunks(seq, n=25):
            for i in range(0, len(seq), n):
                yield seq[i:i+n]

        select_rows = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Escolha o cargo para configurar",
                    options=chunk,
                    custom_id=f"Configuracoes_EditarCargo:{i}",
                )
            )
            for i, chunk in enumerate(chunks(options, 25))
        ]

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Configurações > **Cargos**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Utilize o painel para gerenciar os cargos do servidor.\n"
                    "Você pode criar também os cargos automaticamente."
                ),
                disnake.ui.Separator(),
                *select_rows,
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Criar os cargos automaticamente",
                        emoji=emoji.wand,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Configuracoes_CriarTodosCargos",
                    ),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Painel_Configuracoes")
            ),
        ]

    @staticmethod
    def cargos_embed(inter: disnake.MessageInteraction):
        definicoes = db.get_document("cargos") or {}
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        guild = inter.guild
        options = []

        for key, label, emoji_icon in CARGOS_OPCOES:
            nome = "Não definido"
            cargo = None

            cargo_id = definicoes.get(key)
            if guild and cargo_id:
                try:
                    cargo = guild.get_role(int(cargo_id))
                except (TypeError, ValueError):
                    cargo = None

            if cargo:
                base = cargo.name[:25] + ("..." if len(cargo.name) > 25 else "")
                nome = f"{base} ({cargo.id})"

            options.append(
                disnake.SelectOption(
                    label=label,
                    value=key,
                    emoji=emoji_icon,
                    description=f"Cargo atual: {nome}",
                )
            )

        def chunks(seq, n=25):
            for i in range(0, len(seq), n):
                yield seq[i:i+n]

        select_rows = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Escolha o cargo para configurar",
                    options=chunk,
                    custom_id=f"Configuracoes_EditarCargo:{i}",
                )
            )
            for i, chunk in enumerate(chunks(options, 25))
        ]

        embed = disnake.Embed(
            title=f"Cargos",
            description="Utilize o painel para gerenciar os cargos do servidor.\nVocê pode criar também os cargos automaticamente.",
            # timestamp=disnake.utils.utcnow()
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color

        # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)

        components = [
            *select_rows,
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Criar os cargos automaticamente",
                    emoji=emoji.wand,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Configuracoes_CriarTodosCargos",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Painel_Configuracoes")
            ),
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Configuracoes_EditarCargos":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.cargos_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.cargos_components(inter))