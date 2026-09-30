import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message

PROTECAO_OPCOES = [
    ("protecao_canais", "Proteção de Canais", emoji.textc, "Contra criação, exclusão e edição em massa de canais."),
    ("protecao_cargos", "Proteção dos Cargos", emoji.role, "Contra criação, exclusão e edição em massa de cargos."),
    ("protecao_webhooks", "Proteção de Webhooks", emoji.web, "Contra criação e spam em massa de webhooks."),
    ("protecao_comandos_externos", "Proteção de Comandos Externos", emoji.robot, "Previne spam de mensagens de bots externos."),
    ("protecao_banimentos", "Proteção de Banimentos", emoji.ban, "Previne banimentos em massa de membros."),
    ("protecao_expulsoes", "Proteção de Expulsões em Massa", emoji.group, "Previne expulsões em massa de membros."),
    ("protecao_comandos_canais", "Proibir Comandos Externos", emoji.robot, "Bloqueia comandos externos em todos os canais."),
    ("protecao_url", "Proteção de URL", emoji.link, "Protege a URL personalizada (vanity) do servidor."),
    ("protecao_incident_actions", "Incident Actions", emoji.shield, "Bloqueia DMs e Invites temporariamente."),
    ("protecao_imagens_mrbeast", "Proteção MrBeast", emoji.image, "Bloqueia spam de imagens MrBeast de selfbots."),
]

class ProtectionGeralCog(commands.Cog):
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
        
        options = []
        for custom_id, label, button_emoji, description in PROTECAO_OPCOES:
            options.append(disnake.SelectOption(label=label, value=custom_id, emoji=button_emoji, description=description))

        select_menu = disnake.ui.Select(
            placeholder="Selecione uma opção de proteção",
            options=options,
            custom_id="Protecao_Geral_Select"
        )
        
        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > **Proteção Geral**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Gerencie as opções de proteção geral do servidor.\nEscolha uma das opções abaixo para configurar:"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(select_menu),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Back_To_Protection_Panel"),
            )
        ]
        return components

    @staticmethod
    def PainelEmbed(inter: disnake.MessageInteraction):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        embed = disnake.Embed(
            title=f"Painel de Proteção Geral",
            description="Gerencie as opções de proteção geral do servidor.\nEscolha uma das opções abaixo para configurar:",
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color

        options = [
            disnake.SelectOption(label=label, value=custom_id, emoji=button_emoji, description=description)
            for custom_id, label, button_emoji, description in PROTECAO_OPCOES
        ]

        select_menu = disnake.ui.Select(
            placeholder="Selecione uma opção de proteção",
            options=options,
            custom_id="Protecao_Geral_Select"
        )
        
        components = [
            disnake.ui.ActionRow(select_menu),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Back_To_Protection_Panel"),
            )
        ]
        return embed, components

    async def display_protecao_geral_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        
        if mode == "embed":
            embed, components = self.PainelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(content=None, embed=None, components=self.PainelComponents(inter))

    @commands.Cog.listener("on_dropdown")
    async def protecao_geral_dropdown_listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "Protecao_Geral_Select":
            return
        
        await inter.response.defer()

        protection_id = inter.values[0]
        protection_cog_name = {
            "protecao_canais": "CanaisCog",
            "protecao_cargos": "CargosCog",
            "protecao_webhooks": "WebhooksCog",
            "protecao_comandos_externos": "ComandosExtCog",
            "protecao_banimentos": "BanimentosCog",
            "protecao_expulsoes": "ExpulsoesCog",
            "protecao_comandos_canais": "ComandosCanaisCog",
            "protecao_url": "ProtecaoUrlCog",
            "protecao_incident_actions": "IncidentActionsCog",
            "protecao_imagens_mrbeast": "ImagensMrBeastCog",
        }.get(protection_id)

        if protection_cog_name:
            protection_cog = self.bot.get_cog(protection_cog_name)
            if protection_cog and hasattr(protection_cog, 'display_panel'):
                await protection_cog.display_panel(inter)
            else:
                await inter.followup.send(f"O módulo de proteção para '{protection_id.replace('_', ' ').title()}' ainda não foi implementado.", ephemeral=True)
        else:
            await inter.followup.send(f"Opção de proteção '{protection_id}' não encontrada.", ephemeral=True)


def setup(bot: commands.Bot):
    bot.add_cog(ProtectionGeralCog(bot))
