"""
Sistema de solicitação de estoque
Usuários podem solicitar reposição de estoque de produtos
"""

import disnake
from disnake.ext import commands
from datetime import datetime

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.server_check import is_main_server
from functions.utils import utils
from .container_utils import ContainerUtils


# --- Modais para seleção de canal/cargo ---

class StockRequestChannelModal(disnake.ui.Modal):
    """Modal para selecionar canal de solicitações de estoque"""
    
    def __init__(self, current_channel_id: str = ""):
        components = [
            disnake.ui.Label(
                text="Selecione o Canal de Solicitações",
                component=disnake.ui.ChannelSelect(
                    placeholder="Escolha um canal de texto",
                    custom_id="stock_request_channel_select",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                ),
                description="Este canal receberá as solicitações de estoque dos usuários.",
            ),
        ]
        super().__init__(title="Configurar Canal de Solicitações", components=components, custom_id="stock_request_channel_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        try:
            valores = inter.resolved_values
            selected = valores.get("stock_request_channel_select")
            
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
            
            if "stock_requests" not in prefs:
                prefs["stock_requests"] = {}
            
            prefs["stock_requests"]["channel_id"] = channel_id
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
                panel = StockRequestPreferences.panel(inter)
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


class StockRequestRoleModal(disnake.ui.Modal):
    """Modal para selecionar cargo permitido para solicitar estoque"""
    
    def __init__(self, current_role_id: str = ""):
        components = [
            disnake.ui.Label(
                text="Selecione o Cargo Permitido",
                component=disnake.ui.RoleSelect(
                    placeholder="Escolha um cargo para restringir",
                    custom_id="stock_request_role_select",
                    min_values=1,
                    max_values=1,
                ),
                description="Apenas membros com este cargo poderão solicitar estoque.",
            ),
        ]
        super().__init__(title="Configurar Cargo de Solicitações", components=components, custom_id="stock_request_role_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        try:
            valores = inter.resolved_values
            selected = valores.get("stock_request_role_select")
            
            # Normalizar seleção para string role ID
            if isinstance(selected, (list, tuple)):
                selected = selected[0] if selected else None
            if isinstance(selected, (str, int)):
                role_id = int(selected)
            elif hasattr(selected, "id"):
                role_id = int(selected.id)
            else:
                await inter.response.send_message(
                    f"{emoji.wrong} Cargo inválido!",
                    ephemeral=True
                )
                return
            
            # Verificar se o cargo existe
            role = inter.guild.get_role(role_id)
            if not role:
                await inter.response.send_message(
                    f"{emoji.wrong} Cargo não encontrado!",
                    ephemeral=True
                )
                return
            
            # Salvar configuração
            prefs = db.get_document("loja_preferences") or {}
            if not isinstance(prefs, dict):
                prefs = {}
            
            if "stock_requests" not in prefs:
                prefs["stock_requests"] = {}
            
            prefs["stock_requests"]["role_id"] = role_id
            db.save_document("loja_preferences", prefs)
            
            await inter.response.send_message(
                f"{emoji.correct} Cargo configurado: {role.mention}\n"
                f"O painel de preferências foi atualizado.",
                ephemeral=True
            )
            
            # Atualizar painel
            try:
                mode = db.get_document("custom_mode").get("mode")
                await inter.response.defer()
                panel = StockRequestPreferences.panel(inter)
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


class StockRequestSendChannelModal(disnake.ui.Modal):
    """Modal para selecionar canal onde enviar o painel de solicitações"""
    
    def __init__(self):
        components = [
            disnake.ui.Label(
                text="Selecione o Canal",
                component=disnake.ui.ChannelSelect(
                    placeholder="Escolha um canal de texto",
                    custom_id="stock_request_send_channel_select",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                ),
                description="O painel de solicitações será enviado para este canal.",
            ),
        ]
        super().__init__(title="Enviar Painel de Solicitações", components=components, custom_id="stock_request_send_channel_modal")
    
    async def callback(self, inter: disnake.ModalInteraction):
        try:
            valores = inter.resolved_values
            selected = valores.get("stock_request_send_channel_select")
            
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
            
            # Obter configuração da mensagem
            prefs = db.get_document("loja_preferences") or {}
            stock_requests = prefs.get("stock_requests", {})
            message_config = stock_requests.get("panel_message", {})
            
            await inter.response.defer(ephemeral=True)
            success, error_msg = await _send_stock_request_panel(channel, message_config)
            
            if success:
                await inter.followup.send(
                    f"{emoji.correct} Painel enviado com sucesso para {channel.mention}!",
                    ephemeral=True
                )
            else:
                await inter.followup.send(
                    f"{emoji.wrong} Erro ao enviar painel: {error_msg}",
                    ephemeral=True
                )
        except Exception as e:
            if not inter.response.is_done():
                await inter.response.send_message(
                    f"{emoji.wrong} Erro ao processar modal: {str(e)}",
                    ephemeral=True
                )


class StockRequestPreferences(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def panel(inter: disnake.MessageInteraction) -> dict:
        mode = db.get_document("custom_mode").get("mode")
        return StockRequestPreferences._panel_embed(inter) if mode == "embed" else StockRequestPreferences._panel_components(inter)

    @staticmethod
    def _panel_components(inter: disnake.MessageInteraction) -> dict:
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        prefs = db.get_document("loja_preferences") or {}
        stock_requests = prefs.get("stock_requests", {})
        
        enabled = stock_requests.get("enabled", False)
        channel_id = stock_requests.get("channel_id")
        role_id = stock_requests.get("role_id")

        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        status_text = f"**Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        if enabled:
            if channel_id:
                channel = inter.guild.get_channel(int(channel_id)) if inter.guild else None
                channel_name = channel.name if channel else "Canal não encontrado"
                status_text += f"-# Canal: `#{channel_name}`\n"
            else:
                status_text += f"-# Canal: `Não configurado`\n"
            
            if role_id:
                role = inter.guild.get_role(int(role_id)) if inter.guild else None
                role_name = role.name if role else "Cargo não encontrado"
                status_text += f"-# Cargo permitido: `@{role_name}`\n"
            else:
                status_text += f"-# Cargo: `Todos podem solicitar`\n"
        else:
            status_text += "-# Configure o canal e ative para permitir solicitações"

        return {"components": [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Preferências > **Solicitar Estoque**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(status_text),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ativar" if not enabled else "Desativar",
                        emoji=emoji.power,
                        style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red,
                        custom_id="Loja_Pref_StockRequests_Toggle"
                    ),
                    disnake.ui.Button(
                        label="Configurar Canal",
                        emoji=emoji.edit,
                        style=disnake.ButtonStyle.blurple,
                        custom_id="Loja_Pref_StockRequests_Channel"
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Configurar Cargo",
                        emoji=emoji.members,
                        style=disnake.ButtonStyle.grey,
                        custom_id="Loja_Pref_StockRequests_Role"
                    ),
                    disnake.ui.Button(
                        label="Enviar Painel",
                        emoji=emoji.arrow,
                        style=disnake.ButtonStyle.green,
                        custom_id="Loja_Pref_StockRequests_SendPanel",
                        disabled=not enabled
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
        stock_requests = prefs.get("stock_requests", {})
        
        enabled = stock_requests.get("enabled", False)
        channel_id = stock_requests.get("channel_id")
        role_id = stock_requests.get("role_id")

        status_text = f"**Status:** `{'Ativado' if enabled else 'Desativado'}`\n"
        if enabled:
            if channel_id:
                channel = inter.guild.get_channel(int(channel_id)) if inter.guild else None
                channel_name = channel.name if channel else "Canal não encontrado"
                status_text += f"-# Canal: `#{channel_name}`\n"
            else:
                status_text += f"-# Canal: `Não configurado`\n"
            
            if role_id:
                role = inter.guild.get_role(int(role_id)) if inter.guild else None
                role_name = role.name if role else "Cargo não encontrado"
                status_text += f"-# Cargo permitido: `@{role_name}`\n"
            else:
                status_text += f"-# Cargo: `Todos podem solicitar`\n"
        else:
            status_text += "-# Configure o canal e ative para permitir solicitações"

        embed = disnake.Embed(
            title="Solicitar Estoque",
            description=(
                "-# Painel > Loja > Preferências > **Solicitar Estoque**\n\n"
                f"{status_text}"
            )
        )
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Ativar" if not enabled else "Desativar",
                    emoji=emoji.power,
                    style=disnake.ButtonStyle.green if not enabled else disnake.ButtonStyle.red,
                    custom_id="Loja_Pref_StockRequests_Toggle"
                ),
                disnake.ui.Button(
                    label="Configurar Canal",
                    emoji=emoji.edit,
                    style=disnake.ButtonStyle.blurple,
                    custom_id="Loja_Pref_StockRequests_Channel"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Configurar Cargo",
                    emoji=emoji.members,
                    style=disnake.ButtonStyle.grey,
                    custom_id="Loja_Pref_StockRequests_Role"
                ),
                disnake.ui.Button(
                    label="Enviar Painel",
                    emoji=emoji.arrow,
                    style=disnake.ButtonStyle.green,
                    custom_id="Loja_Pref_StockRequests_SendPanel",
                    disabled=not enabled
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Preferencias")
            )
        ]
        return {"embed": embed, "components": components}

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        # Handlers de dropdown removidos - agora usando modais
        pass
    
    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Loja_Pref_StockRequests_Toggle":
            prefs = db.get_document("loja_preferences") or {}
            if not isinstance(prefs, dict):
                prefs = {}
            
            if "stock_requests" not in prefs:
                prefs["stock_requests"] = {}
            
            current = prefs["stock_requests"].get("enabled", False)
            prefs["stock_requests"]["enabled"] = not current
            db.save_document("loja_preferences", prefs)
            
            mode = db.get_document("custom_mode").get("mode")
            await (embed_message if mode == "embed" else message).wait(inter, send=False)
            panel = StockRequestPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_Channel":
            # Mostrar modal com select de canal
            prefs = db.get_document("loja_preferences") or {}
            stock_requests = prefs.get("stock_requests", {})
            current_channel_id = str(stock_requests.get("channel_id", ""))
            await inter.response.send_modal(StockRequestChannelModal(current_channel_id))
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_Role":
            # Mostrar modal com select de cargo
            prefs = db.get_document("loja_preferences") or {}
            stock_requests = prefs.get("stock_requests", {})
            current_role_id = str(stock_requests.get("role_id", ""))
            await inter.response.send_modal(StockRequestRoleModal(current_role_id))
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_RemoveRole":
            # Remover restrição de cargo
            prefs = db.get_document("loja_preferences") or {}
            if not isinstance(prefs, dict):
                prefs = {}
            
            if "stock_requests" not in prefs:
                prefs["stock_requests"] = {}
            
            prefs["stock_requests"]["role_id"] = None
            db.save_document("loja_preferences", prefs)
            
            await inter.response.send_message(
                f"{emoji.correct} Restrição de cargo removida. Todos podem solicitar estoque.",
                ephemeral=True
            )
            
            # Tentar atualizar a mensagem original se possível
            try:
                mode = db.get_document("custom_mode").get("mode")
                await (embed_message if mode == "embed" else message).wait(inter, send=False)
                panel = StockRequestPreferences.panel(inter)
                if mode == "embed":
                    await inter.edit_original_message(content=None, **panel)
                else:
                    await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
            except:
                pass
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_SendPanel":
            # Mostrar painel de edição de mensagem
            await self._show_message_editor(inter)
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_Back":
            # Voltar ao painel principal
            mode = db.get_document("custom_mode").get("mode")
            await inter.response.defer()
            panel = StockRequestPreferences.panel(inter)
            if mode == "embed":
                await inter.edit_original_message(content=None, **panel)
            else:
                await inter.edit_original_message(**panel, flags=disnake.MessageFlags(is_components_v2=True))
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_EditButton":
            # Mostrar modal para editar botão
            prefs = db.get_document("loja_preferences") or {}
            stock_requests = prefs.get("stock_requests", {})
            message_config = stock_requests.get("panel_message", {})
            button_data = message_config.get("button", {})
            await inter.response.send_modal(EditButtonModal(button_data))
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_EditContent":
            # Mostrar modal para editar conteúdo baseado no estilo
            prefs = db.get_document("loja_preferences") or {}
            stock_requests = prefs.get("stock_requests", {})
            message_config = stock_requests.get("panel_message", {})
            style = message_config.get("message_style", "embed")
            
            if style == "embed":
                embed_data = message_config.get("embed", {})
                await inter.response.send_modal(EditEmbedModal(embed_data))
            elif style == "content":
                content_data = message_config.get("content", {})
                await inter.response.send_modal(EditContentModal(content_data))
            elif style == "container":
                container_data = message_config.get("container", {})
                await inter.response.send_modal(EditContainerModal(container_data))
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_CycleStyle":
            # Trocar estilo da mensagem
            prefs = db.get_document("loja_preferences") or {}
            if "stock_requests" not in prefs:
                prefs["stock_requests"] = {}
            if "panel_message" not in prefs["stock_requests"]:
                prefs["stock_requests"]["panel_message"] = {}
            
            message_config = prefs["stock_requests"]["panel_message"]
            styles = ["embed", "content", "container"]
            current_style = message_config.get("message_style", "embed")
            try:
                current_index = styles.index(current_style)
                new_style = styles[(current_index + 1) % len(styles)]
            except ValueError:
                new_style = "embed"
            
            message_config["message_style"] = new_style
            prefs["stock_requests"]["panel_message"] = message_config
            db.save_document("loja_preferences", prefs)
            
            await self._show_message_editor(inter)
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_Preview":
            # Visualizar mensagem
            prefs = db.get_document("loja_preferences") or {}
            stock_requests = prefs.get("stock_requests", {})
            message_config = stock_requests.get("panel_message", {})
            
            await inter.response.defer(ephemeral=True)
            preview_msg = await _build_preview_message(message_config)
            await inter.followup.send(**preview_msg, ephemeral=True)
        
        elif inter.component.custom_id == "Loja_Pref_StockRequests_Send":
            # Mostrar modal com select de canal para enviar
            await inter.response.send_modal(StockRequestSendChannelModal())
    
    async def _show_message_editor(self, inter: disnake.MessageInteraction):
        """Mostra o painel de edição de mensagem"""
        mode = db.get_document("custom_mode").get("mode")
        
        if mode == "embed":
            await embed_message.wait(inter)
            embed, components = _message_editor_embed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await message.wait(inter)
            components = _message_editor_components(inter)
            await inter.edit_original_message(**components, flags=disnake.MessageFlags(is_components_v2=True))


# --- Modais para edição de mensagem ---

class EditButtonModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        self.data = data
        
        color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
        current_style_en = data.get("style", "green")
        current_style_pt = next((pt for pt, en in color_map_pt_to_en.items() if en == current_style_en), "verde")

        components = [
            disnake.ui.TextInput(label="Texto do Botão", custom_id="label", value=data.get("label", "Solicitar Estoque"), max_length=30, required=True, placeholder="Solicitar Estoque"),
            disnake.ui.TextInput(label="Emoji do Botão (Opcional)", custom_id="emoji", value=data.get("emoji", ""), required=False, max_length=100, placeholder="📦 ou <:nome:ID>"),
            disnake.ui.TextInput(label="Estilo (verde, cinza, vermelho, azul)", custom_id="style", value=current_style_pt, max_length=10, required=True, placeholder="Ex: verde"),
        ]
        super().__init__(title="Editar Botão de Solicitação", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        prefs = db.get_document("loja_preferences") or {}
        if "stock_requests" not in prefs:
            prefs["stock_requests"] = {}
        if "panel_message" not in prefs["stock_requests"]:
            prefs["stock_requests"]["panel_message"] = {}
        if "button" not in prefs["stock_requests"]["panel_message"]:
            prefs["stock_requests"]["panel_message"]["button"] = {}

        option_emoji = inter.text_values.get("emoji", "")
        if option_emoji:
            validation = utils.validate_emoji_for_components(option_emoji)
            if not validation["valid"]:
                error_msg = validation.get("error", "Emoji inválido")
                await inter.response.send_message(
                    f"{emoji.wrong} O emoji fornecido não é válido para uso em componentes. {error_msg}\n\nUse um emoji unicode (ex: ✅) ou um emoji customizado no formato <:nome:id>.",
                    ephemeral=True
                )
                return
            # Converter para string apropriada
            if isinstance(validation["emoji"], disnake.PartialEmoji):
                option_emoji = str(validation["emoji"])
            else:
                option_emoji = validation["emoji"]

        color_map_pt_to_en = {"verde": "green", "cinza": "grey", "vermelho": "red", "azul": "blue"}
        style_pt = inter.text_values.get("style", "verde").lower()
        style_en = color_map_pt_to_en.get(style_pt, "green")
        
        prefs["stock_requests"]["panel_message"]["button"]["label"] = inter.text_values["label"]
        prefs["stock_requests"]["panel_message"]["button"]["emoji"] = option_emoji
        prefs["stock_requests"]["panel_message"]["button"]["style"] = style_en
        db.save_document("loja_preferences", prefs)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            components = _message_editor_components(inter)
            await inter.response.edit_message(**components, flags=disnake.MessageFlags(is_components_v2=True))
        else:
            embed, components = _message_editor_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class EditEmbedModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        components = [
            disnake.ui.TextInput(label="Título", custom_id="title", value=data.get("title", "Solicitar Estoque"), max_length=256, placeholder="Solicitar Estoque", required=True),
            disnake.ui.TextInput(label="Descrição", custom_id="description", value=data.get("description", ""), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para solicitar reposição de estoque...", required=False),
            disnake.ui.TextInput(label="URL da Imagem/Banner", custom_id="image_url", value=data.get("image_url", ""), required=False, placeholder="https://i.imgur.com/banner.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url", ""), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color", ""), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Conteúdo: Embed", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        prefs = db.get_document("loja_preferences") or {}
        if "stock_requests" not in prefs:
            prefs["stock_requests"] = {}
        if "panel_message" not in prefs["stock_requests"]:
            prefs["stock_requests"]["panel_message"] = {}
        if "embed" not in prefs["stock_requests"]["panel_message"]:
            prefs["stock_requests"]["panel_message"]["embed"] = {}

        new_data = inter.text_values.copy()
        
        for key in ["color", "image_url", "thumbnail_url", "description"]:
            if key in new_data and not new_data[key]:
                prefs["stock_requests"]["panel_message"]["embed"].pop(key, None)
                del new_data[key]

        prefs["stock_requests"]["panel_message"]["embed"].update(new_data)
        db.save_document("loja_preferences", prefs)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            components = _message_editor_components(inter)
            await inter.response.edit_message(**components, flags=disnake.MessageFlags(is_components_v2=True))
        else:
            embed, components = _message_editor_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class EditContentModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content", ""), style=disnake.TextInputStyle.paragraph, max_length=2000, placeholder="Clique no botão abaixo para solicitar estoque...", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url", ""), required=False, placeholder="https://i.imgur.com/imagem.png"),
        ]
        super().__init__(title="Editar Conteúdo: Texto Simples", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        prefs = db.get_document("loja_preferences") or {}
        if "stock_requests" not in prefs:
            prefs["stock_requests"] = {}
        if "panel_message" not in prefs["stock_requests"]:
            prefs["stock_requests"]["panel_message"] = {}
        if "content" not in prefs["stock_requests"]["panel_message"]:
            prefs["stock_requests"]["panel_message"]["content"] = {}

        new_data = inter.text_values.copy()
        for key in ["image_url", "content"]:
            if key in new_data and not new_data[key]:
                prefs["stock_requests"]["panel_message"]["content"].pop(key, None)
                del new_data[key]

        prefs["stock_requests"]["panel_message"]["content"].update(new_data)
        db.save_document("loja_preferences", prefs)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            components = _message_editor_components(inter)
            await inter.response.edit_message(**components, flags=disnake.MessageFlags(is_components_v2=True))
        else:
            embed, components = _message_editor_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)

class EditContainerModal(disnake.ui.Modal):
    def __init__(self, data: dict):
        components = [
            disnake.ui.TextInput(label="Conteúdo", custom_id="content", value=data.get("content", ""), style=disnake.TextInputStyle.paragraph, max_length=4000, placeholder="Clique no botão abaixo para solicitar estoque...", required=False),
            disnake.ui.TextInput(label="URL da Imagem", custom_id="image_url", value=data.get("image_url", ""), required=False, placeholder="https://i.imgur.com/imagem.png"),
            disnake.ui.TextInput(label="URL da Thumbnail", custom_id="thumbnail_url", value=data.get("thumbnail_url", ""), required=False, placeholder="https://i.imgur.com/thumbnail.png"),
            disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", value=data.get("color", ""), max_length=7, required=False, placeholder="#5865F2"),
        ]
        super().__init__(title="Editar Conteúdo: Container", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        prefs = db.get_document("loja_preferences") or {}
        if "stock_requests" not in prefs:
            prefs["stock_requests"] = {}
        if "panel_message" not in prefs["stock_requests"]:
            prefs["stock_requests"]["panel_message"] = {}
        if "container" not in prefs["stock_requests"]["panel_message"]:
            prefs["stock_requests"]["panel_message"]["container"] = {}

        new_data = inter.text_values.copy()
        
        for key in ["color", "image_url", "thumbnail_url", "content"]:
            if key in new_data and not new_data[key]:
                prefs["stock_requests"]["panel_message"]["container"].pop(key, None)
                del new_data[key]

        prefs["stock_requests"]["panel_message"]["container"].update(new_data)
        db.save_document("loja_preferences", prefs)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            components = _message_editor_components(inter)
            await inter.response.edit_message(**components, flags=disnake.MessageFlags(is_components_v2=True))
        else:
            embed, components = _message_editor_embed(inter)
            await inter.response.edit_message(content=None, embed=embed, components=components)


# --- Funções auxiliares para o editor ---

def _message_editor_components(inter: disnake.Interaction) -> dict:
    prefs = db.get_document("loja_preferences") or {}
    message_config = prefs.get("stock_requests", {}).get("panel_message", {})
    
    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    style = message_config.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(message_config.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(message_config.get("embed", {}).get("title"))
    elif style == "content":
        content_data = message_config.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(message_config.get("container", {}).get("content"))
    
    preview_enabled = button_configured and content_configured

    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if button_configured else emoji.wrong} **Botão:** {'`Configurado`' if button_configured else '`Não Configurado`'}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    container_kwargs = {}
    if primary_color_hex:
        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

    main_container_children = [
        disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Loja > Preferências > Solicitar Estoque > **Editor de Mensagem**"),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.TextDisplay(status_text),
        disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id="Loja_Pref_StockRequests_CycleStyle"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id="Loja_Pref_StockRequests_EditButton"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Loja_Pref_StockRequests_EditContent"),
        ),
    ]

    container = disnake.ui.Container(*main_container_children, **container_kwargs)
    
    action_row_buttons = [
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Pref_StockRequests_Back")
    ]

    publish_enabled = button_configured and content_configured
    if publish_enabled:
        action_row_buttons.append(
            disnake.ui.Button(label="Enviar", style=disnake.ButtonStyle.green, emoji=emoji.arrow, custom_id="Loja_Pref_StockRequests_Send")
        )
        action_row_buttons.append(
            disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="Loja_Pref_StockRequests_Preview")
        )
    else:
        action_row_buttons.append(
            disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="Loja_Pref_StockRequests_Preview", disabled=True)
        )

    buttons = disnake.ui.ActionRow(*action_row_buttons)

    return {"components": [container, buttons]}

def _message_editor_embed(inter: disnake.Interaction):
    prefs = db.get_document("loja_preferences") or {}
    message_config = prefs.get("stock_requests", {}).get("panel_message", {})

    custom_colors = db.get_document("custom_colors") or {}
    primary_color_hex = custom_colors.get("primary", "#5c5ef0")
    style = message_config.get("message_style", "embed")
    style_names = {"embed": "`Embed`", "content": "`Texto Simples`", "container": "`Container V2`"}
    styles = list(style_names.keys())
    
    button_configured = bool(message_config.get("button", {}).get("label"))
    content_configured = False
    if style == "embed":
        content_configured = bool(message_config.get("embed", {}).get("title"))
    elif style == "content":
        content_data = message_config.get("content", {})
        content_configured = bool(content_data.get("content") or content_data.get("image_url"))
    elif style == "container":
        content_configured = bool(message_config.get("container", {}).get("content"))
    
    preview_enabled = button_configured and content_configured

    status_text = (
        f"{emoji.receipt} **Estilo Atual:** {style_names.get(style, 'N/A')}\n"
        f"{emoji.correct if button_configured else emoji.wrong} **Botão:** {'`Configurado`' if button_configured else '`Não Configurado`'}\n"
        f"{emoji.correct if content_configured else emoji.wrong} **Conteúdo:** {'`Configurado`' if content_configured else '`Não Configurado`'}"
    )

    embed_kwargs = {}
    if primary_color_hex:
        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

    embed = disnake.Embed(
        title="Editor de Mensagem - Solicitar Estoque",
        description=status_text,
        **embed_kwargs
    )

    current_style_index = styles.index(style) if style in styles else 0
    style_button_label = f"Trocar Estilo ({current_style_index + 1}/{len(styles)})"

    action_row_buttons = [
        disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Loja_Pref_StockRequests_Back")
    ]

    publish_enabled = button_configured and content_configured
    if publish_enabled:
        action_row_buttons.append(
            disnake.ui.Button(label="Enviar", style=disnake.ButtonStyle.green, emoji=emoji.arrow, custom_id="Loja_Pref_StockRequests_Send")
        )
        action_row_buttons.append(
            disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="Loja_Pref_StockRequests_Preview")
        )
    else:
        action_row_buttons.append(
            disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="Loja_Pref_StockRequests_Preview", disabled=True)
        )

    components = [
        disnake.ui.ActionRow(
            disnake.ui.Button(label=style_button_label, style=disnake.ButtonStyle.grey, emoji=emoji.reload, custom_id="Loja_Pref_StockRequests_CycleStyle"),
            disnake.ui.Button(label="Editar Botão", style=disnake.ButtonStyle.grey, emoji=emoji.wand, custom_id="Loja_Pref_StockRequests_EditButton"),
            disnake.ui.Button(label="Editar Conteúdo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Loja_Pref_StockRequests_EditContent"),
        ),
        disnake.ui.ActionRow(*action_row_buttons)
    ]

    return embed, components


async def _build_preview_message(message_config: dict) -> dict:
    """Constrói mensagem de preview"""
    style = message_config.get("message_style", "embed")
    send_kwargs = {}
    
    if style == "embed":
        embed_data = message_config.get("embed", {})
        normalized_data = utils.normalize_embed_data(embed_data)
        embed = disnake.Embed.from_dict(normalized_data)
        send_kwargs["embed"] = embed
    elif style == "content":
        content_data = message_config.get("content", {})
        send_kwargs["content"] = content_data.get("content")
        if content_data.get("image_url"):
            send_kwargs["file"] = await utils.url_to_file(content_data["image_url"], "image.png")
    elif style == "container":
        data = message_config.get("container", {})
        container = ContainerUtils.montar_container(
            conteudo=data.get("content"), 
            imagem_url=data.get("image_url"), 
            cor_hex=data.get("color"),
            thumbnail_url=data.get("thumbnail_url")
        )
        button_data = message_config.get("button", {})
        style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}
        button = disnake.ui.Button(
            label=button_data.get("label", "Solicitar Estoque"),
            style=style_map.get(button_data.get("style", "green")),
            emoji=button_data.get("emoji") or None,
            custom_id="StockRequest_OpenModal"
        )
        action_row = disnake.ui.ActionRow(button)
        send_kwargs["components"] = [container, action_row]
        send_kwargs["flags"] = disnake.MessageFlags(is_components_v2=True)
        return send_kwargs

    button_data = message_config.get("button", {})
    style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}
    button = disnake.ui.Button(
        label=button_data.get("label", "Solicitar Estoque"),
        style=style_map.get(button_data.get("style", "green")),
        emoji=button_data.get("emoji") or None,
        custom_id="StockRequest_OpenModal"
    )
    
    view = disnake.ui.View(timeout=None)
    view.add_item(button)
    send_kwargs["view"] = view
    
    return send_kwargs


async def _send_stock_request_panel(channel: disnake.TextChannel, message_config: dict) -> tuple[bool, str | None]:
    """Envia o painel de solicitação de estoque"""
    style = message_config.get("message_style", "embed")
    send_kwargs = {}
    
    if style == "embed":
        embed_data = message_config.get("embed", {})
        normalized_data = utils.normalize_embed_data(embed_data)
        embed = disnake.Embed.from_dict(normalized_data)
        send_kwargs["embed"] = embed
    elif style == "content":
        content_data = message_config.get("content", {})
        send_kwargs["content"] = content_data.get("content")
        if content_data.get("image_url"):
            send_kwargs["file"] = await utils.url_to_file(content_data["image_url"], "image.png")
    elif style == "container":
        data = message_config.get("container", {})
        container = ContainerUtils.montar_container(
            conteudo=data.get("content"), 
            imagem_url=data.get("image_url"), 
            cor_hex=data.get("color"),
            thumbnail_url=data.get("thumbnail_url")
        )
        button_data = message_config.get("button", {})
        style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}
        button = disnake.ui.Button(
            label=button_data.get("label", "Solicitar Estoque"),
            style=style_map.get(button_data.get("style", "green")),
            emoji=button_data.get("emoji") or None,
            custom_id="StockRequest_OpenModal"
        )
        action_row = disnake.ui.ActionRow(button)
        send_kwargs["components"] = [container, action_row]
        send_kwargs["flags"] = disnake.MessageFlags(is_components_v2=True)
        try:
            await channel.send(**send_kwargs)
            return True, None
        except disnake.Forbidden:
            return False, "Não tenho permissão para enviar mensagens nesse canal."
        except Exception as e:
            return False, f"Ocorreu um erro ao enviar a mensagem: {e}"

    button_data = message_config.get("button", {})
    style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}
    button = disnake.ui.Button(
        label=button_data.get("label", "Solicitar Estoque"),
        style=style_map.get(button_data.get("style", "green")),
        emoji=button_data.get("emoji") or None,
        custom_id="StockRequest_OpenModal"
    )
    
    view = disnake.ui.View(timeout=None)
    view.add_item(button)
    send_kwargs["view"] = view
    
    try:
        await channel.send(**send_kwargs)
        return True, None
    except disnake.Forbidden:
        return False, "Não tenho permissão para enviar mensagens nesse canal."
    except Exception as e:
        return False, f"Ocorreu um erro ao enviar a mensagem: {e}"


class StockRequestCommand(commands.Cog):
    """
    Comando slash para solicitar estoque
    
    IMPORTANTE: Este comando deve funcionar independentemente do status da loja
    (manutenção ou horário de funcionamento), pois solicitar estoque não é uma compra.
    """
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.slash_command(
        name="solicitar_estoque",
        description="Solicitar reposição de estoque de um produto",
        guild_ids=[utils.obter_server_principal()]
    )
    async def solicitar_estoque_slash(
        self,
        inter: disnake.ApplicationCommandInteraction,
        produto: str = commands.Param(description="Nome do produto que precisa de estoque"),
        quantidade: int = commands.Param(description="Quantidade desejada", min_value=1),
        mensagem: str = commands.Param(description="Mensagem adicional (opcional)", default="", max_length=500)
    ):
        """
        Comando para solicitar estoque.
        Funciona mesmo quando a loja está em manutenção ou fora do horário de funcionamento.
        Apenas disponível no servidor principal.
        """
        # Verificar se está no servidor principal
        if not is_main_server(inter.guild_id):
            await inter.response.send_message(
                f"{emoji.wrong} Este comando só pode ser usado no servidor principal.",
                ephemeral=True
            )
            return
        
        # Verificar se está habilitado
        prefs = db.get_document("loja_preferences") or {}
        stock_requests = prefs.get("stock_requests", {})
        
        if not stock_requests.get("enabled", False):
            await inter.response.send_message(
                f"{emoji.wrong} Sistema de solicitação de estoque está desativado.",
                ephemeral=True
            )
            return
        
        # Verificar cargo se configurado
        role_id = stock_requests.get("role_id")
        if role_id:
            member = inter.guild.get_member(inter.user.id) if inter.guild else None
            if not member or not any(role.id == int(role_id) for role in member.roles):
                await inter.response.send_message(
                    f"{emoji.wrong} Você não tem permissão para solicitar estoque.",
                    ephemeral=True
                )
                return
        
        # Processar solicitação diretamente (sem modal)
        channel_id = stock_requests.get("channel_id")
        
        if not channel_id:
            await inter.response.send_message(
                f"{emoji.wrong} Canal de solicitações não configurado!",
                ephemeral=True
            )
            return
        
        channel = inter.guild.get_channel(int(channel_id)) if inter.guild else None
        if not channel:
            await inter.response.send_message(
                f"{emoji.wrong} Canal não encontrado!",
                ephemeral=True
            )
            return
        
        # Criar solicitação
        request_id = f"{inter.user.id}_{int(datetime.utcnow().timestamp())}"
        
        # Salvar solicitação
        requests_data = db.get_document("loja_stock_requests") or {}
        if not isinstance(requests_data, dict):
            requests_data = {}
        
        if "requests" not in requests_data:
            requests_data["requests"] = {}
        
        requests_data["requests"][request_id] = {
            "user_id": inter.user.id,
            "product_id": None,  # Não temos product_id do comando
            "product_name": produto,
            "quantity": quantidade,
            "message": mensagem.strip(),
            "status": "pending",
            "created_at": int(datetime.utcnow().timestamp()),
            "guild_id": inter.guild.id if inter.guild else None
        }
        db.save_document("loja_stock_requests", requests_data)
        
        # Enviar mensagem no canal
        mode = db.get_document("custom_mode").get("mode", "embed")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        
        if mode == "components":
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            request_msg = await channel.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.cardbox}\n-# **Solicitação de Estoque**"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"-# **Solicitante:** {inter.user.mention}\n"
                            f"-# **Produto:** `{produto}`\n"
                            f"-# **Quantidade:** `{quantidade}`"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(f"-# **Mensagem:**\n{mensagem.strip()}" if mensagem.strip() else "-# Sem mensagem adicional"),
                        **container_kwargs
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Aprovar",
                            emoji=emoji.correct,
                            style=disnake.ButtonStyle.green,
                            custom_id=f"approve_stock_request:{request_id}"
                        ),
                        disnake.ui.Button(
                            label="Rejeitar",
                            emoji=emoji.wrong,
                            style=disnake.ButtonStyle.red,
                            custom_id=f"reject_stock_request:{request_id}"
                        )
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            embed_color = disnake.Color.blue()
            if primary_color_hex:
                try:
                    embed_color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except:
                    pass
            
            embed = disnake.Embed(
                title=f"{emoji.cardbox} Solicitação de Estoque",
                color=embed_color,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Solicitante", value=inter.user.mention, inline=True)
            embed.add_field(name="Produto", value=produto, inline=True)
            embed.add_field(name="Quantidade", value=str(quantidade), inline=True)
            if mensagem.strip():
                embed.add_field(name="Mensagem", value=mensagem.strip(), inline=False)
            
            request_msg = await channel.send(
                embed=embed,
                components=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Aprovar",
                            emoji=emoji.correct,
                            style=disnake.ButtonStyle.green,
                            custom_id=f"approve_stock_request:{request_id}"
                        ),
                        disnake.ui.Button(
                            label="Rejeitar",
                            emoji=emoji.wrong,
                            style=disnake.ButtonStyle.red,
                            custom_id=f"reject_stock_request:{request_id}"
                        )
                    )
                ]
            )
        
        # Salvar message_id
        requests_data["requests"][request_id]["message_id"] = request_msg.id
        db.save_document("loja_stock_requests", requests_data)
        
        await inter.response.send_message(
            f"{emoji.correct} Solicitação enviada com sucesso!",
            ephemeral=True
        )


class StockRequestModal(disnake.ui.Modal):
    """Modal para solicitar estoque"""
    
    def __init__(self, product_id: str):
        self.product_id = product_id
        
        components = [
            disnake.ui.TextInput(
                label="Nome do Produto",
                custom_id="product_name",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
                placeholder="Nome do produto que precisa de estoque"
            ),
            disnake.ui.TextInput(
                label="Quantidade Desejada",
                custom_id="quantity",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=10,
                placeholder="100",
                value="1"
            ),
            disnake.ui.TextInput(
                label="Mensagem Adicional",
                custom_id="message",
                style=disnake.TextInputStyle.paragraph,
                required=False,
                max_length=500,
                placeholder="Informações adicionais sobre a solicitação..."
            )
        ]
        super().__init__(title="Solicitar Estoque", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        product_name = inter.text_values.get("product_name", "").strip()
        quantity_str = inter.text_values.get("quantity", "1").strip()
        message_text = inter.text_values.get("message", "").strip()
        
        if not product_name:
            await inter.response.send_message(
                f"{emoji.wrong} Nome do produto não pode estar vazio!",
                ephemeral=True
            )
            return
        
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Quantidade inválida!",
                ephemeral=True
            )
            return
        
        # Obter configuração
        prefs = db.get_document("loja_preferences") or {}
        stock_requests = prefs.get("stock_requests", {})
        channel_id = stock_requests.get("channel_id")
        
        if not channel_id:
            await inter.response.send_message(
                f"{emoji.wrong} Canal de solicitações não configurado!",
                ephemeral=True
            )
            return
        
        channel = inter.guild.get_channel(int(channel_id)) if inter.guild else None
        if not channel:
            await inter.response.send_message(
                f"{emoji.wrong} Canal não encontrado!",
                ephemeral=True
            )
            return
        
        # Criar solicitação
        request_id = f"{inter.user.id}_{int(datetime.utcnow().timestamp())}"
        
        # Salvar solicitação
        requests_data = db.get_document("loja_stock_requests") or {}
        if not isinstance(requests_data, dict):
            requests_data = {}
        
        if "requests" not in requests_data:
            requests_data["requests"] = {}
        
        requests_data["requests"][request_id] = {
            "user_id": inter.user.id,
            "product_id": self.product_id,
            "product_name": product_name,
            "quantity": quantity,
            "message": message_text,
            "status": "pending",
            "created_at": int(datetime.utcnow().timestamp()),
            "guild_id": inter.guild.id if inter.guild else None
        }
        db.save_document("loja_stock_requests", requests_data)
        
        # Enviar mensagem no canal
        mode = db.get_document("custom_mode").get("mode", "embed")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        
        if mode == "components":
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            request_msg = await channel.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.cardbox}\n-# **Solicitação de Estoque**"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"-# **Solicitante:** {inter.user.mention}\n"
                            f"-# **Produto:** `{product_name}`\n"
                            f"-# **Quantidade:** `{quantity}`"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(f"-# **Mensagem:**\n{message_text}" if message_text else "-# Sem mensagem adicional"),
                        **container_kwargs
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Aprovar",
                            emoji=emoji.correct,
                            style=disnake.ButtonStyle.green,
                            custom_id=f"approve_stock_request:{request_id}"
                        ),
                        disnake.ui.Button(
                            label="Rejeitar",
                            emoji=emoji.wrong,
                            style=disnake.ButtonStyle.red,
                            custom_id=f"reject_stock_request:{request_id}"
                        )
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            embed_color = disnake.Color.blue()
            if primary_color_hex:
                try:
                    embed_color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except:
                    pass
            
            embed = disnake.Embed(
                title=f"{emoji.cardbox} Solicitação de Estoque",
                color=embed_color,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Solicitante", value=inter.user.mention, inline=True)
            embed.add_field(name="Produto", value=product_name, inline=True)
            embed.add_field(name="Quantidade", value=str(quantity), inline=True)
            if message_text:
                embed.add_field(name="Mensagem", value=message_text, inline=False)
            
            request_msg = await channel.send(
                embed=embed,
                components=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Aprovar",
                            emoji=emoji.correct,
                            style=disnake.ButtonStyle.green,
                            custom_id=f"approve_stock_request:{request_id}"
                        ),
                        disnake.ui.Button(
                            label="Rejeitar",
                            emoji=emoji.wrong,
                            style=disnake.ButtonStyle.red,
                            custom_id=f"reject_stock_request:{request_id}"
                        )
                    )
                ]
            )
        
        # Salvar message_id
        requests_data["requests"][request_id]["message_id"] = request_msg.id
        db.save_document("loja_stock_requests", requests_data)
        
        await inter.response.send_message(
            f"{emoji.correct} Solicitação enviada com sucesso!",
            ephemeral=True
        )


class StockRequestPanelModal(disnake.ui.Modal):
    """Modal que abre quando o usuário clica no botão do painel"""
    
    def __init__(self):
        components = [
            disnake.ui.TextInput(
                label="Nome do Produto",
                custom_id="product_name",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=100,
                placeholder="Nome do produto que precisa de estoque"
            ),
            disnake.ui.TextInput(
                label="Quantidade Desejada",
                custom_id="quantity",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=10,
                placeholder="100",
                value="1"
            ),
            disnake.ui.TextInput(
                label="Mensagem Adicional",
                custom_id="message",
                style=disnake.TextInputStyle.paragraph,
                required=False,
                max_length=500,
                placeholder="Informações adicionais sobre a solicitação..."
            )
        ]
        super().__init__(title="Solicitar Estoque", components=components)
    
    async def callback(self, inter: disnake.ModalInteraction):
        product_name = inter.text_values.get("product_name", "").strip()
        quantity_str = inter.text_values.get("quantity", "1").strip()
        message_text = inter.text_values.get("message", "").strip()
        
        if not product_name:
            await inter.response.send_message(
                f"{emoji.wrong} Nome do produto não pode estar vazio!",
                ephemeral=True
            )
            return
        
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError
        except ValueError:
            await inter.response.send_message(
                f"{emoji.wrong} Quantidade inválida!",
                ephemeral=True
            )
            return
        
        # Verificar se está habilitado
        prefs = db.get_document("loja_preferences") or {}
        stock_requests = prefs.get("stock_requests", {})
        
        if not stock_requests.get("enabled", False):
            await inter.response.send_message(
                f"{emoji.wrong} Sistema de solicitação de estoque está desativado.",
                ephemeral=True
            )
            return
        
        # Verificar cargo se configurado
        role_id = stock_requests.get("role_id")
        if role_id:
            member = inter.guild.get_member(inter.user.id) if inter.guild else None
            if not member or not any(role.id == int(role_id) for role in member.roles):
                await inter.response.send_message(
                    f"{emoji.wrong} Você não tem permissão para solicitar estoque.",
                    ephemeral=True
                )
                return
        
        # Verificar se está no servidor principal
        if not is_main_server(inter.guild_id):
            await inter.response.send_message(
                f"{emoji.wrong} Este comando só pode ser usado no servidor principal.",
                ephemeral=True
            )
            return
        
        # Processar solicitação
        channel_id = stock_requests.get("channel_id")
        
        if not channel_id:
            await inter.response.send_message(
                f"{emoji.wrong} Canal de solicitações não configurado!",
                ephemeral=True
            )
            return
        
        channel = inter.guild.get_channel(int(channel_id)) if inter.guild else None
        if not channel:
            await inter.response.send_message(
                f"{emoji.wrong} Canal não encontrado!",
                ephemeral=True
            )
            return
        
        # Criar solicitação
        request_id = f"{inter.user.id}_{int(datetime.utcnow().timestamp())}"
        
        # Salvar solicitação
        requests_data = db.get_document("loja_stock_requests") or {}
        if not isinstance(requests_data, dict):
            requests_data = {}
        
        if "requests" not in requests_data:
            requests_data["requests"] = {}
        
        requests_data["requests"][request_id] = {
            "user_id": inter.user.id,
            "product_id": None,
            "product_name": product_name,
            "quantity": quantity,
            "message": message_text,
            "status": "pending",
            "created_at": int(datetime.utcnow().timestamp()),
            "guild_id": inter.guild.id if inter.guild else None
        }
        db.save_document("loja_stock_requests", requests_data)
        
        # Enviar mensagem no canal
        mode = db.get_document("custom_mode").get("mode", "embed")
        colors = db.get_document("custom_colors") or {}
        primary_color_hex = colors.get("primary")
        
        if mode == "components":
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
            request_msg = await channel.send(
                components=[
                    disnake.ui.Container(
                        disnake.ui.TextDisplay(f"# {emoji.cardbox}\n-# **Solicitação de Estoque**"),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(
                            f"-# **Solicitante:** {inter.user.mention}\n"
                            f"-# **Produto:** `{product_name}`\n"
                            f"-# **Quantidade:** `{quantity}`"
                        ),
                        disnake.ui.Separator(),
                        disnake.ui.TextDisplay(f"-# **Mensagem:**\n{message_text}" if message_text else "-# Sem mensagem adicional"),
                        **container_kwargs
                    ),
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Aprovar",
                            emoji=emoji.correct,
                            style=disnake.ButtonStyle.green,
                            custom_id=f"approve_stock_request:{request_id}"
                        ),
                        disnake.ui.Button(
                            label="Rejeitar",
                            emoji=emoji.wrong,
                            style=disnake.ButtonStyle.red,
                            custom_id=f"reject_stock_request:{request_id}"
                        )
                    )
                ],
                flags=disnake.MessageFlags(is_components_v2=True)
            )
        else:
            embed_color = disnake.Color.blue()
            if primary_color_hex:
                try:
                    embed_color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except:
                    pass
            
            embed = disnake.Embed(
                title=f"{emoji.cardbox} Solicitação de Estoque",
                color=embed_color,
                timestamp=datetime.utcnow()
            )
            embed.add_field(name="Solicitante", value=inter.user.mention, inline=True)
            embed.add_field(name="Produto", value=product_name, inline=True)
            embed.add_field(name="Quantidade", value=str(quantity), inline=True)
            if message_text:
                embed.add_field(name="Mensagem", value=message_text, inline=False)
            
            request_msg = await channel.send(
                embed=embed,
                components=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Aprovar",
                            emoji=emoji.correct,
                            style=disnake.ButtonStyle.green,
                            custom_id=f"approve_stock_request:{request_id}"
                        ),
                        disnake.ui.Button(
                            label="Rejeitar",
                            emoji=emoji.wrong,
                            style=disnake.ButtonStyle.red,
                            custom_id=f"reject_stock_request:{request_id}"
                        )
                    )
                ]
            )
        
        # Salvar message_id
        requests_data["requests"][request_id]["message_id"] = request_msg.id
        db.save_document("loja_stock_requests", requests_data)
        
        await inter.response.send_message(
            f"{emoji.correct} Solicitação enviada com sucesso!",
            ephemeral=True
        )


class StockRequestModeration(commands.Cog):
    """Handler para aprovar/rejeitar solicitações e abrir modal do painel"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener("on_button_click")
    async def on_moderate_stock_request(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "StockRequest_OpenModal":
            # Abrir modal para solicitar estoque
            await inter.response.send_modal(StockRequestPanelModal())
            return
        
        if custom_id.startswith("approve_stock_request:") or custom_id.startswith("reject_stock_request:"):
            # Verificar permissão (admin)
            cargos_data = db.get_document("cargos") or {}
            cargo_admin_id = cargos_data.get("cargo_admin")
            
            is_admin = inter.author.guild_permissions.administrator
            has_admin_role = False
            if cargo_admin_id:
                has_admin_role = any(role.id == int(cargo_admin_id) for role in inter.author.roles)
            
            if not (is_admin or has_admin_role):
                await inter.response.send_message(
                    f"{emoji.wrong} Você não tem permissão para moderar solicitações!",
                    ephemeral=True
                )
                return
            
            action = "approve" if custom_id.startswith("approve_stock_request:") else "reject"
            request_id = custom_id.split(":")[1] if ":" in custom_id else None
            
            if not request_id:
                await inter.response.send_message(
                    f"{emoji.wrong} Erro ao processar solicitação.",
                    ephemeral=True
                )
                return
            
            # Carregar solicitação
            requests_data = db.get_document("loja_stock_requests") or {}
            request = requests_data.get("requests", {}).get(request_id)
            
            if not request:
                await inter.response.send_message(
                    f"{emoji.wrong} Solicitação não encontrada!",
                    ephemeral=True
                )
                return
            
            if request.get("status") != "pending":
                await inter.response.send_message(
                    f"{emoji.wrong} Esta solicitação já foi processada!",
                    ephemeral=True
                )
                return
            
            # Atualizar status
            requests_data["requests"][request_id]["status"] = "approved" if action == "approve" else "rejected"
            requests_data["requests"][request_id]["moderated_by"] = inter.author.id
            requests_data["requests"][request_id]["moderated_at"] = int(datetime.utcnow().timestamp())
            db.save_document("loja_stock_requests", requests_data)
            
            # Atualizar mensagem
            mode = db.get_document("custom_mode").get("mode", "embed")
            colors = db.get_document("custom_colors") or {}
            primary_color_hex = colors.get("primary")
            
            status_emoji = emoji.correct if action == "approve" else emoji.wrong
            status_text = "Aprovada" if action == "approve" else "Rejeitada"
            status_color = disnake.Color.green() if action == "approve" else disnake.Color.red()
            
            if mode == "components":
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                await inter.response.edit_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {status_emoji}\n-# **Solicitação {status_text}**"),
                            disnake.ui.Separator(),
                            disnake.ui.TextDisplay(
                                f"-# **Solicitante:** {inter.guild.get_member(request['user_id']).mention if inter.guild.get_member(request['user_id']) else 'Usuário não encontrado'}\n"
                                f"-# **Produto:** `{request['product_name']}`\n"
                                f"-# **Quantidade:** `{request['quantity']}`\n"
                                f"-# **Status:** {status_text} por {inter.author.mention}"
                            ),
                            **container_kwargs
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            else:
                embed = disnake.Embed(
                    title=f"{status_emoji} Solicitação {status_text}",
                    color=status_color,
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Solicitante", value=inter.guild.get_member(request['user_id']).mention if inter.guild.get_member(request['user_id']) else 'Usuário não encontrado', inline=True)
                embed.add_field(name="Produto", value=request['product_name'], inline=True)
                embed.add_field(name="Quantidade", value=str(request['quantity']), inline=True)
                embed.add_field(name="Status", value=f"{status_text} por {inter.author.mention}", inline=False)
                
                await inter.response.edit_message(embed=embed, components=[])
            
            # Notificar usuário
            try:
                user = await inter.bot.fetch_user(request['user_id'])
                if user:
                    if mode == "components":
                        container_kwargs = {}
                        if primary_color_hex:
                            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                        
                        await user.send(
                            components=[
                                disnake.ui.Container(
                                    disnake.ui.TextDisplay(f"# {status_emoji}\n-# **Solicitação {status_text}**"),
                                    disnake.ui.Separator(),
                                    disnake.ui.TextDisplay(
                                        f"-# Sua solicitação de estoque foi {status_text.lower()}.\n\n"
                                        f"-# **Produto:** `{request['product_name']}`\n"
                                        f"-# **Quantidade:** `{request['quantity']}`"
                                    ),
                                    **container_kwargs
                                )
                            ],
                            flags=disnake.MessageFlags(is_components_v2=True)
                        )
                    else:
                        embed = disnake.Embed(
                            title=f"{status_emoji} Solicitação {status_text}",
                            description=f"Sua solicitação de estoque foi {status_text.lower()}.",
                            color=status_color
                        )
                        embed.add_field(name="Produto", value=request['product_name'], inline=True)
                        embed.add_field(name="Quantidade", value=str(request['quantity']), inline=True)
                        await user.send(embed=embed)
            except:
                pass


def setup(bot: commands.Bot):
    bot.add_cog(StockRequestPreferences(bot))
    bot.add_cog(StockRequestCommand(bot))
    bot.add_cog(StockRequestModeration(bot))
