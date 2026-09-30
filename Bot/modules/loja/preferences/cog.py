"""
Aqui nesse painel vai ficar um select com todas as preferencias que da pra configurar igual no modules/tickets que tem o sistema de preferencias legal e organizado.
"""

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class PreferenciasLoja(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        return PreferenciasLoja._panel_embed(inter) if mode == "embed" else PreferenciasLoja._panel_components(inter)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        options = [
            disnake.SelectOption(label="Tempo do Carrinho", value="cart", emoji=emoji.clock, description="Defina o tempo padrão do carrinho"),
            disnake.SelectOption(label="Horário de Funcionamento", value="hours", emoji=emoji.calendar, description="Defina o horário de funcionamento da loja"),
            disnake.SelectOption(label="Manutenção", value="maintenance", emoji=emoji.settings2, description="Ative ou desative a manutenção da loja"),
            disnake.SelectOption(label="Solicitar Estoque", value="stock_requests", emoji=emoji.cardbox, description="Configure solicitações de estoque"),
            disnake.SelectOption(label="Notificar Restock", value="restock_notify", emoji=emoji.warn, description="Notifique um canal ao adicionar estoque"),
            disnake.SelectOption(label="Termos da Loja", value="terms", emoji=emoji.receipt, description="Configure os termos que usuários precisam aceitar"),
            disnake.SelectOption(label="Transcript de Carrinhos", value="transcripts", emoji=emoji.double_speech, description="Ative ou desative o transcript"),
            disnake.SelectOption(label="5 Estrelas", value="cinco_estrelas", emoji=emoji.star, description="Sistema de avaliação de compras por estrelas"),
            disnake.SelectOption(label="Recompensa por Feedback", value="recompensa_feedback", emoji=emoji.gift, description="Recompense clientes que deixam feedback"),
            disnake.SelectOption(label="Ranking Público", value="ranking_publico", emoji=emoji.star, description="Exiba um ranking público dos melhores clientes"),
        ]

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > **Preferências**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Gerencie as preferências globais da sua loja."),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Loja_Preferencias_Select",
                        placeholder="Selecione uma preferência para configurar",
                        options=options
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Loja")
            )
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        embed = disnake.Embed(
            title="Preferências da Loja",
            description=(
                "-# Painel > Loja > **Preferências**\n\n"
                "Gerencie as preferências globais da sua loja."
            )
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        options = [
            disnake.SelectOption(label="Tempo do Carrinho", value="cart", emoji=emoji.clock, description="Defina o tempo padrão do carrinho"),
            disnake.SelectOption(label="Horário de Funcionamento", value="hours", emoji=emoji.calendar, description="Defina o horário de funcionamento da loja"),
            disnake.SelectOption(label="Manutenção", value="maintenance", emoji=emoji.settings2, description="Ative ou desative a manutenção da loja"),
            disnake.SelectOption(label="Solicitar Estoque", value="stock_requests", emoji=emoji.cardbox, description="Configure solicitações de estoque"),
            disnake.SelectOption(label="Notificar Restock", value="restock_notify", emoji=emoji.warn, description="Notifique um canal ao adicionar estoque"),
            disnake.SelectOption(label="Termos da Loja", value="terms", emoji=emoji.receipt, description="Configure os termos que usuários precisam aceitar"),
            disnake.SelectOption(label="Transcript de Carrinhos", value="transcripts", emoji=emoji.double_speech, description="Ative ou desative o transcript"),
            disnake.SelectOption(label="5 Estrelas", value="cinco_estrelas", emoji=emoji.star, description="Sistema de avaliação de compras por estrelas"),
            disnake.SelectOption(label="Recompensa por Feedback", value="recompensa_feedback", emoji=emoji.gift, description="Recompense clientes que deixam feedback"),
            disnake.SelectOption(label="Ranking Público", value="ranking_publico", emoji=emoji.star, description="Exiba um ranking público dos melhores clientes"),
        ]

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Loja_Preferencias_Select",
                    placeholder="Selecione uma preferência para configurar",
                    options=options
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Painel_Loja")
            )
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Preferencias":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = PreferenciasLoja.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Preferencias_Select":
            value = inter.values[0]
            mode = db.get_document("custom_mode").get("mode")
            
            # Defer a resposta primeiro
            await inter.response.defer()

            try:
                if value == "cart":
                    from .temp_cart import CartPreferences
                    panel = CartPreferences.panel(inter)
                elif value == "hours":
                    from .horario import StoreHoursPreferences
                    panel = StoreHoursPreferences.panel(inter)
                elif value == "maintenance":
                    from .manutencao import MaintenancePreferences
                    panel = MaintenancePreferences.panel(inter)
                elif value == "stock_requests":
                    from .solicitar_estoque import StockRequestPreferences
                    panel = StockRequestPreferences.panel(inter)
                elif value == "restock_notify":
                    from .notificar_restock import RestockNotifyPreferences
                    panel = RestockNotifyPreferences.panel(inter)
                elif value == "terms":
                    from .terms import TermsPreferences
                    panel = TermsPreferences.panel(inter)
                elif value == "transcripts":
                    from .transcripts import TranscriptsPreferences
                    panel = TranscriptsPreferences.panel(inter)
                elif value == "cinco_estrelas":
                    from .cinco_estrelas import CincoEstrelasPreferences
                    panel = CincoEstrelasPreferences.panel(inter)
                elif value == "recompensa_feedback":
                    from .recompensa_feedback import RecompensaFeedbackPreferences
                    panel = RecompensaFeedbackPreferences.panel(inter)
                elif value == "ranking_publico":
                    from .ranking_publico import RankingPublicoPreferences
                    panel = RankingPublicoPreferences.panel(inter)
                else:
                    panel = PreferenciasLoja.panel(inter)

                # Verificar o tipo de retorno do painel
                if "embed" in panel:
                    await inter.edit_original_message(content=None, **panel)
                elif "components" in panel:
                    await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
                else:
                    await inter.edit_original_message(**panel)
            except Exception as e:
                # Em caso de erro, voltar ao painel principal silenciosamente
                try:
                    panel = PreferenciasLoja.panel(inter)
                    if "embed" in panel:
                        await inter.edit_original_message(content=None, **panel)
                    else:
                        await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
                except Exception as e2:
                    await inter.followup.send(
                        f"{emoji.wrong} Erro ao carregar painel: {str(e2)}",
                        ephemeral=True
                    )


def setup(bot: commands.Bot):
    bot.add_cog(PreferenciasLoja(bot))