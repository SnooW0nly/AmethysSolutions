"""
Sistema de Saldo - Cog principal
Gerencia configurações do sistema de saldo e listeners
"""
import disnake
from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .config_panel import panel_embed, panel_components
from .bonus_modal import BonusModal
from .rules_modal import RulesModal


class SaldoSystem(commands.Cog):
    """Sistema de Saldo para a loja"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    def get_config(self) -> dict:
        """Obtém configuração do sistema de saldo"""
        return db.get_document("loja_saldo_config") or self._get_default_config()
    
    def save_config(self, config: dict):
        """Salva configuração do sistema de saldo"""
        db.save_document("loja_saldo_config", config)
    
    def _get_default_config(self) -> dict:
        """Retorna configuração padrão"""
        return {
            "enabled": False,
            "bonus": {
                "type": "disabled",  # disabled, percentage, fixed
                "value": 0
            },
            "rules": {
                "max_usage_percentage": 100,
                "max_usage_amount": None,
                "min_usage_amount": 0,
                "allow_partial_payment": True
            },
            "deposit_panel": {
                "message_style": "embed",
                "embed": {
                    "title": "Depositar Saldo",
                    "description": "Clique no botão abaixo para fazer um depósito de saldo.",
                    "color": "#5c5ef0",
                    "image_url": None,
                    "thumbnail_url": None
                },
                "content": {
                    "content": "Clique no botão abaixo para fazer um depósito de saldo.",
                    "image_url": None
                },
                "container": {
                    "content": "Clique no botão abaixo para fazer um depósito de saldo.",
                    "color": "#5c5ef0",
                    "image_url": None,
                    "thumbnail_url": None
                },
                "button": {
                    "label": "Depositar",
                    "emoji": None,
                    "style": "green"
                },
                "channel_id": None,
                "message_id": None,
                "category_id": None
            },
            "deposit_settings": {
                "min_deposit": 5.00,
                "max_deposit": 1000.00,
                "terms": None,
                "notify_role_id": None
            }
        }
    
    def panel(self, inter: disnake.MessageInteraction) -> dict:
        """Retorna o painel de configuração do sistema de saldo"""
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            return panel_embed(inter, self.get_config())
        return panel_components(inter, self.get_config())
    
    # === LISTENERS ===
    
    @commands.Cog.listener("on_button_click")
    async def on_saldo_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Voltar ao painel de saldo
        if custom_id == "Saldo_Panel":
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            
            panel_data = self.panel(inter)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Ligar/Desligar sistema
        elif custom_id == "Saldo_Toggle":
            config = self.get_config()
            config["enabled"] = not config.get("enabled", False)
            self.save_config(config)
            
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            
            panel_data = self.panel(inter)
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Definir Bônus
        elif custom_id == "Saldo_Bonus":
            config = self.get_config()
            await inter.response.send_modal(BonusModal(config))
        
        # Definir Regras
        elif custom_id == "Saldo_Rules":
            config = self.get_config()
            await inter.response.send_modal(RulesModal(config))
        
        # Painel de Depósito
        elif custom_id == "Saldo_DepositPanel":
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            
            from .deposit_panel.editor import deposit_panel_editor_embed, deposit_panel_editor_components
            if mode == "embed":
                panel_data = deposit_panel_editor_embed(inter, self.get_config())
            else:
                panel_data = deposit_panel_editor_components(inter, self.get_config())
            
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Opções (Admin)
        elif custom_id == "Saldo_Options":
            # Verificar se é admin
            from functions.perms import perms as perms_check
            is_admin = await perms_check.check(inter.user.id)
            
            if not is_admin:
                await inter.response.send_message(
                    f"{emoji.wrong} Apenas administradores podem acessar as opções.",
                    ephemeral=True
                )
                return
            
            mode = db.get_document("custom_mode").get("mode")
            color_data = db.get_document("custom_colors") or {}
            primary_color_hex = color_data.get("primary")
            
            if mode == "components":
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                await inter.response.edit_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.settings2} Opções de Saldo"),
                            disnake.ui.Separator(),
                            disnake.ui.TextDisplay("Selecione uma ação administrativa:"),
                            disnake.ui.ActionRow(
                                disnake.ui.StringSelect(
                                    placeholder="Selecione uma ação",
                                    custom_id="Saldo_AdminAction",
                                    options=[
                                        disnake.SelectOption(
                                            label="Adicionar saldo a usuário",
                                            value="add_balance",
                                            emoji=emoji.plus if hasattr(emoji, "plus") else "➕"
                                        ),
                                        disnake.SelectOption(
                                            label="Remover saldo de usuário",
                                            value="remove_balance",
                                            emoji=emoji.minus if hasattr(emoji, "minus") else "➖"
                                        ),
                                        disnake.SelectOption(
                                            label="Transferir saldo",
                                            value="transfer_balance",
                                            emoji=emoji.arrow if hasattr(emoji, "arrow") else "↔️"
                                        )
                                    ]
                                )
                            ),
                            **container_kwargs
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(
                                label="Voltar",
                                emoji=emoji.back,
                                style=disnake.ButtonStyle.grey,
                                custom_id="Saldo_Panel"
                            )
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True)
                )
            else:
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                
                embed = disnake.Embed(
                    title=f"{emoji.settings} Opções de Saldo",
                    description="Selecione uma ação administrativa:",
                    **embed_kwargs
                )
                
                await inter.response.edit_message(
                    embed=embed,
                    components=[
                        disnake.ui.ActionRow(
                            disnake.ui.StringSelect(
                                placeholder="Selecione uma ação",
                                custom_id="Saldo_AdminAction",
                                options=[
                                    disnake.SelectOption(
                                        label="Adicionar saldo a usuário",
                                        value="add_balance",
                                        emoji="➕"
                                    ),
                                    disnake.SelectOption(
                                        label="Remover saldo de usuário",
                                        value="remove_balance",
                                        emoji="➖"
                                    ),
                                    disnake.SelectOption(
                                        label="Transferir saldo",
                                        value="transfer_balance",
                                        emoji="↔️"
                                    )
                                ]
                            )
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(
                                label="Voltar",
                                emoji=emoji.back,
                                style=disnake.ButtonStyle.grey,
                                custom_id="Saldo_Panel"
                            )
                        )
                    ]
                )
        
        # === Botões do Editor de Painel de Depósito ===
        
        # Ciclar estilo
        elif custom_id == "DepositPanel_CycleStyle":
            config = self.get_config()
            deposit_panel = config.get("deposit_panel", {})
            current_style = deposit_panel.get("message_style", "embed")
            
            styles = ["embed", "content", "container"]
            current_index = styles.index(current_style) if current_style in styles else 0
            new_index = (current_index + 1) % len(styles)
            new_style = styles[new_index]
            
            config.setdefault("deposit_panel", {})["message_style"] = new_style
            self.save_config(config)
            
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            
            from .deposit_panel.editor import deposit_panel_editor_embed, deposit_panel_editor_components
            if mode == "embed":
                panel_data = deposit_panel_editor_embed(inter, config)
            else:
                panel_data = deposit_panel_editor_components(inter, config)
            
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Editar conteúdo
        elif custom_id == "DepositPanel_EditContent":
            config = self.get_config()
            style = config.get("deposit_panel", {}).get("message_style", "embed")
            
            from .deposit_panel.editor import EditEmbedModal, EditContentModal, EditContainerModal
            
            if style == "embed":
                data = config.get("deposit_panel", {}).get("embed", {})
                await inter.response.send_modal(EditEmbedModal(data))
            elif style == "content":
                data = config.get("deposit_panel", {}).get("content", {})
                await inter.response.send_modal(EditContentModal(data))
            elif style == "container":
                data = config.get("deposit_panel", {}).get("container", {})
                await inter.response.send_modal(EditContainerModal(data))
        
        # Editar botão
        elif custom_id == "DepositPanel_EditButton":
            config = self.get_config()
            from .deposit_panel.editor import EditButtonModal
            data = config.get("deposit_panel", {}).get("button", {})
            await inter.response.send_modal(EditButtonModal(data))
        
        # Enviar painel (abre painel de seleção de canal)
        elif custom_id == "DepositPanel_Send":
            mode = db.get_document("custom_mode").get("mode")
            color_data = db.get_document("custom_colors") or {}
            primary_color_hex = color_data.get("primary")
            
            if mode == "components":
                container_kwargs = {}
                if primary_color_hex:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                await inter.response.send_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# **Publicar Painel de Depósito**"),
                            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                            disnake.ui.TextDisplay("Selecione o canal onde o painel de depósito será enviado."),
                            disnake.ui.ActionRow(
                                disnake.ui.ChannelSelect(
                                    placeholder="Selecione um canal",
                                    channel_types=[disnake.ChannelType.text],
                                    custom_id="DepositPanel_ChannelSelect"
                                )
                            ),
                            **container_kwargs
                        )
                    ],
                    flags=disnake.MessageFlags(is_components_v2=True),
                    ephemeral=True
                )
            else:
                embed_kwargs = {}
                if primary_color_hex:
                    embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                
                embed = disnake.Embed(
                    title="Publicar Painel de Depósito",
                    description="Selecione o canal onde o painel de depósito será enviado.",
                    **embed_kwargs
                )
                
                await inter.response.send_message(
                    embed=embed,
                    components=[
                        disnake.ui.ActionRow(
                            disnake.ui.ChannelSelect(
                                placeholder="Selecione um canal",
                                channel_types=[disnake.ChannelType.text],
                                custom_id="DepositPanel_ChannelSelect"
                            )
                        )
                    ],
                    ephemeral=True
                )
        
        # Preview do painel
        elif custom_id == "DepositPanel_Preview":
            config = self.get_config()
            deposit_panel = config.get("deposit_panel", {})
            style = deposit_panel.get("message_style", "embed")
            content_data = deposit_panel.get(style, {})
            button_data = deposit_panel.get("button", {})
            
            # Construir botão (desativado para preview)
            button_style_map = {
                "green": disnake.ButtonStyle.success,
                "grey": disnake.ButtonStyle.secondary,
                "red": disnake.ButtonStyle.danger,
                "blue": disnake.ButtonStyle.primary
            }
            
            preview_button = disnake.ui.Button(
                label=button_data.get("label", "Depositar"),
                style=button_style_map.get(button_data.get("style", "green"), disnake.ButtonStyle.success),
                disabled=True,
                custom_id="preview_disabled"
            )
            action_row = disnake.ui.ActionRow(preview_button)
            
            if style == "embed":
                try:
                    color_str = content_data.get("color", "#5c5ef0").lstrip("#")
                    color = disnake.Color(int(color_str, 16))
                except:
                    color = disnake.Color.default()
                
                embed = disnake.Embed(
                    title=content_data.get("title"),
                    description=content_data.get("description"),
                    color=color
                )
                
                if image_url := content_data.get("image_url"):
                    embed.set_image(url=image_url)
                
                await inter.response.send_message(
                    embed=embed,
                    components=[action_row],
                    ephemeral=True
                )
            elif style == "content":
                await inter.response.send_message(
                    content=content_data.get("content", ""),
                    components=[action_row],
                    ephemeral=True
                )
            elif style == "container":
                from modules.tickets.config.container_utils import ContainerUtils
                
                container = ContainerUtils.montar_container(
                    conteudo=content_data.get("content"),
                    imagem_url=content_data.get("image_url"),
                    cor_hex=content_data.get("color"),
                    extra_children=[action_row]
                )
                
                await inter.response.send_message(
                    components=[container],
                    flags=disnake.MessageFlags(is_components_v2=True),
                    ephemeral=True
                )
    
    @commands.Cog.listener("on_dropdown")
    async def on_deposit_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Select de estilo do painel (legado, mantido por compatibilidade)
        if custom_id == "DepositPanel_StyleSelect":
            new_style = inter.values[0]
            
            config = self.get_config()
            config.setdefault("deposit_panel", {})["message_style"] = new_style
            self.save_config(config)
            
            mode = db.get_document("custom_mode").get("mode")
            msg_handler = embed_message if mode == "embed" else message
            await msg_handler.wait(inter, send=False)
            
            from .deposit_panel.editor import deposit_panel_editor_embed, deposit_panel_editor_components
            if mode == "embed":
                panel_data = deposit_panel_editor_embed(inter, config)
            else:
                panel_data = deposit_panel_editor_components(inter, config)
            
            if "embed" in panel_data:
                await inter.edit_original_message(content=None, **panel_data)
            else:
                await inter.edit_original_message(**panel_data, flags=disnake.MessageFlags(is_components_v2=True))
        
        # Channel select para publicar painel
        elif custom_id == "DepositPanel_ChannelSelect":
            if not inter.values:
                await inter.response.send_message(
                    f"{emoji.wrong} Nenhum canal selecionado.",
                    ephemeral=True
                )
                return
            
            # Obter canal resolvido
            channel_id = int(inter.values[0])
            channel = self.bot.get_channel(channel_id)
            
            if not channel:
                await inter.response.send_message(
                    f"{emoji.wrong} Canal não encontrado.",
                    ephemeral=True
                )
                return
            
            # Salvar canal na config
            config = self.get_config()
            config.setdefault("deposit_panel", {})["channel_id"] = channel.id
            self.save_config(config)
            
            await inter.response.defer(ephemeral=True)
            
            # Enviar o painel
            from .deposit_panel.send_panel import send_deposit_panel
            await send_deposit_panel(inter, self.bot, channel)
        
        # Handler para ações administrativas de saldo
        elif custom_id == "Saldo_AdminAction":
            if not inter.values:
                await inter.response.send_message(
                    f"{emoji.wrong} Nenhuma ação selecionada.",
                    ephemeral=True
                )
                return
            
            action = inter.values[0]
            
            # Opção em desenvolvimento
            if action == "transfer_balance":
                await inter.response.send_message(
                    f"{emoji.warn} Transferência de saldo estará disponível em breve!",
                    ephemeral=True
                )
                return
            
            # Adicionar saldo
            if action == "add_balance":
                modal = disnake.ui.Modal(
                    title="Adicionar Saldo",
                    custom_id="admin_add_balance_modal",
                    components=[
                        disnake.ui.TextInput(
                            label="ID do Usuário",
                            placeholder="Ex: 123456789012345678",
                            custom_id="user_id",
                            required=True,
                            max_length=20
                        ),
                        disnake.ui.TextInput(
                            label="Valor a Adicionar (R$)",
                            placeholder="Ex: 50.00",
                            custom_id="amount",
                            required=True,
                            max_length=10
                        )
                    ]
                )
                await inter.response.send_modal(modal)
            
            # Remover saldo
            elif action == "remove_balance":
                modal = disnake.ui.Modal(
                    title="Remover Saldo",
                    custom_id="admin_remove_balance_modal",
                    components=[
                        disnake.ui.TextInput(
                            label="ID do Usuário",
                            placeholder="Ex: 123456789012345678",
                            custom_id="user_id",
                            required=True,
                            max_length=20
                        ),
                        disnake.ui.TextInput(
                            label="Valor a Remover (R$)",
                            placeholder="Ex: 25.00",
                            custom_id="amount",
                            required=True,
                            max_length=10
                        )
                    ]
                )
                await inter.response.send_modal(modal)
    
    @commands.Cog.listener("on_modal_submit")
    async def on_admin_balance_modal(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id
        
        # Modal de adicionar saldo
        if custom_id == "admin_add_balance_modal":
            try:
                user_id = int(inter.text_values["user_id"])
                amount = float(inter.text_values["amount"].replace(",", "."))
                
                if amount <= 0:
                    await inter.response.send_message(
                        f"{emoji.wrong} O valor deve ser maior que zero.",
                        ephemeral=True
                    )
                    return
                
                # Adicionar saldo
                from .balance_manager import BalanceManager
                BalanceManager.add_balance(user_id, amount, bonus=0, deposit_id="admin_add")
                
                await inter.response.send_message(
                    f"{emoji.correct} Saldo de R$ {amount:.2f} adicionado ao usuário <@{user_id}>!",
                    ephemeral=True
                )
            except ValueError:
                await inter.response.send_message(
                    f"{emoji.wrong} ID do usuário ou valor inválido. Use apenas números.",
                    ephemeral=True
                )
            except Exception as e:
                await inter.response.send_message(
                    f"{emoji.wrong} Erro ao adicionar saldo: {str(e)}",
                    ephemeral=True
                )
        
        # Modal de remover saldo
        elif custom_id == "admin_remove_balance_modal":
            try:
                user_id = int(inter.text_values["user_id"])
                amount = float(inter.text_values["amount"].replace(",", "."))
                
                if amount <= 0:
                    await inter.response.send_message(
                        f"{emoji.wrong} O valor deve ser maior que zero.",
                        ephemeral=True
                    )
                    return
                
                # Verificar se usuário tem saldo suficiente
                from .balance_manager import BalanceManager
                current_balance = BalanceManager.get_user_balance(user_id)
                
                if current_balance < amount:
                    await inter.response.send_message(
                        f"{emoji.wrong} Usuário possui apenas R$ {current_balance:.2f} de saldo.",
                        ephemeral=True
                    )
                    return
                
                # Remover saldo
                success, message = BalanceManager.use_balance(
                    user_id, 
                    amount, 
                    reference_id="admin_remove",
                    description="Remoção manual pelo admin"
                )
                
                if success:
                    await inter.response.send_message(
                        f"{emoji.correct} Saldo de R$ {amount:.2f} removido do usuário <@{user_id}>!",
                        ephemeral=True
                    )
                else:
                    await inter.response.send_message(
                        f"{emoji.wrong} Erro ao remover saldo: {message}",
                        ephemeral=True
                    )
            except ValueError:
                await inter.response.send_message(
                    f"{emoji.wrong} ID do usuário ou valor inválido. Use apenas números.",
                    ephemeral=True
                )
            except Exception as e:
                await inter.response.send_message(
                    f"{emoji.wrong} Erro ao remover saldo: {str(e)}",
                    ephemeral=True
                )


def setup(bot: commands.Bot):
    bot.add_cog(SaldoSystem(bot))

