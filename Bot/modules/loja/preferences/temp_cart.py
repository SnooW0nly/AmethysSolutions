"""
Aqui o usuario vai poder configurar o tempo padrão de expiração do carrinho em minutos que será aplicado globalmente a todos os carrinhos.
"""

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


def _get_prefs():
    prefs = db.get_document("loja_preferences") or {}
    if not isinstance(prefs, dict):
        prefs = {}
    # defaults
    prefs.setdefault("cart_duration_minutes", 30)
    prefs.setdefault("store_hours", "")
    prefs.setdefault("transcript_enabled", False)
    return prefs


class CartPreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        return CartPreferences._panel_embed(inter) if mode == "embed" else CartPreferences._panel_components(inter)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        prefs = _get_prefs()
        duration = int(prefs.get("cart_duration_minutes", 30))

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        options = [
            disnake.SelectOption(label=f"{m} minutos", value=str(m), default=(duration == m))
            for m in (10, 15, 20, 30, 45, 60, 90, 120)
        ]

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Preferências > **Tempo do Carrinho**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Defina o tempo padrão de expiração do carrinho.\n"
                    "Esse tempo é aplicado globalmente a todos os carrinhos."
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Loja_Pref_CartDuration_Select",
                        placeholder="Selecione a duração do carrinho",
                        options=options,
                        min_values=1,
                        max_values=1,
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Preferencias")
            )
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        prefs = _get_prefs()
        duration = int(prefs.get("cart_duration_minutes", 30))

        embed = disnake.Embed(
            title="Tempo do Carrinho",
            description=(
                "-# Painel > Loja > Preferências > **Tempo do Carrinho**\n\n"
                f"Duração atual: `{duration} minutos`\n"
                "Defina o tempo padrão de expiração do carrinho."
            )
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        options = [
            disnake.SelectOption(label=f"{m} minutos", value=str(m), default=(duration == m))
            for m in (10, 15, 20, 30, 45, 60, 90, 120)
        ]

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Loja_Pref_CartDuration_Select",
                    placeholder="Selecione a duração do carrinho",
                    options=options,
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Preferencias")
            )
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Pref_CartDuration_Select":
            value = inter.values[0]
            try:
                minutes = int(value)
            except Exception:
                await inter.response.send_message("Valor inválido.", ephemeral=True)
                return

            prefs = _get_prefs()
            prefs["cart_duration_minutes"] = minutes
            db.save_document("loja_preferences", prefs)

            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = CartPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))


def setup(bot: commands.Bot):
    bot.add_cog(CartPreferences(bot))
