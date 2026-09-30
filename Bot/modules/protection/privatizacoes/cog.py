import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message

PRIVATIZACOES_OPCOES = [
    ("privatizacao_cargos", "Privatização de Cargos", emoji.route, "Impede a atribuição de certos cargos manualmente."),
    ("privatizacao_permissoes", "Privatização de Permissões", emoji.shield, "Impede atribuição de permissões perigosas."),
    ("privatizacao_mencoes", "Privatização de Menções", emoji.role, "Impede que não autorizados usem @here ou @everyone."),
    ("privatizacao_aplicacoes", "Privatização de Aplicações", emoji.robot, "Impede adicionar bots ao servidor."),
    ("privatizacao_urls", "Privatização de URLs", emoji.website, "Impede o envio de links no servidor."),
    ("persistencia_canais", "Persistência de Canais", emoji.dir, "Restaura canais apagados automaticamente."),
]

class PrivatizacoesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def PainelComponents(inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)
        
        options = [
            disnake.SelectOption(label=label, value=custom_id, emoji=button_emoji, description=description)
            for custom_id, label, button_emoji, description in PRIVATIZACOES_OPCOES
        ]

        select_menu = disnake.ui.Select(
            placeholder="Selecione uma opção de privatização",
            options=options,
            custom_id="Privatizacao_Select"
        )
        
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > **Privatizações**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Gerencie as opções de privatizações do servidor.\nEscolha uma das opções abaixo para configurar:"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(select_menu),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Back_To_Protection_Panel"),
            )
        ]

    @staticmethod
    def PainelEmbed(inter: disnake.MessageInteraction):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        embed = disnake.Embed(
            title=f"Painel de Privatizações",
            description="Gerencie as opções de privatizações do servidor.\nEscolha uma das opções abaixo para configurar:",
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        options = [
            disnake.SelectOption(label=label, value=custom_id, emoji=button_emoji, description=description)
            for custom_id, label, button_emoji, description in PRIVATIZACOES_OPCOES
        ]

        select_menu = disnake.ui.Select(
            placeholder="Selecione uma opção de privatização",
            options=options,
            custom_id="Privatizacao_Select"
        )
        
        return embed, [
            disnake.ui.ActionRow(select_menu),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Back_To_Protection_Panel"),
            )
        ]

    async def display_privatizacoes_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        
        if mode == "embed":
            embed, components = self.PainelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(content=None, embed=None, components=self.PainelComponents(inter))

    @commands.Cog.listener("on_dropdown")
    async def privatizacao_dropdown_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "Privatizacao_Select":
            return
        
        await inter.response.defer()

        option_id = inter.values[0]
        cog_name_map = {
            "privatizacao_cargos": "PrivatizacaoCargosCog",
            "privatizacao_permissoes": "PrivatizacaoPermissoesCog",
            "privatizacao_mencoes": "PrivatizacaoMencoesCog",
            "privatizacao_aplicacoes": "PrivatizacaoAplicacoesCog",
            "privatizacao_urls": "PrivatizacaoURLsCog",
            "persistencia_canais": "PersistenciaCanaisCog",
        }
        cog_name = cog_name_map.get(option_id)

        if cog_name:
            cog = self.bot.get_cog(cog_name)
            if cog and hasattr(cog, 'display_panel'):
                await cog.display_panel(inter)
            else:
                await inter.followup.send(f"O módulo para '{option_id.replace('_', ' ').title()}' ainda não foi implementado.", ephemeral=True)
        else:
            await inter.followup.send(f"Opção '{option_id}' não encontrada.", ephemeral=True)

    @commands.Cog.listener("on_button_click")
    async def privatizacoes_button_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Privatizacoes_Panel":
            await self.display_privatizacoes_panel(inter)

def setup(bot: commands.Bot):
    bot.add_cog(PrivatizacoesCog(bot))
