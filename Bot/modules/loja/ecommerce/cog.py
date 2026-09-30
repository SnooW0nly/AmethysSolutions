"""
Amethys Marketplace — Painel principal
"""
import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from .service import MarketplaceService


class EcommerceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def get_panel_data(self, inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode", "components")
        return self._build_embed() if mode == "embed" else self._build_components()

    # ── Builders ──────────────────────────────────────────────────────────────

    @staticmethod
    def _build_components() -> dict:
        color_data = db.get_document("custom_colors") or {}
        primary_color_hex = color_data.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.basket} — Amethys Marketplace\n"
                        f"-# Painel > **Amethys Marketplace**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        "Vincule este bot a uma loja da plataforma Amethys para integrar "
                        "seus produtos, pagamentos e entregas.\n\n"
                        "Clique em **Vincular Loja** para gerar um código temporário e "
                        "use-o em **[amethys.shop/dashboard](https://amethys.shop/dashboard)** "
                        "na seção **Configurações → Token do Bot**."
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Vincular Loja",
                            emoji="🔗",
                            style=disnake.ButtonStyle.blurple,
                            custom_id="Marketplace_VincularLoja",
                        ),
                    ),
                    **container_kwargs,
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Painel_Loja",
                    )
                ),
            ]
        }

    @staticmethod
    def _build_embed() -> dict:
        color_data = db.get_document("custom_colors") or {}
        primary_color_hex = color_data.get("primary")
        embed_kwargs = {}
        if primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

        embed = disnake.Embed(
            description=(
                "-# Painel > **Amethys Marketplace**\n\n"
                "Vincule este bot a uma loja da plataforma Amethys para integrar "
                "seus produtos, pagamentos e entregas.\n\n"
                "Clique em **Vincular Loja** para gerar um código temporário e "
                "use-o em [amethys.shop/dashboard](https://amethys.shop/dashboard) "
                "na seção **Configurações → Token do Bot**."
            ),
            **embed_kwargs,
        )
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Vincular Loja",
                    emoji="🔗",
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Marketplace_VincularLoja",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Painel_Loja",
                )
            ),
        ]
        return {"embed": embed, "components": components}

    # ── Listener ───────────────────────────────────────────────────────────────

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "Marketplace_VincularLoja":
            return

        bot_id = str(self.bot.user.id)
        ok, data, err = await MarketplaceService.generate_link_code(bot_id)
        if not ok:
            await inter.response.send_message(
                f"{emoji.wrong} Não foi possível gerar o código: {err}",
                ephemeral=True,
            )
            return

        code = data.get("code", "???")
        expires_at = data.get("expires_at", "")

        import datetime
        try:
            exp = datetime.datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            exp_str = f"<t:{int(exp.timestamp())}:R>"
        except Exception:
            exp_str = "em 10 minutos"

        await inter.response.send_message(
            f"## 🔗 Código de Vinculação\n"
            f"Use este código no painel da plataforma para vincular sua loja a este bot.\n\n"
            f"```\n{code}\n```\n"
            f"-# Válido {exp_str} — acesse **amethys.shop/dashboard** → Configurações → Token do Bot.",
            ephemeral=True,
        )


def setup(bot: commands.Bot):
    bot.add_cog(EcommerceCog(bot))