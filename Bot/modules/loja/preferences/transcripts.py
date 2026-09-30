"""
Aqui o usuario vai poder configurar se os transcripts de carrinhos serão enviados para um canal que tambem poderá ser configurado junto com as informações do carrinho como dono, produtos, etc
"""

import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message


class TranscriptsChannelModal(disnake.ui.Modal):
    """Modal para selecionar canal de transcripts"""
    
    def __init__(self, current_channel_id: str = ""):
        components = [
            disnake.ui.Label(
                text="Selecione o Canal de Transcripts",
                component=disnake.ui.ChannelSelect(
                    placeholder="Escolha um canal de texto",
                    custom_id="transcripts_channel_select",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                ),
                description="Os transcripts de carrinhos serão enviados para este canal.",
            ),
        ]
        super().__init__(title="Configurar Canal de Transcripts", components=components, custom_id="transcripts_channel_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        try:
            valores = inter.resolved_values
            selected = valores.get("transcripts_channel_select")
            
            # Normalizar seleção para string channel ID
            if isinstance(selected, (list, tuple)):
                selected = selected[0] if selected else None
            if isinstance(selected, (str, int)):
                channel_id = int(selected)
            elif hasattr(selected, "id"):
                channel_id = int(selected.id)
            else:
                await inter.response.send_message(
                    f"{emoji.wrong} Canal inválido!",
                    ephemeral=True
                )
                return
            
            # Verificar se o canal existe
            channel = inter.guild.get_channel(channel_id)
            if not channel:
                await inter.response.send_message(
                    f"{emoji.wrong} Canal não encontrado!",
                    ephemeral=True
                )
                return
            
            # Salvar configuração
            prefs = db.get_document("loja_preferences") or {}
            if not isinstance(prefs, dict):
                prefs = {}
            
            prefs["transcript_channel_id"] = channel_id
            db.save_document("loja_preferences", prefs)
            
            await inter.response.send_message(
                f"{emoji.correct} Canal configurado: {channel.mention}\n"
                f"O painel de preferências foi atualizado.",
                ephemeral=True
            )
            
            # Atualizar painel
            try:
                mode = db.get_document("custom_mode").get("mode")
                await inter.response.defer()
                panel = TranscriptsPreferences.panel(inter)
                if mode == "embed":
                    await inter.edit_original_message(content=None, **panel)
                else:
                    await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
            except:
                pass
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"{emoji.wrong} Erro ao processar modal: {str(e)}",
                    ephemeral=True
                )


class TranscriptsPreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        return TranscriptsPreferences._panel_embed(inter) if mode == "embed" else TranscriptsPreferences._panel_components(inter)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        prefs = db.get_document("loja_preferences") or {}
        transcript_enabled = prefs.get("transcript_enabled", False)
        transcript_channel_id = prefs.get("transcript_channel_id")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        status_text = f"{emoji.on if transcript_enabled else emoji.off} **Status:** `{'Ativado' if transcript_enabled else 'Desativado'}`\n"
        status_text += "-# Os transcripts de carrinhos permitem salvar o histórico de compras.\n"
        if transcript_enabled:
            if transcript_channel_id:
                channel = inter.guild.get_channel(int(transcript_channel_id)) if inter.guild else None
                channel_name = channel.name if channel else "Canal não encontrado"
                status_text += f"-# Canal: `#{channel_name}`\n"
            else:
                status_text += f"-# Canal: `Não configurado`\n"
        else:
            status_text += "-# Configure o canal e ative para salvar transcripts"

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Preferências > **Transcript de Carrinhos**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(status_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativar" if not transcript_enabled else "Desativar",
                        emoji=emoji.correct if not transcript_enabled else emoji.off,
                        style=disnake.ButtonStyle.green if not transcript_enabled else disnake.ButtonStyle.red,
                        custom_id="Loja_Pref_Transcripts_Toggle"
                    ),
                    disnake.ui.Button(
                        label="Configurar Canal",
                        emoji=emoji.edit,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Loja_Pref_Transcripts_Channel"
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
        prefs = db.get_document("loja_preferences") or {}
        transcript_enabled = prefs.get("transcript_enabled", False)
        transcript_channel_id = prefs.get("transcript_channel_id")

        status_text = f"{emoji.on if transcript_enabled else emoji.off} **Status:** `{'Ativado' if transcript_enabled else 'Desativado'}`\n"
        status_text += "-# Os transcripts de carrinhos permitem salvar o histórico de compras.\n"
        if transcript_enabled:
            if transcript_channel_id:
                channel = inter.guild.get_channel(int(transcript_channel_id)) if inter.guild else None
                channel_name = channel.name if channel else "Canal não encontrado"
                status_text += f"-# Canal: `#{channel_name}`\n"
            else:
                status_text += f"-# Canal: `Não configurado`\n"
        else:
            status_text += "-# Configure o canal e ative para salvar transcripts"

        embed = disnake.Embed(
            title="Transcript de Carrinhos",
            description=(
                "-# Painel > Loja > Preferências > **Transcript de Carrinhos**\n\n"
                f"{status_text}"
            )
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ativar" if not transcript_enabled else "Desativar",
                    emoji=emoji.correct if not transcript_enabled else emoji.off,
                    style=disnake.ButtonStyle.green if not transcript_enabled else disnake.ButtonStyle.red,
                    custom_id="Loja_Pref_Transcripts_Toggle"
                ),
                disnake.ui.Button(
                    label="Configurar Canal",
                    emoji=emoji.edit,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Loja_Pref_Transcripts_Channel"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Preferencias")
            )
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Pref_Transcripts_Toggle":
            # Toggle transcript
            prefs = db.get_document("loja_preferences") or {}
            if not isinstance(prefs, dict):
                prefs = {}
            
            current = prefs.get("transcript_enabled", False)
            prefs["transcript_enabled"] = not current
            db.save_document("loja_preferences", prefs)

            mode = db.get_document("custom_mode").get("mode")
            await inter.response.defer()
            panel = TranscriptsPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Loja_Pref_Transcripts_Channel":
            # Mostrar modal com select de canal
            prefs = db.get_document("loja_preferences") or {}
            current_channel_id = str(prefs.get("transcript_channel_id", ""))
            await inter.response.send_modal(TranscriptsChannelModal(current_channel_id))
    
    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        # Handler de dropdown removido - agora usando modal
        pass


def setup(bot: commands.Bot):
    bot.add_cog(TranscriptsPreferences(bot))
