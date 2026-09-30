import disnake
from functions.emoji import emoji
from functions.database import database as db
from disnake.ext import commands
from functions.message import message as Message

class PermsInternas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    PERMS_OPCOES = [
        ("perms_gerar_pagamento", "Quem pode usar /gerar_pagamento", emoji.card, "Define quem pode gerar pagamentos pelo bot."),
        ("perms_entregar", "Quem pode usar /entregar", emoji.truck, "Define quem pode entregar produtos ou assinaturas."),
        ("perms_tickets_lembrar", "Quem pode usar /ticket_lembrar", emoji.ticket, "Define quem pode lembrar usuarios nos tickets."),
        ("perms_tickets_fechar", "Quem pode usar /ticket_fechar", emoji.ticket, "Define quem pode fechar tickets."),
        ("perms_tickets_arquivar", "Quem pode usar /ticket_arquivar", emoji.ticket, "Define quem pode arquivar tickets.")
    ]

    async def display_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            embed, components = self.PainelPermsInternasEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.PainelPermsInternasComponents(inter)
            await inter.edit_original_message(components=components)

    @staticmethod
    def PainelPermsInternasComponents(inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        options = [
            disnake.SelectOption(
                label=label,
                value=key,
                emoji=e,
                description=desc
            ) for key, label, e, desc in PermsInternas.PERMS_OPCOES
        ]
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > **Permissões Internas**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Gerencie quem pode usar comandos internos do bot. \nSelecione uma opção abaixo para configurar:"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Escolha o comando para configurar",
                        options=options,
                        custom_id="PermsInternasSelectMenu"
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protection"),
            )
        ]

    @staticmethod
    def PainelPermsInternasEmbed(inter: disnake.MessageInteraction):
        options = [
            disnake.SelectOption(
                label=label,
                value=key,
                emoji=e,
                description=desc
            ) for key, label, e, desc in PermsInternas.PERMS_OPCOES
        ]
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        embed = disnake.Embed(
            title=f"Painel de Permissões Internas",
            description="Gerencie quem pode usar comandos internos do bot. \nSelecione uma opção abaixo para configurar:",
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Escolha o comando para configurar",
                    options=options,
                    custom_id="PermsInternasSelectMenu"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protection"),
            )
        ]
        return embed, components

    @staticmethod
    def PainelEscolherPermsInternas(inter: disnake.MessageInteraction, perms_key) -> list[disnake.ui.Container]:
        label = next(label for key, label, *_ in PermsInternas.PERMS_OPCOES if key == perms_key)
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Permissões Internas > **{label}**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Configuração de {label} (em breve)"),
                disnake.ui.Separator(),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_PermissoesInternas"),
            )
        ]

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "PermsInternasSelectMenu":
            perms_key = inter.values[0]
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelEscolherPermsInternas(inter, perms_key))

def setup(bot: commands.Bot):
    bot.add_cog(PermsInternas(bot))
