"""
Sistema de notificação de restock
Quando estoque é adicionado, envia mensagem no canal configurado com info do produto/campo
"""

import disnake
from disnake.ext import commands
from datetime import datetime

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


# ---------------------------------------------------------------------------
# Painel de preferências
# ---------------------------------------------------------------------------

class RestockNotifyPreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Helpers de config
    # ------------------------------------------------------------------

    @staticmethod
    def _get_config() -> dict:
        prefs = db.get_document("loja_preferences") or {}
        return prefs.get("restock_notify") or {}

    @staticmethod
    def _save_config(data: dict) -> None:
        prefs = db.get_document("loja_preferences") or {}
        if not isinstance(prefs, dict):
            prefs = {}
        prefs["restock_notify"] = data
        db.save_document("loja_preferences", prefs)

    # ------------------------------------------------------------------
    # Panel builders
    # ------------------------------------------------------------------

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        return (
            RestockNotifyPreferences._panel_embed(inter)
            if mode == "embed"
            else RestockNotifyPreferences._panel_components(inter)
        )

    @staticmethod
    def _build_status_text(cfg: dict, guild: disnake.Guild | None) -> str:
        enabled = cfg.get("enabled", False)
        channel_id = cfg.get("channel_id")

        status_icon = emoji.correct if enabled else emoji.wrong
        status_label = "Ativado" if enabled else "Desativado"

        channel_mention = "Não configurado"
        if channel_id and guild:
            ch = guild.get_channel(int(channel_id))
            channel_mention = ch.mention if ch else f"<#{channel_id}>"
        elif channel_id:
            channel_mention = f"<#{channel_id}>"

        return (
            f"-# Status: {status_icon} **{status_label}**\n"
            f"-# Canal de restock: {channel_mention}"
        )

    @staticmethod
    def _can_enable(cfg: dict) -> bool:
        return bool(cfg.get("channel_id"))

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(
                int(primary_color_hex.replace("#", ""), 16)
            )

        cfg = RestockNotifyPreferences._get_config()
        enabled = cfg.get("enabled", False)
        can_enable = RestockNotifyPreferences._can_enable(cfg)

        status_text = RestockNotifyPreferences._build_status_text(cfg, inter.guild)

        toggle_label = "Desativar" if enabled else "Ativar"
        toggle_style = disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green
        toggle_emoji = emoji.wrong if enabled else emoji.correct

        return {
            "components": [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(
                        f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                        f"-# Painel > Loja > Preferências > **Notificar Restock**"
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(
                        "Configure o canal onde serão enviadas as notificações automáticas "
                        "sempre que novo estoque for adicionado a um produto."
                    ),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(status_text),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label=toggle_label,
                            style=toggle_style,
                            emoji=toggle_emoji,
                            custom_id="RestockNotify_Toggle",
                            disabled=not can_enable,
                        ),
                        disnake.ui.Button(
                            label="Configurar Canal",
                            style=disnake.ButtonStyle.blurple,
                            emoji=emoji.settings2,
                            custom_id="RestockNotify_SetChannel",
                        ),
                    ),
                    **container_kwargs,
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Voltar",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.back,
                        custom_id="Loja_Preferencias",
                    )
                ),
            ]
        }

    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")

        cfg = RestockNotifyPreferences._get_config()
        enabled = cfg.get("enabled", False)
        can_enable = RestockNotifyPreferences._can_enable(cfg)

        status_text = RestockNotifyPreferences._build_status_text(cfg, inter.guild)

        embed = disnake.Embed(
            title="Notificar Restock",
            description=(
                "-# Painel > Loja > Preferências > **Notificar Restock**\n\n"
                "Configure o canal onde serão enviadas as notificações automáticas "
                "sempre que novo estoque for adicionado a um produto.\n\n"
                + status_text
            ),
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        toggle_label = "Desativar" if enabled else "Ativar"
        toggle_style = disnake.ButtonStyle.red if enabled else disnake.ButtonStyle.green
        toggle_emoji = emoji.wrong if enabled else emoji.correct

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=toggle_label,
                    style=toggle_style,
                    emoji=toggle_emoji,
                    custom_id="RestockNotify_Toggle",
                    disabled=not can_enable,
                ),
                disnake.ui.Button(
                    label="Configurar Canal",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.settings2,
                    custom_id="RestockNotify_SetChannel",
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Loja_Preferencias",
                )
            ),
        ]
        return {"embed": embed, "components": components}

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        # ---- Painel principal ----
        if custom_id == "RestockNotify_Panel":
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = RestockNotifyPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(
                    **panel, flags=disnake.MessageFlags(is_components_v2=True)
                )

        # ---- Toggle on/off ----
        elif custom_id == "RestockNotify_Toggle":
            cfg = RestockNotifyPreferences._get_config()
            if not RestockNotifyPreferences._can_enable(cfg):
                await inter.response.send_message(
                    f"{emoji.wrong} Configure um canal antes de ativar!",
                    ephemeral=True,
                )
                return

            cfg["enabled"] = not cfg.get("enabled", False)
            RestockNotifyPreferences._save_config(cfg)

            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = RestockNotifyPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(
                    **panel, flags=disnake.MessageFlags(is_components_v2=True)
                )

        # ---- Configurar Canal ----
        elif custom_id == "RestockNotify_SetChannel":
            await inter.response.send_modal(RestockNotifyChannelModal())


# ---------------------------------------------------------------------------
# Modal – seleção de canal
# ---------------------------------------------------------------------------

class RestockNotifyChannelModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.Label(
                text="Selecione o Canal de Restock",
                component=disnake.ui.ChannelSelect(
                    placeholder="Escolha um canal de texto",
                    custom_id="restock_notify_channel_select",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                ),
                description="As notificações de restock serão enviadas neste canal.",
            ),
        ]
        super().__init__(
            title="Configurar Canal de Restock",
            components=components,
            custom_id="restock_notify_channel_modal",
        )

    async def callback(self, inter: disnake.ModalInteraction):
        try:
            valores = inter.resolved_values
            selected = valores.get("restock_notify_channel_select")

            # Normalizar para int
            if isinstance(selected, (list, tuple)):
                selected = selected[0] if selected else None
            if isinstance(selected, (str, int)):
                channel_id = int(selected)
            elif hasattr(selected, "id"):
                channel_id = int(selected.id)
            else:
                await inter.response.send_message(
                    f"{emoji.wrong} Canal inválido!", ephemeral=True
                )
                return

            channel = inter.guild.get_channel(channel_id)
            if not channel:
                await inter.response.send_message(
                    f"{emoji.wrong} Canal não encontrado!", ephemeral=True
                )
                return

            # Salvar
            cfg = RestockNotifyPreferences._get_config()
            cfg["channel_id"] = channel_id
            RestockNotifyPreferences._save_config(cfg)

            # Atualizar painel
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = RestockNotifyPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(
                    **panel, flags=disnake.MessageFlags(is_components_v2=True)
                )

        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"{emoji.wrong} Erro ao processar: {str(e)}", ephemeral=True
                )


# ---------------------------------------------------------------------------
# Função pública chamada por adicionar.py
# ---------------------------------------------------------------------------

async def notify_restock(
    bot: commands.Bot,
    product_id: str,
    field_id: str,
    items_added: int,
) -> None:
    """
    Envia a notificação de restock no canal configurado.
    Chamada após adicionar estoque em adicionar.py.

    Parâmetros
    ----------
    bot         : instância do bot
    product_id  : ID do produto
    field_id    : ID do campo que recebeu estoque
    items_added : quantidade de itens adicionados nesta operação
    """
    try:
        cfg = RestockNotifyPreferences._get_config()
        if not cfg.get("enabled"):
            return

        channel_id = cfg.get("channel_id")
        if not channel_id:
            return

        channel = bot.get_channel(int(channel_id))
        if not channel:
            return

        # Dados do produto/campo
        from functions.database import database as db_inner
        products = db_inner.get_document("loja_products") or {}
        product = products.get(product_id) or {}
        product_name = product.get("name") or product_id
        campo = (product.get("campos") or {}).get(field_id) or {}
        campo_name = campo.get("name") or field_id

        # Estoque total atual
        from modules.loja.cart.stock_manager import StockManager
        is_infinite = campo.get("infinite_stock", {}).get("enabled", False)
        if is_infinite:
            total_stock = "Infinito"
        else:
            total_stock = str(StockManager.get_available_stock(product_id, field_id))

        # Data formatada
        now = datetime.utcnow()
        data_fmt = now.strftime("%d/%m/%Y às %H:%M") + " UTC"

        # Montar mensagem
        msg_content = (
            f"## {emoji.cardbox} **RESTOCK!** O produto **{product_name}** acabou de receber novos itens!\n\n"
            f"-# {emoji.chevron_arrow} **Campo:** __`{campo_name}`__\n"
            f"-# {emoji.chevron_arrow} **Adicionados:** __`{items_added}x`__\n"
            f"-# {emoji.chevron_arrow} **Estoque total:** __`{total_stock}`__\n"
            f"-# {emoji.chevron_arrow} **Data:** __{data_fmt}__\n\n"
            f"-# ||@everyone||"
        )

        await channel.send(msg_content)

    except Exception:
        # Notificação nunca deve quebrar o fluxo principal
        pass


def setup(bot: commands.Bot):
    bot.add_cog(RestockNotifyPreferences(bot))