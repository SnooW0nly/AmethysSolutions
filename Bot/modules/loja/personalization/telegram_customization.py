"""
Sistema de personalização das mensagens do bot do Telegram (/start e tals)
"""
import disnake
from functions.database import database as db
from functions.emoji import emoji

_DEFAULT_WELCOME   = "👤 *{nome}*\n🆔 `{id}`"
_DEFAULT_FINAL     = "O que deseja fazer?"
_DEFAULT_BTN_PROD  = "🛍️ Produtos"
_DEFAULT_BTN_SALDO = "💰 Saldo"
_DEFAULT_HEADER    = "🛍️ *Produtos disponíveis:*"


class TelegramCustomizationModal(disnake.ui.Modal):
    def __init__(self):
        data = db.get_document("loja_telegram_customization")

        components = [
            disnake.ui.TextInput(
                label="Mensagem de Boas-vindas",
                custom_id="welcome_message",
                value=data.get("welcome_message", _DEFAULT_WELCOME),
                placeholder="Use {nome} e {id} como variáveis",
                style=disnake.TextInputStyle.paragraph,
                max_length=500,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Texto Final (pergunta)",
                custom_id="final_text",
                value=data.get("final_text", _DEFAULT_FINAL),
                max_length=100,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Texto do Botão Produtos",
                custom_id="button_produtos_label",
                value=data.get("button_produtos_label", _DEFAULT_BTN_PROD),
                max_length=30,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Texto do Botão Saldo",
                custom_id="button_saldo_label",
                value=data.get("button_saldo_label", _DEFAULT_BTN_SALDO),
                max_length=30,
                required=True,
            ),
            disnake.ui.TextInput(
                label="Cabeçalho da Lista de Produtos",
                custom_id="produtos_header",
                value=data.get("produtos_header", _DEFAULT_HEADER),
                max_length=100,
                required=True,
            ),
        ]

        super().__init__(title="Personalizar Telegram", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(ephemeral=True)

        data = db.get_document("loja_telegram_customization")
        data["welcome_message"]       = inter.text_values["welcome_message"]
        data["final_text"]            = inter.text_values["final_text"]
        data["button_produtos_label"] = inter.text_values["button_produtos_label"]
        data["button_saldo_label"]    = inter.text_values["button_saldo_label"]
        data["produtos_header"]       = inter.text_values["produtos_header"]
        data["enabled"] = True

        db.save_document("loja_telegram_customization", data)

        await inter.followup.send(
            f"{emoji.correct} Mensagens do Telegram personalizadas com sucesso!",
            ephemeral=True
        )


class TelegramCustomizationSystem:
    """Painel de personalização das mensagens do bot do Telegram"""

    @staticmethod
    def panel(inter: disnake.Interaction) -> dict:
        mode = db.get_document("custom_mode").get("mode", "components")
        if mode == "embed":
            return TelegramCustomizationSystem._panel_embed(inter)
        return TelegramCustomizationSystem._panel_components(inter)

    @staticmethod
    def _panel_components(inter: disnake.Interaction) -> dict:
        data = db.get_document("loja_telegram_customization")

        color_data = db.get_document("custom_colors")
        primary_color_hex = color_data.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        status = f"{emoji.on} Ativado" if data.get("enabled") else f"{emoji.off} Desativado"

        config_text = (
            f"**Status:** {status}\n"
            f"**Boas-vindas:** {data.get('welcome_message', _DEFAULT_WELCOME)[:80]}\n"
            f"**Texto Final:** {data.get('final_text', _DEFAULT_FINAL)}\n"
            f"**Botão Produtos:** {data.get('button_produtos_label', _DEFAULT_BTN_PROD)}\n"
            f"**Botão Saldo:** {data.get('button_saldo_label', _DEFAULT_BTN_SALDO)}\n"
            f"**Cabeçalho Produtos:** {data.get('produtos_header', _DEFAULT_HEADER)}"
        )

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Loja > Personalizar > **Telegram**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Personalize as mensagens enviadas pelo bot do Telegram.\n"
                    "Use {nome} e {id} na mensagem de boas-vindas."
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(config_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Configurar",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.config,
                        custom_id="Loja_Telegram_Config"
                    ),
                    disnake.ui.Button(
                        label="Ativar" if not data.get("enabled") else "Desativar",
                        style=disnake.ButtonStyle.green if not data.get("enabled") else disnake.ButtonStyle.red,
                        emoji=emoji.on if not data.get("enabled") else emoji.off,
                        custom_id="Loja_Telegram_Toggle"
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Personalizar"
                )
            )
        ]}

    @staticmethod
    def _panel_embed(inter: disnake.Interaction):
        data = db.get_document("loja_telegram_customization")

        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Personalizar Telegram",
            description="Configure as mensagens do bot do Telegram",
            color=disnake.Color.from_rgb(0, 202, 164)
        )

        embed.add_field(
            name="Status",
            value=f"{emoji.on if data.get('enabled') else emoji.off} {'Ativado' if data.get('enabled') else 'Desativado'}",
            inline=True
        )
        embed.add_field(
            name="Botões",
            value=f"{data.get('button_produtos_label', _DEFAULT_BTN_PROD)} / {data.get('button_saldo_label', _DEFAULT_BTN_SALDO)}",
            inline=True
        )
        embed.add_field(
            name="Boas-vindas",
            value=data.get("welcome_message", _DEFAULT_WELCOME)[:200],
            inline=False
        )

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.config,
                    custom_id="Loja_Telegram_Config"
                ),
                disnake.ui.Button(
                    label="Ativar" if not data.get("enabled") else "Desativar",
                    style=disnake.ButtonStyle.green if not data.get("enabled") else disnake.ButtonStyle.red,
                    emoji=emoji.on if not data.get("enabled") else emoji.off,
                    custom_id="Loja_Telegram_Toggle"
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Personalizar"
                )
            )
        ]

        return embed, components
