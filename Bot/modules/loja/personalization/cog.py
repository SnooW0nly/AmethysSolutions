"""
Painel de personalização da loja
"""
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


async def sync_all_products_silently(bot: commands.Bot):
    """Sincroniza as mensagens de todos os produtos após mudança global (ex: toggle do botão de dúvidas)"""
    try:
        from modules.loja.products.product.edit import sync_product_messages_silently
        products = db.get_document("loja_products")
        if not products:
            return
        for product_id in products.keys():
            await sync_product_messages_silently(bot, product_id)
    except Exception:
        pass


class PersonalizarLoja(commands.Cog):
    """Painel de personalização da loja"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        """Retorna o painel de personalização"""
        mode = db.get_document("custom_mode").get("mode", "components")
        
        if mode == "embed":
            return PersonalizarLoja._panel_embed(inter)
        else:
            return PersonalizarLoja._panel_components(inter)
    
    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        """Painel em modo components v2"""
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > **Personalizar**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Personalize a experiência da sua loja.\n"
                    "Configure mensagens, marca e muito mais."
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Mensagens",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.message,
                        custom_id="Loja_Personalizar_Mensagens"
                    ),
                    disnake.ui.Button(
                        label="Botão de Dúvidas",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.interrogation,
                        custom_id="Loja_Personalizar_DoubtButton"
                    ),
                    disnake.ui.Button(
                        label="QR Code",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.mobile,
                        custom_id="Loja_Personalizar_QRCode",
                        disabled=False
                    ),
                    disnake.ui.Button(
                        label="Logs de Vendas",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.edit,
                        custom_id="Loja_Personalizar_SalesLogs"
                    ),
                    disnake.ui.Button(
                        label="Telegram",
                        style=disnake.ButtonStyle.grey,
                        emoji=emoji.message,
                        custom_id="Loja_Personalizar_Telegram"
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Painel_Loja"
                )
            )
        ]}
    
    @staticmethod
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        """Painel em modo embed"""
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        embed_kwargs = {}
        if primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
        
        embed = disnake.Embed(
            title="Personalizar Loja",
            description=(
                "-# Painel > Loja > **Personalizar**\n\n"
                "Personalize a experiência da sua loja.\n"
                "Configure mensagens, marca e muito mais."
            ),
            **embed_kwargs
        )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Mensagens",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.message,
                    custom_id="Loja_Personalizar_Mensagens"
                ),
                disnake.ui.Button(
                    label="Botão de Dúvidas",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.interrogation,
                    custom_id="Loja_Personalizar_DoubtButton"
                ),
                disnake.ui.Button(
                    label="QR Code",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.mobile,
                    custom_id="Loja_Personalizar_QRCode",
                    disabled=True
                ),
                disnake.ui.Button(
                    label="Logs de Vendas",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.edit,
                    custom_id="Loja_Personalizar_SalesLogs"
                ),
                disnake.ui.Button(
                    label="Telegram",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.message,
                    custom_id="Loja_Personalizar_Telegram"
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Painel_Loja"
                )
            )
        ]
        
        return {"embed": embed, "components": components}
    
    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Personalizar":
            mode = db.get_document("custom_mode").get("mode")
            
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = self.panel(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_Personalizar_DoubtButton":
            from .doubt_button import DoubtButtonSystem
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = DoubtButtonSystem.panel_doubt_button(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_Personalizar_QRCode":
            from .qr_customization import QRCodeGenerator
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = QRCodeGenerator.panel(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_DoubtButton_Config":
            from .doubt_button import DoubtButtonModal
            await inter.response.send_modal(DoubtButtonModal())
        
        elif inter.component.custom_id == "Loja_DoubtButton_Toggle":
            data = db.get_document("loja_doubt_button")
            data["enabled"] = not data.get("enabled", False)
            db.save_document("loja_doubt_button", data)
            
            # Sincronizar todas as mensagens de todos os produtos
            await sync_all_products_silently(self.bot)
            
            from .doubt_button import DoubtButtonSystem
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = DoubtButtonSystem.panel_doubt_button(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_QRCode_Config":
            from .qr_customization import QRCustomizationModal
            await inter.response.send_modal(QRCustomizationModal())
        
        elif inter.component.custom_id == "Loja_QRCode_Toggle":
            data = db.get_document("loja_qr_customization")
            data["enabled"] = not data.get("enabled", False)
            db.save_document("loja_qr_customization", data)
            
            from .qr_customization import QRCodeGenerator
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = QRCodeGenerator.panel(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_QRCode_Test":
            from .qr_customization import QRCodeGenerator
            
            await inter.response.defer(ephemeral=True)
            
            qr_bytes = await QRCodeGenerator.generate_custom_qr("https://amethys.solutions/")
            
            if qr_bytes:
                import io
                file = disnake.File(io.BytesIO(qr_bytes), filename="qr_test.png")
                await inter.followup.send(
                    f"{emoji.correct} QR Code de teste gerado!",
                    file=file,
                    ephemeral=True
                )
            else:
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao gerar QR Code de teste!",
                    ephemeral=True
                )
        
        elif inter.component.custom_id == "Loja_Personalizar_SalesLogs":
            from .sales_logs_customization import SalesLogsSystem
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = SalesLogsSystem.panel(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_Personalizar_Telegram":
            from .telegram_customization import TelegramCustomizationSystem
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = TelegramCustomizationSystem.panel(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_Telegram_Config":
            from .telegram_customization import TelegramCustomizationModal
            await inter.response.send_modal(TelegramCustomizationModal())
        
        elif inter.component.custom_id == "Loja_Telegram_Toggle":
            data = db.get_document("loja_telegram_customization")
            data["enabled"] = not data.get("enabled", False)
            db.save_document("loja_telegram_customization", data)
            
            from .telegram_customization import TelegramCustomizationSystem
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = TelegramCustomizationSystem.panel(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_SalesLogs_Config":
            from .sales_logs_customization import open_config_modal, SalesLogsSystem
            data = SalesLogsSystem.get_config()
            mode = data.get("mode", "image")
            await inter.response.send_modal(open_config_modal(mode))
        
        elif inter.component.custom_id == "Loja_SalesLogs_CycleMode":
            from .sales_logs_customization import SalesLogsSystem, _MODE_CYCLE
            data = db.get_document("loja_receipt_customization")
            current_mode = data.get("mode", "image")
            data["mode"] = _MODE_CYCLE.get(current_mode, "embed")
            db.save_document("loja_receipt_customization", data)
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = SalesLogsSystem.panel(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_SalesLogs_Toggle":
            data = db.get_document("loja_receipt_customization")
            data["enabled"] = not data.get("enabled", True)
            db.save_document("loja_receipt_customization", data)
            
            from .sales_logs_customization import SalesLogsSystem
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = SalesLogsSystem.panel(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "product_doubt_button":
            from .doubt_button import DoubtButtonSystem
            await DoubtButtonSystem.handle_doubt_button(inter)


def setup(bot: commands.Bot):
    bot.add_cog(PersonalizarLoja(bot))