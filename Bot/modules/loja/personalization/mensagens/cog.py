"""
Sistema de personalização de mensagens da loja
"""
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class PersonalizarMensagens(commands.Cog):
    """Personalização de mensagens da loja"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        """Retorna o painel de personalização de mensagens"""
        mode = db.get_document("custom_mode").get("mode", "components")
        
        if mode == "embed":
            return PersonalizarMensagens._panel_embed(inter)
        else:
            return PersonalizarMensagens._panel_components(inter)
    
    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        """Painel em modo components v2"""
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        # Carregar configurações atuais
        config = db.get_document("loja_personalization") or {}
        event_config = config.get("purchase_event", {})
        feedback_config = config.get("feedback_incentive", {})
        
        # Status das configurações
        event_configured = bool(event_config.get("color") or event_config.get("image"))
        feedback_configured = feedback_config.get("message") is not None
        
        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Personalizar > **Mensagens**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    "Configure as mensagens automáticas da sua loja.\n"
                    "Personalize eventos de compra e incentivos de feedback."
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("**Configurações Disponíveis**"),
                disnake.ui.TextDisplay(
                    f"{emoji.on if event_configured else emoji.off} **Evento de Compra**\n"
                    f"-# Mensagem pública quando alguém compra\n"
                    f"{emoji.on if feedback_configured else emoji.off} **Incentivo de Feedback**\n"
                    f"-# Mensagem para incentivar avaliações"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Evento de Compra",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.sparkles,
                        custom_id="Loja_Personalizar_EventoCompra"
                    ),
                    disnake.ui.Button(
                        label="Incentivo Feedback",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.star,
                        custom_id="Loja_Personalizar_Feedback"
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
    def _panel_embed(inter: disnake.MessageInteraction) -> dict:
        """Painel em modo embed"""
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        embed_kwargs = {}
        if primary_color_hex:
            embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
        
        # Carregar configurações atuais
        config = db.get_document("loja_personalization") or {}
        event_config = config.get("purchase_event", {})
        feedback_config = config.get("feedback_incentive", {})
        
        # Status das configurações
        event_configured = bool(event_config.get("color") or event_config.get("image"))
        feedback_configured = feedback_config.get("message") is not None
        
        embed = disnake.Embed(
            title="Personalizar Mensagens",
            description=(
                "-# Painel > Loja > Personalizar > **Mensagens**\n\n"
                "Configure as mensagens automáticas da sua loja.\n\n"
                f"{emoji.on if event_configured else emoji.off} **Evento de Compra**\n"
                f"Mensagem pública quando alguém compra\n"
                f"{emoji.on if feedback_configured else emoji.off} **Incentivo de Feedback**\n"
                f"Mensagem para incentivar avaliações"
            ),
            **embed_kwargs
        )
        
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Evento de Compra",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.sparkles,
                    custom_id="Loja_Personalizar_EventoCompra"
                ),
                disnake.ui.Button(
                    label="Incentivo Feedback",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.star,
                    custom_id="Loja_Personalizar_Feedback"
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
        
        return {"embed": embed, "components": components}
    
    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Personalizar_Mensagens":
            mode = db.get_document("custom_mode").get("mode")
            
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            panel_data = self.panel(inter)
            await inter.edit_original_message(**panel_data)
        
        elif inter.component.custom_id == "Loja_Personalizar_EventoCompra":
            await inter.response.send_modal(ConfigurarEventoCompraModal())
        
        elif inter.component.custom_id == "Loja_Personalizar_Feedback":
            await inter.response.send_modal(ConfigurarFeedbackModal())


class ConfigurarEventoCompraModal(disnake.ui.Modal):
    """Modal para configurar visual do evento de compra"""
    
    def __init__(self):
        # Carregar configuração atual
        config = db.get_document("loja_personalization") or {}
        event_config = config.get("purchase_event", {})
        
        current_color = event_config.get("color", "")
        current_image = event_config.get("image", "")
        
        components = [
            disnake.ui.TextInput(
                label="Cor do Evento (Hex)",
                placeholder="Ex: #00FF00 (deixe vazio para cor padrão verde)",
                custom_id="color",
                style=disnake.TextInputStyle.short,
                value=current_color,
                required=False,
                max_length=7
            ),
            disnake.ui.TextInput(
                label="URL da Imagem (Embed)",
                placeholder="https://... (deixe vazio para sem imagem)",
                custom_id="image",
                style=disnake.TextInputStyle.short,
                value=current_image,
                required=False
            )
        ]
        
        super().__init__(
            title="Configurar Visual do Evento",
            custom_id="ConfigurarEventoCompra_Modal",
            components=components
        )
    
    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)
        
        # Salvar configuração (apenas cor e imagem)
        config = db.get_document("loja_personalization") or {}
        config["purchase_event"] = {
            "color": inter.text_values.get("color", "").strip(),
            "image": inter.text_values.get("image", "").strip()
        }
        db.save_document("loja_personalization", config)
        
        # Atualizar painel
        panel_data = PersonalizarMensagens.panel(inter)
        await inter.edit_original_message(**panel_data)


class ConfigurarFeedbackModal(disnake.ui.Modal):
    """Modal para configurar mensagem de incentivo de feedback"""
    
    def __init__(self):
        # Carregar configuração atual
        config = db.get_document("loja_personalization") or {}
        feedback_config = config.get("feedback_incentive", {})
        
        current_message = feedback_config.get(
            "message",
            "**Obrigado pela sua compra!** 🎉\n\n"
            "Que tal deixar uma avaliação sobre sua experiência?\n"
            "-# Seu feedback é muito importante para nós!"
        )
        current_button_text = feedback_config.get("button_text", "Deixar Avaliação")
        
        components = [
            disnake.ui.TextInput(
                label="Mensagem de Incentivo",
                placeholder="Mensagem para incentivar feedback",
                custom_id="message",
                style=disnake.TextInputStyle.paragraph,
                value=current_message,
                required=True,
                max_length=1000
            ),
            disnake.ui.TextInput(
                label="Texto do Botão",
                placeholder="Ex: Deixar Avaliação",
                custom_id="button_text",
                style=disnake.TextInputStyle.short,
                value=current_button_text,
                required=True,
                max_length=30
            )
        ]
        
        super().__init__(
            title="Configurar Incentivo de Feedback",
            custom_id="ConfigurarFeedback_Modal",
            components=components
        )
    
    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)
        
        # Salvar configuração
        config = db.get_document("loja_personalization") or {}
        config["feedback_incentive"] = {
            "message": inter.text_values.get("message"),
            "button_text": inter.text_values.get("button_text")
        }
        db.save_document("loja_personalization", config)
        
        # Atualizar painel
        panel_data = PersonalizarMensagens.panel(inter)
        await inter.edit_original_message(**panel_data)


def setup(bot: commands.Bot):
    bot.add_cog(PersonalizarMensagens(bot))