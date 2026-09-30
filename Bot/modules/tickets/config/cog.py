import disnake
from disnake.ext import commands
import aiohttp
import io
from functions.database import database as db
from functions.message import message, embed_message
from functions.emoji import emoji
from .config_ticket import PainelTicket_components, PainelTicket_embed
from .create_panel import CreateTicketPanelModal
from .edit_panel import (
    EditPanelView_components,
    EditPanelView_embed,
    SpecificPanelView_components,
    SpecificPanelView_embed,
    ChannelSelectView_components,
    ChannelSelectView_embed,
    CategorySelectView_components,
    CategorySelectView_embed
)
from .edit_message import (
    MessageEditView_components,
    MessageEditView_embed,
    EditEmbedModal,
    EditContentModal,
    EditContainerModal,
    MessageEditSelectionView_components,
    MessageEditSelectionView_embed,
    EditTicketMessageModal,
    MessageSubtypePreviewView,
    MessagePreviewSelectionView_components,
    MessagePreviewSelectionView_embed,
    MessageSubtypePreviewSelect,
    show_prefixes_panel
)
from .edit_message_open import (
    OpenMessageEditView_components,
    OpenMessageEditView_embed,
    EditOpenEmbedModal,
    EditOpenContentModal,
    EditOpenContainerModal,
    OpenMessageOptionSelectView_components,
    OpenMessageOptionSelectView_embed
)
from .edit_button import EditButtonModal
from .send_panel import send_panel
from .horario import OfficeHoursModal
from .config_ia import ConfigIAView_components, ConfigIAView_embed, EditIAPromptModal
from .config_roles import (
    RolesConfigView_components, 
    RolesConfigView_embed, 
    RoleSelectView_components, 
    RoleSelectView_embed,
    RolesOptionSelectView_components,
    RolesOptionSelectView_embed
)
from .container_utils import ContainerUtils
from .preferencias import PreferenciasView_components, PreferenciasView_embed
from .preferences.transcripts import TranscriptsView_components, TranscriptsView_embed
from .preferences.setup_members import MemberSetupView_components, MemberSetupView_embed
from .preferences.setup_team import TeamSetupView_components, TeamSetupView_embed
from .preferences.close_tickets import CloseTicketsView_components, CloseTicketsView_embed, SetInactiveModal, SetTimeCloseModal
from .preferences.form import (
    config_form_select_components, 
    config_form_select_embed, 
    config_form_editor_components, 
    config_form_editor_embed,
    QuestionModal
)
from .create_options import AddOptionModal, create_options_components, create_options_embed
from .config_opcoes import config_options_components, config_options_embed, EditOptionModal
from ..utils import SafeFormatter

MODAL_CONFIGS = {
    "CloseMessage": {
        "title": "Editar Mensagem de Fechamento",
        "fields": {
            "close_message": {
                "label": "Mensagem (sem motivo)",
                "description": "Enviada na DM ao fechar sem motivo.",
                "emoji": emoji.arrow
            },
            "close_message_reason": {
                "label": "Mensagem (com motivo)",
                "description": "Enviada na DM ao fechar com motivo.",
                "emoji": emoji.arrow
            }
        }
    },
    "NotifyMessage": {
        "title": "Editar Mensagem de Notificação",
        "fields": {
            "notify_message_staff_to_user": {
                "label": "Notificação para Usuário",
                "description": "Enviada no ticket para notificar o usuário.",
                "emoji": emoji.arrow
            },
            "notify_message_user_to_staff": {
                "label": "Notificação para Staff",
                "description": "Enviada no ticket para notificar a equipe.",
                "emoji": emoji.arrow
            }
        }
    },
    "AddUserMessage": {
        "title": "Editar Mensagem de Adicionar Usuário",
        "fields": {
            "add_user_message": {
                "label": "Mensagem ao adicionar",
                "description": "Enviada no ticket quando um usuário é adicionado.",
                "emoji": emoji.arrow
            },
            "add_user_dm_message": {
                "label": "Mensagem na DM ao adicionar",
                "description": "Enviada na DM do usuário que foi adicionado.",
                "emoji": emoji.arrow
            }
        }
    },
    "RemoveUserMessage": {
        "title": "Editar Mensagem de Remover Usuário",
        "fields": {
            "remove_user_message": {
                "label": "Mensagem ao remover",
                "description": "Enviada no ticket quando um usuário é removido.",
                "emoji": emoji.arrow
            },
            "remove_user_dm_message": {
                "label": "Mensagem na DM ao remover",
                "description": "Enviada na DM do usuário que foi removido.",
                "emoji": emoji.arrow
            }
        }
    },
    "AssumeMessage": {
        "title": "Editar Mensagem de Assumir Ticket",
        "fields": {
            "assume_message": {
                "label": "Mensagem no canal do ticket",
                "description": "Enviada no ticket quando um atendente assume.",
                "emoji": emoji.arrow
            },
            "assume_dm_message": {
                "label": "Mensagem na DM do usuário",
                "description": "Enviada na DM do usuário quando um atendente assume.",
                "emoji": emoji.arrow
            }
        }
    },
    "TransferMessage": {
        "title": "Editar Mensagem de Transferir",
        "fields": {
            "transfer_message": {
                "label": "Mensagem ao transferir",
                "description": "Enviada no ticket quando é transferido.",
                "emoji": emoji.arrow
            }
        }
    },
    "CreateCallMessage": {
        "title": "Editar Mensagens de Call",
        "fields": {
            "create_call_message": {
                "label": "Mensagem no ticket ao criar call",
                "description": "Enviada no ticket quando uma call é criada.",
                "emoji": emoji.arrow
            },
            "create_call_dm_message": {
                "label": "Mensagem na DM ao criar call",
                "description": "Enviada na DM do usuário quando uma call é criada.",
                "emoji": emoji.arrow
            },
            "request_call_message": {
                "label": "Mensagem ao solicitar call",
                "description": "Enviada no ticket quando um usuário solicita call.",
                "emoji": emoji.arrow
            }
        }
    },
    "TranscriptMessage": {
        "title": "Editar Mensagem de Transcript",
        "fields": {
            "transcript_message": {
                "label": "Mensagem (Fechamento de Ticket)",
                "description": "Enviada na DM com transcript ao fechar.",
                "emoji": emoji.arrow
            },
            "transcript_dm_message": {
                "label": "Mensagem (Solicitação)",
                "description": "Enviada na DM com transcript ao solicitar.",
                "emoji": emoji.arrow
            }
        }
    }
}

class TicketConfigCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def display_ticket_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter)
            embed, components = PainelTicket_embed(inter)
            await self._handle_embed_edit(inter, embed, components)
        else:
            await message.wait(inter)
            components = PainelTicket_components(inter)
            await inter.edit_original_message(content=None, components=components)

    async def _handle_embed_edit(self, inter: disnake.MessageInteraction, embed, components):
        """
        Handles editing a message to an embed, safely swapping from a V2 component message if necessary.
        This uses a try/except block because the is_components_v2 flag can be unreliable.
        """
        try:
            # Optimistically try to edit. This works for embed -> embed or V1 -> embed.
            await inter.edit_original_message(content=None, embed=embed, components=components)
        except disnake.errors.HTTPException as e:
            # If it fails with the specific V2 error, it means we are in the V2 -> embed case.
            # So, we delete and send a new message.
            if e.code == 50035:  # Invalid Form Body
                try:
                    is_ephemeral = inter.message.flags.ephemeral
                    await inter.delete_original_message()
                    await inter.followup.send(embed=embed, components=components, ephemeral=is_ephemeral)
                except (disnake.errors.NotFound, disnake.errors.HTTPException):
                    # The interaction or message might be gone if there's a big delay.
                    # In this case, we can't do anything.
                    pass
            else:
                # Re-raise other HTTP exceptions.
                raise e

    async def _mode_aware_wait(self, inter: disnake.MessageInteraction):
        """
        Sends a 'wait' message that respects the current display mode.
        """
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

    @commands.Cog.listener("on_button_click")
    async def ticket_button_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Só processa se for um botão relacionado ao sistema de tickets
        if not (custom_id.startswith("Ticket") or custom_id.startswith("ticket_panel_")):
            return
        
        # --- Navegação Principal ---
        if custom_id == "Ticket_CriarPainel":
            await inter.response.send_modal(CreateTicketPanelModal(inter))
        elif custom_id == "Ticket_EditarPainel":
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=EditPanelView_components())
            else:
                embed, components = EditPanelView_embed(inter)
                await self._handle_embed_edit(inter, embed, components)

        elif custom_id == "Ticket_ToggleAllPanels":
            await self._mode_aware_wait(inter)
            config = db.get_document("tickets_config") or {}
            panels = config.get("panels", {})
            
            if not panels:
                return

            any_panel_enabled = any(p.get("enabled", False) for p in panels.values())
            new_status = not any_panel_enabled

            for panel_id in panels:
                panels[panel_id]["enabled"] = new_status
            
            db.save_document("tickets_config", config)
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=PainelTicket_components(inter))
            else:
                embed, components = PainelTicket_embed(inter)
                await self._handle_embed_edit(inter, embed, components)

        # --- Ações do Painel de Edição (`TicketEdit_`) ---
        elif custom_id.startswith("TicketEdit_"):
            try:
                _, action, panel_id = custom_id.split("_", 2)
            except ValueError:
                return
            
            await self.handle_panel_edit_actions(inter, action, panel_id)

        # --- Ações da Configuração de IA (`TicketIA_`) ---
        elif custom_id.startswith("TicketIA_"):
            try:
                _, action, panel_id = custom_id.split("_", 2)
            except ValueError:
                return

            await self.handle_ia_config_actions(inter, action, panel_id)

        # --- Ações da Edição de Mensagem (`TicketMsgEdit_`) ---
        elif custom_id.startswith("TicketMsgEdit_"):
            try:
                _, action, panel_id = custom_id.split("_", 2)
            except ValueError:
                return

            await self.handle_message_edit_actions(inter, action, panel_id)

        # --- Ações da Edição de Mensagem de Abertura (`TicketOpenMsgEdit_`) ---
        elif custom_id.startswith("TicketOpenMsgEdit_"):
            try:
                parts = custom_id.split("_")
                action = parts[1]
                panel_id = parts[2]
                option_id = parts[3] if len(parts) > 3 else None
            except IndexError:
                return

            await self.handle_open_message_edit_actions(inter, action, panel_id, option_id)

        elif custom_id.startswith("TicketOpenMsg_"):
            try:
                _, action, panel_id = custom_id.split("_", 2)
            except ValueError:
                return

            if action == "BackToSelect":
                await self._mode_aware_wait(inter)
                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=OpenMessageOptionSelectView_components(inter, panel_id))
                else:
                    embed, components = OpenMessageOptionSelectView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketRoles_"):
            await self.handle_roles_config_actions(inter, custom_id)

        elif custom_id.startswith("TicketPref_"):
            # Always use full split to robustly support IDs like TicketPref_Transcripts_Toggle_{panel_id}
            parts = custom_id.split("_")
            if len(parts) < 3:
                return
            action = parts[1]
            panel_id = parts[-1]
            await self.handle_preferences_actions(inter, action, panel_id, custom_id)

        elif custom_id.startswith("TicketCreateOption_"):
            try:
                _, action, panel_id = custom_id.split("_", 2)
            except ValueError:
                return
            await self.handle_create_option_actions(inter, action, panel_id)

        elif custom_id.startswith("TicketOptions_"):
            try:
                _, action, panel_id = custom_id.split("_", 2)
            except ValueError:
                return
            await self.handle_options_actions(inter, action, panel_id)

        elif custom_id.startswith("TicketForm_"):
            try:
                parts = custom_id.split("_")
                action = parts[1]
                panel_id = parts[2]
                option_id = parts[3] if len(parts) > 3 else None
            except IndexError:
                return
            await self.handle_form_actions(inter, action, panel_id, option_id, custom_id)

    async def handle_create_option_actions(self, inter, action, panel_id):
        if action == "Add":
            await inter.response.send_modal(AddOptionModal(inter, panel_id))
        elif action == "Continue":
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(
                    components=ChannelSelectView_components(panel_id)
                )
            else:
                embed, components = ChannelSelectView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)

    async def handle_options_actions(self, inter, action, panel_id):
        if action == "Add":
            await inter.response.send_modal(AddOptionModal(inter, panel_id, from_edit=True))

    async def handle_form_actions(self, inter: disnake.Interaction, action: str, panel_id: str, option_id: str, custom_id: str):
        if action == "BackToSelect":
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=config_form_select_components(inter, panel_id))
            else:
                embed, view = config_form_select_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, view)
        
        elif action == "Add":
            await inter.response.send_modal(QuestionModal(inter, panel_id, option_id))

    async def handle_preferences_actions(self, inter, action, panel_id, custom_id):
        config = db.get_document("tickets_config") or {}
        if not config.get("panels", {}).get(panel_id):
            await self._mode_aware_wait(inter)
            return await message.error(inter, "Painel não encontrado.")
        
        preferences = config["panels"][panel_id].setdefault("preferences", {})

        if action == "Transcripts":
            sub_action = custom_id.split("_")[2]
            if sub_action == "Toggle":
                await self._mode_aware_wait(inter)
                
                config = db.get_document("tickets_config") or {} # Re-obter
                preferences = config["panels"][panel_id].setdefault("preferences", {})
                transcript_prefs = preferences.setdefault("transcripts", {})
                transcript_prefs["send_on_close"] = not transcript_prefs.get("send_on_close", False)
                db.save_document("tickets_config", config)

                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=TranscriptsView_components(inter, panel_id))
                else:
                    embed, components = TranscriptsView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)

        elif action == "CloseTickets":
            pass
        elif action == "Back":
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=PreferenciasView_components(inter, panel_id))
            else:
                embed, components = PreferenciasView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)

    async def handle_panel_edit_actions(self, inter, action, panel_id):
        config = db.get_document("tickets_config") or {}
        panels = config.get("panels", {})
        panel_data = panels.get(panel_id)
        if not panel_data: return await message.error(inter, "Painel não encontrado.")

        # Ações de modal são tratadas primeiro, pois têm seu próprio tipo de resposta.
        if action == "Hours":
            await inter.response.send_modal(OfficeHoursModal(panel_id))
            return

        # Para todas as outras ações, a resposta será uma edição da mensagem original.
        
        mode = db.get_document("custom_mode").get("mode")

        if action == "ConfigIA":
            await self._mode_aware_wait(inter)
            if mode == "components":
                await inter.edit_original_message(components=ConfigIAView_components(inter, panel_id))
            else:
                embed, components = ConfigIAView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "Preferences":
            await self._mode_aware_wait(inter)
            if mode == "components":
                await inter.edit_original_message(components=PreferenciasView_components(inter, panel_id))
            else:
                embed, components = PreferenciasView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "ConfigRoles":
            await self._mode_aware_wait(inter)
            options = panel_data.get("options", [])
            if len(options) > 1:
                # Mostra a seleção de opção se houver mais de uma
                if mode == "components":
                    await inter.edit_original_message(components=RolesOptionSelectView_components(inter, panel_id))
                else:
                    embed, components = RolesOptionSelectView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)
            elif len(options) == 1:
                # Vai direto para a config se houver apenas uma
                option_id = str(options[0].get("id"))
                if mode == "components":
                    await inter.edit_original_message(components=RolesConfigView_components(inter, panel_id, option_id))
                else:
                    embed, components = RolesConfigView_embed(inter, panel_id, option_id)
                    await self._handle_embed_edit(inter, embed, components)
            else:
                # Nenhuma opção configurada, talvez mostrar um erro
                 await message.error(inter, "Este painel não possui opções de ticket configuradas. Adicione opções antes de configurar os cargos.")

        elif action == "EditOptions":
            await self._mode_aware_wait(inter)
            if mode == "components":
                await inter.edit_original_message(components=config_options_components(inter, panel_id))
            else:
                embed, components = config_options_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "OpenMessageEditor":
            await self._mode_aware_wait(inter)
            if mode == "components":
                await inter.edit_original_message(components=MessageEditSelectionView_components(inter, panel_id))
            else:
                embed, components = MessageEditSelectionView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "ToggleEnable":
            await self._mode_aware_wait(inter)
            panels[panel_id]["enabled"] = not panel_data.get("enabled", False)
            db.save_document("tickets_config", config)
            if mode == "components":
                await inter.edit_original_message(components=SpecificPanelView_components(inter, panel_id))
            else:
                embed, components = SpecificPanelView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "ToggleAutoAssume":
            await self._mode_aware_wait(inter)
            panels[panel_id]["auto_assume_on_first_message"] = not panel_data.get("auto_assume_on_first_message", False)
            db.save_document("tickets_config", config)
            if mode == "components":
                await inter.edit_original_message(components=SpecificPanelView_components(inter, panel_id))
            else:
                embed, components = SpecificPanelView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "CycleMode":
            await self._mode_aware_wait(inter)
            current_mode = panel_data.get("mode") or "channel"  # Garantir padrão
            if current_mode not in modes:
                current_mode = "channel"  # Resetar para padrão se inválido
            next_index = (modes.index(current_mode) + 1) % len(modes)
            panels[panel_id]["mode"] = modes[next_index]
            db.save_document("tickets_config", config)
            if mode == "components":
                await inter.edit_original_message(components=SpecificPanelView_components(inter, panel_id))
            else:
                embed, components = SpecificPanelView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "SetChannel":
            await self._mode_aware_wait(inter)
            if mode == "components":
                await inter.edit_original_message(components=ChannelSelectView_components(panel_id))
            else:
                embed, components = ChannelSelectView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "SetCategory":
            await self._mode_aware_wait(inter)
            if mode == "components":
                await inter.edit_original_message(components=CategorySelectView_components(panel_id))
            else:
                embed, components = CategorySelectView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "BackToPanel":
            await self._mode_aware_wait(inter)
            if mode == "components":
                await inter.edit_original_message(components=SpecificPanelView_components(inter, panel_id))
            else:
                embed, components = SpecificPanelView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "Delete":
            await self._mode_aware_wait(inter)
            if panel_data.get("message_id") and panel_data.get("channel_id"):
                try:
                    channel = await self.bot.fetch_channel(panel_data["channel_id"])
                    msg = await channel.fetch_message(panel_data["message_id"])
                    await msg.delete()
                except (disnake.NotFound, disnake.Forbidden): pass
            del panels[panel_id]
            db.save_document("tickets_config", config)
            if mode == "components":
                await inter.edit_original_message(components=PainelTicket_components(inter))
            else:
                embed, components = PainelTicket_embed(inter)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "Sync":
             await self._mode_aware_wait(inter)
             await send_panel(inter, self.bot, panel_id)
             if mode == "components":
                await inter.edit_original_message(components=SpecificPanelView_components(inter, panel_id))
             else:
                embed, components = SpecificPanelView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)

    async def handle_open_message_edit_actions(self, inter, action, panel_id, option_id=None):
        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id)
        if not panel_data: return await message.error(inter, "Painel não encontrado.")

        option_data = {}
        if option_id:
            options = panel_data.get("options", [])
            option_data = next((opt for opt in options if str(opt.get("id")) == option_id), None)
            if not option_data:
                return await message.error(inter, "Opção não encontrada.")

        if action == "EditContent":
            open_message_data = option_data.get("open_message", {})
            style = open_message_data.get("style", "embed")

            if style == "embed":
                modal = EditOpenEmbedModal(panel_id, option_id, open_message_data.get("embed", {}))
            elif style == "content":
                modal = EditOpenContentModal(panel_id, option_id, open_message_data.get("content", {}))
            elif style == "container":
                modal = EditOpenContainerModal(panel_id, option_id, open_message_data.get("container", {}))
            else:
                return

            await inter.response.send_modal(modal)

        elif action == "CycleStyle":
            await self._mode_aware_wait(inter)
            
            options = config["panels"][panel_id].get("options", [])
            for i, opt in enumerate(options):
                if str(opt.get("id")) == option_id:
                    open_message_data = config["panels"][panel_id]["options"][i].setdefault("open_message", {})
                    styles = ["embed", "content", "container"]
                    current_style = open_message_data.get("style", "embed")
                    next_index = (styles.index(current_style) + 1) % len(styles)
                    open_message_data["style"] = styles[next_index]
                    db.save_document("tickets_config", config)
                    break
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=OpenMessageEditView_components(inter, panel_id, option_id))
            else:
                embed, components = OpenMessageEditView_embed(inter, panel_id, option_id)
                await self._handle_embed_edit(inter, embed, components)
        
        elif action == "Preview":
            await self.send_open_message_preview(inter, option_data)

    async def send_open_message_preview(self, inter: disnake.Interaction, option_data: dict):
        open_message_data = option_data.get("open_message", {})
        style = open_message_data.get("style", "embed")
        payload = {}

        if style == "embed":
            data = open_message_data.get("embed", {})
            color_str = data.get("color") or "#2F3136"
            try:
                color = disnake.Color(int(color_str.lstrip("#"), 16))
            except (ValueError, TypeError):
                color = disnake.Color.default()
            
            embed = disnake.Embed(
                title=data.get("title"),
                description=data.get("description"),
                color=color
            )
            if image_url := data.get("image_url"):
                embed.set_image(url=image_url)
            if thumbnail_url := data.get("thumbnail_url"):
                embed.set_thumbnail(url=thumbnail_url)
            
            payload["embed"] = embed

        elif style == "content":
            data = open_message_data.get("content", {})
            payload["content"] = data.get("content")
            if image_url := data.get("image_url"):
                if "http" in image_url:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as resp:
                                if resp.status == 200:
                                    image_bytes = await resp.read()
                                    payload["file"] = disnake.File(io.BytesIO(image_bytes), filename="image.png")
                    except Exception:
                        pass # Ignora erro no download para o preview

        elif style == "container":
            data = open_message_data.get("container", {})
            content = data.get("content")
            image_url = data.get("image_url")
            thumbnail_url = data.get("thumbnail_url")
            color_hex = data.get("color")

            if not content and not image_url and not thumbnail_url:
                return # Não há nada para mostrar

            container = ContainerUtils.montar_container(
                conteudo=content, 
                imagem_url=image_url, 
                cor_hex=color_hex,
                thumbnail_url=thumbnail_url
            )
            payload["components"] = [container]
            payload["flags"] = disnake.MessageFlags(is_components_v2=True)
        
        try:
            await inter.response.send_message(**payload, ephemeral=True)
        except Exception as e:
            # Usar followup se a resposta inicial falhar por algum motivo
            try:
                await inter.followup.send(f"Não foi possível gerar o preview: {e}", ephemeral=True)
            except Exception:
                pass # Evita travar se o followup também falhar

    async def send_panel_preview(self, inter: disnake.Interaction, panel_data: dict):
        style = panel_data.get("message_style", "embed")
        payload = {}

        if style == "embed":
            data = panel_data.get("embed", {})
            color_str = data.get("color") or "#2F3136"
            try:
                color = disnake.Color(int(color_str.lstrip("#"), 16))
            except (ValueError, TypeError):
                color = disnake.Color.default()
            
            embed = disnake.Embed(
                title=data.get("title"),
                description=data.get("description"),
                color=color
            )
            if image_url := data.get("image_url"):
                embed.set_image(url=image_url)
            if thumbnail_url := data.get("thumbnail_url"):
                embed.set_thumbnail(url=thumbnail_url)
            
            payload["embed"] = embed

        elif style == "content":
            data = panel_data.get("content", {})
            payload["content"] = data.get("content")
            if image_url := data.get("image_url"):
                if "http" in image_url:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as resp:
                                if resp.status == 200:
                                    image_bytes = await resp.read()
                                    payload["file"] = disnake.File(io.BytesIO(image_bytes), filename="image.png")
                    except Exception:
                        pass # Ignora erro no download para o preview

        elif style == "container":
            data = panel_data.get("container", {})
            content = data.get("content")
            image_url = data.get("image_url")
            thumbnail_url = data.get("thumbnail_url")
            color_hex = data.get("color")

            if not content and not image_url and not thumbnail_url:
                return # Não há nada para mostrar

            container = ContainerUtils.montar_container(
                conteudo=content, 
                imagem_url=image_url, 
                cor_hex=color_hex,
                thumbnail_url=thumbnail_url
            )
            payload["components"] = [container]
            payload["flags"] = disnake.MessageFlags(is_components_v2=True)
        
        try:
            await inter.response.send_message(**payload, ephemeral=True)
        except Exception as e:
            # Usar followup se a resposta inicial falhar por algum motivo
            try:
                await inter.followup.send(f"Não foi possível gerar o preview: {e}", ephemeral=True)
            except Exception:
                pass # Evita travar se o followup também falhar

    async def handle_roles_config_actions(self, inter: disnake.MessageInteraction, custom_id: str):
        await self._mode_aware_wait(inter)
        
        mode = db.get_document("custom_mode").get("mode")
        
        parts = custom_id.split("_")
        action = parts[1]

        # A estrutura do custom_id agora é mais complexa.
        # A melhor abordagem é extrair o painel_id com base na ação.
        if action == "BackToConfig":
            panel_id = parts[2]
            option_id = parts[3]
            if mode == "components":
                await inter.edit_original_message(components=RolesConfigView_components(inter, panel_id, option_id))
            else:
                embed, components = RolesConfigView_embed(inter, panel_id, option_id)
                await self._handle_embed_edit(inter, embed, components)
        elif action == "BackToSelect":
            panel_id = parts[2]
            if mode == "components":
                await inter.edit_original_message(components=RolesOptionSelectView_components(inter, panel_id))
            else:
                embed, components = RolesOptionSelectView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
        
        elif action == "ClearAll":
            panel_id = parts[2]
            option_id = parts[3]
            config = db.get_document("tickets_config") or {}
            if panel_id in config.get("panels", {}):
                options = config["panels"][panel_id].get("options", [])
                for i, opt in enumerate(options):
                    if str(opt.get("id")) == option_id:
                        if "roles" in config["panels"][panel_id]["options"][i]:
                            del config["panels"][panel_id]["options"][i]["roles"]
                            db.save_document("tickets_config", config)
                        break
            if mode == "components":
                await inter.edit_original_message(components=RolesConfigView_components(inter, panel_id, option_id))
            else:
                embed, components = RolesConfigView_embed(inter, panel_id, option_id)
                await self._handle_embed_edit(inter, embed, components)
        
        elif action == "ClearType":
            panel_id = parts[2]
            option_id = parts[3]
            role_type = parts[4]
            
            config = db.get_document("tickets_config") or {}
            if panel_id in config.get("panels", {}):
                options = config["panels"][panel_id].get("options", [])
                for i, opt in enumerate(options):
                    if str(opt.get("id")) == option_id:
                        if "roles" in opt and role_type in opt["roles"]:
                            config["panels"][panel_id]["options"][i]["roles"][role_type] = []
                            db.save_document("tickets_config", config)
                        break

            if mode == "components":
                await inter.edit_original_message(components=RoleSelectView_components(inter, panel_id, option_id, role_type))
            else:
                embed, components = RoleSelectView_embed(inter, panel_id, option_id, role_type)
                await self._handle_embed_edit(inter, embed, components)

    async def handle_ia_config_actions(self, inter, action, panel_id):
        config = db.get_document("tickets_config") or {}
        panels = config.get("panels", {})
        if panel_id not in panels: return

        if action == "Toggle":
            await self._mode_aware_wait(inter)
            panels[panel_id]["ai_enabled"] = not panels[panel_id].get("ai_enabled", False)
            db.save_document("tickets_config", config)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=ConfigIAView_components(inter, panel_id))
            else:
                embed, components = ConfigIAView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)

        elif action == "EditPrompt":
            await inter.response.send_modal(EditIAPromptModal(panel_id))

        elif action == "ToggleContext":
            await self._mode_aware_wait(inter)
            panels[panel_id]["ai_use_context"] = not panels[panel_id].get("ai_use_context", False)
            db.save_document("tickets_config", config)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=ConfigIAView_components(inter, panel_id))
            else:
                embed, components = ConfigIAView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)

    async def handle_message_edit_actions(self, inter, action, panel_id):
        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id)
        if not panel_data: return await message.error(inter, "Painel não encontrado.")

        mode = db.get_document("custom_mode").get("mode")

        if action == "PanelMessage":
            await self._mode_aware_wait(inter)
            if mode == "components":
                await inter.edit_original_message(components=MessageEditView_components(inter, panel_id))
            else:
                embed, components = MessageEditView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
            return
        elif action == "OpenMessage":
            await self._mode_aware_wait(inter)
            options = panel_data.get("options", [])
            if len(options) > 1:
                if mode == "components":
                    await inter.edit_original_message(components=OpenMessageOptionSelectView_components(inter, panel_id))
                else:
                    embed, components = OpenMessageOptionSelectView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)
            elif len(options) == 1:
                option_id = str(options[0].get("id"))
                if mode == "components":
                    await inter.edit_original_message(components=OpenMessageEditView_components(inter, panel_id, option_id))
                else:
                    embed, components = OpenMessageEditView_embed(inter, panel_id, option_id)
                    await self._handle_embed_edit(inter, embed, components)
            else:
                await message.error(inter, "Este painel não possui opções de ticket configuradas. Adicione opções antes de configurar as mensagens de abertura.")
            return

        if action in MODAL_CONFIGS:
            messages_data = panel_data.get("messages", {})
            modal_config = MODAL_CONFIGS[action]
            modal = EditTicketMessageModal(panel_id, modal_config, messages_data)
            await inter.response.send_modal(modal)
            return

        if action == "EditContent":
            style = panel_data.get("message_style", "embed")
            if style == "embed":
                await inter.response.send_modal(EditEmbedModal(panel_id, panel_data.get("embed", {})))
            elif style == "content":
                await inter.response.send_modal(EditContentModal(panel_id, panel_data.get("content", {})))
            elif style == "container":
                await inter.response.send_modal(EditContainerModal(panel_id, panel_data.get("container", {})))
        
        elif action == "EditButton":
            modal = EditButtonModal(panel_id, panel_data.get("button", {}))
            await inter.response.send_modal(modal)
        elif action == "CycleStyle":
            await self._mode_aware_wait(inter)
            styles = ["embed", "content", "container"]
            current_style = panel_data.get("message_style", "embed")
            next_index = (styles.index(current_style) + 1) % len(styles)
            config["panels"][panel_id]["message_style"] = styles[next_index]
            config["panels"][panel_id]["has_pending_changes"] = True
            db.save_document("tickets_config", config)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=MessageEditView_components(inter, panel_id))
            else:
                embed, components = MessageEditView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)

        elif action == "Preview":
            await self.send_panel_preview(inter, panel_data)
        
        elif action == "ShowPrefixes":
            await show_prefixes_panel(inter)

        elif action == "PreviewMessage":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.response.send_message(
                    components=MessagePreviewSelectionView_components(inter, panel_id),
                    ephemeral=True
                )
            else:
                embed, components = MessagePreviewSelectionView_embed(inter, panel_id)
                await inter.response.send_message(
                    embed=embed,
                    components=components,
                    ephemeral=True
                )

    async def send_message_preview(self, inter: disnake.MessageInteraction, panel_id: str, message_key: str):
        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id, {})
        messages = panel_data.get("messages", {})

        default_messages = {
            "close_message": "Seu ticket `{channel_name}` foi fechado por `{autor_mention}`.",
            "close_message_reason": "Seu ticket `{channel_name}` foi fechado por `{autor_mention}`.\n**Motivo:** {reason}",
            "notify_message_staff_to_user": "Olá {user_mention}, você está sendo notificado sobre o seu ticket `{channel_name}`. A equipe de suporte está aguardando sua resposta.",
            "notify_message_user_to_staff": "{user_mention} está solicitando sua atenção no ticket `{channel_name}`.",
            "add_user_message": "{alvo_mention} foi adicionado a este ticket por {autor_mention}.",
            "add_user_dm_message": "Olá {alvo_mention}, você foi adicionado ao ticket `{channel_name}` por {autor_mention}.",
            "remove_user_message": "{alvo_mention} foi removido deste ticket por {autor_mention}.",
            "remove_user_dm_message": "Olá {alvo_mention}, você foi removido do ticket `{channel_name}` por {autor_mention}.",
            "assume_message": "{autor_mention} assumiu o atendimento deste ticket.",
            "assume_dm_message": "Olá {user_mention}, o atendente {autor_mention} assumiu seu ticket `{channel_name}`.",
            "transfer_message": "O ticket foi transferido por {autor_mention}.",
            "create_call_message": "Uma call de voz foi iniciada para este ticket por {autor_mention}.",
            "create_call_dm_message": "Olá! Uma call de voz foi criada para o seu ticket `{channel_name}`.",
            "request_call_message": "O usuário {autor_mention} solicitou a criação de uma call."
        }
        
        message_template = messages.get(message_key, default_messages.get(message_key, "Mensagem não encontrada."))

        placeholders = {
            "channel_name": "nome-do-ticket",
            "autor_mention": inter.author.mention,
            "autor_name": inter.author.name,
            "user_mention": inter.author.mention,
            "user_name": inter.author.name,
            "alvo_mention": inter.author.mention,
            "alvo_name": inter.author.name,
            "reason": "Motivo de Exemplo",
            "guild_name": inter.guild.name,
            "atendente_mention": inter.author.mention,
            "atendente_name": inter.author.name,
            "old_owner_mention": inter.author.mention,
            "old_owner_name": inter.author.name,
            "new_owner_mention": inter.author.mention,
            "new_owner_name": inter.author.name
        }
        try:
            formatted_message = message_template.format_map(SafeFormatter(**placeholders))
        except KeyError as e:
            formatted_message = f"Erro ao formatar a mensagem (variável ausente: {e}):\n`{message_template}`"
            
        await inter.response.send_message(content=formatted_message, ephemeral=True)

    async def handle_message_preview_selection(self, inter: disnake.MessageInteraction, panel_id: str, category: str):
        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id, {})
        if not panel_data:
            return await inter.response.send_message("Painel não encontrado.", ephemeral=True)

        if category == "PanelMessage":
            payload = await self._build_panel_preview_payload(inter, panel_data)
            await inter.response.send_message(**payload, ephemeral=True)
        elif category == "OpenMessage":
            options = panel_data.get("options", [])
            if not options:
                await inter.response.send_message("Este painel não tem opções para visualizar a mensagem de abertura.", ephemeral=True)
                return
            
            if len(options) > 1:
                select_options = [
                    disnake.SelectOption(
                        label=opt.get("name", "Opção sem nome"),
                        value=str(opt.get("id")),
                        emoji=opt.get("emoji") or None,
                        description=opt.get("description")
                    ) for opt in options
                ]
                mode = db.get_document("custom_mode").get("mode")
                panel_name = panel_data.get('name', 'N/A')
                if mode == "components":
                    primary_color_hex = db.get_document("custom_colors").get("primary")
                    container_kwargs = {}
                    if primary_color_hex:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    container = disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Visualizar Mensagem > {panel_name} > **Selecionar Opção**"),
                            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                            disnake.ui.ActionRow(
                                disnake.ui.StringSelect(
                                    custom_id=f"TicketMsgPreview_Open_SelectOption_{panel_id}",
                                    placeholder="Selecione uma opção para visualizar a abertura",
                                    options=select_options,
                                )
                            ),
                        **container_kwargs,
                    )
                    await inter.response.send_message(
                        components=[container],
                        ephemeral=True,
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                else:
                    primary_color_hex = db.get_document("custom_colors").get("primary")
                    embed_kwargs = {}
                    if primary_color_hex:
                        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                    embed = disnake.Embed(
                        title=f"Visualizar Mensagem de Abertura: {panel_name}",
                        description="Selecione uma opção para visualizar a mensagem de abertura.",
                        **embed_kwargs
                    )
                    components = [
                        disnake.ui.ActionRow(
                            disnake.ui.StringSelect(
                                custom_id=f"TicketMsgPreview_Open_SelectOption_{panel_id}",
                                placeholder="Selecione uma opção para visualizar a abertura",
                                options=select_options,
                            )
                        )
                    ]
                    await inter.response.send_message(embed=embed, components=components, ephemeral=True)
            else:
                option_id = str(options[0].get("id"))
                payload = await self._build_open_message_preview_payload(inter, panel_data, option_id)
                await inter.response.send_message(**payload, ephemeral=True)
        elif category in MODAL_CONFIGS:
            modal_config_data = MODAL_CONFIGS[category]
            fields = modal_config_data["fields"]
            
            if len(fields) == 1:
                message_key = list(fields.keys())[0]
                await self.send_message_preview(inter, panel_id, message_key)
            else:
                mode = db.get_document("custom_mode").get("mode")
                
                if mode == "components":
                    config = db.get_document("tickets_config") or {}
                    panel_data = config.get("panels", {}).get(panel_id, {})
                    panel_name = panel_data.get('name', 'N/A')
                    primary_color_hex = db.get_document("custom_colors").get("primary")
                    
                    container_kwargs = {}
                    if primary_color_hex:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    
                    container = disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Gerenciar Tickets > Editar Painel > Visualizar Mensagem > **{panel_name}**"),
                            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                            disnake.ui.ActionRow(MessageSubtypePreviewSelect(panel_id, category, fields)),
                        **container_kwargs,
                    )
                    await inter.response.send_message(
                        components=[container],
                        ephemeral=True,
                        flags=disnake.MessageFlags(is_components_v2=True)
                    )
                else: # embed mode
                    config = db.get_document("tickets_config") or {}
                    panel_data = config.get("panels", {}).get(panel_id, {})
                    panel_name = panel_data.get('name', 'N/A')
                    primary_color_hex = db.get_document("custom_colors").get("primary")
                    embed_kwargs = {}
                    if primary_color_hex:
                        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                    
                    embed = disnake.Embed(
                        title=f"Visualizar Mensagem: {panel_name}",
                        description="Esta categoria tem múltiplas mensagens. Selecione qual visualizar:",
                        **embed_kwargs
                    )
                    await inter.response.send_message(
                        embed=embed,
                        components=[MessageSubtypePreviewView(panel_id, category, fields)],
                        ephemeral=True
                    )
        else:
            await inter.response.send_message("Categoria de mensagem inválida.", ephemeral=True)
            
    async def _build_panel_preview_payload(self, inter: disnake.Interaction, panel_data: dict) -> dict:
        style = panel_data.get("message_style", "embed")
        payload = {}
        
        options = panel_data.get("options", [])
        action_row = None

        if len(options) > 1:
            select_options = [
                disnake.SelectOption(
                    label=opt.get("name", "Opção sem nome"),
                    value=str(opt.get("id")),
                    emoji=opt.get("emoji") or None,
                    description=opt.get("description")
                ) for opt in options
            ]
            select = disnake.ui.StringSelect(
                custom_id=f"ticket_panel_option_select_{panel_data.get('id', 'preview')}",
                placeholder="Selecione uma opção para abrir o ticket...",
                options=select_options,
                disabled=True
            )
            action_row = disnake.ui.ActionRow(select)
        else:
            button_data = panel_data.get("button", {})
            button_style_map = {
                "green": disnake.ButtonStyle.success, "grey": disnake.ButtonStyle.secondary,
                "red": disnake.ButtonStyle.danger, "blue": disnake.ButtonStyle.primary
            }
            button_style = button_style_map.get(button_data.get("style", "green").lower(), disnake.ButtonStyle.secondary)
            button = disnake.ui.Button(
                label=button_data.get("label") or "Abrir Ticket",
                emoji=button_data.get("emoji") or None,
                style=button_style,
                disabled=True 
            )
            action_row = disnake.ui.ActionRow(button)

        if style == "embed":
            data = panel_data.get("embed", {})
            color_str = data.get("color") or "#2F3136"
            try:
                color = disnake.Color(int(color_str.lstrip("#"), 16))
            except (ValueError, TypeError):
                color = disnake.Color(int("2F3136", 16))

            embed = disnake.Embed(
                title=data.get("title"),
                description=data.get("description"),
                color=color
            )

            if image_url := data.get("image_url"):
                if "http" in image_url:
                    embed.set_image(url=image_url)
            
            if thumbnail_url := data.get("thumbnail_url"):
                if "http" in thumbnail_url:
                    embed.set_thumbnail(url=thumbnail_url)

            payload["embed"] = embed
            payload["components"] = [action_row]

        elif style == "content":
            data = panel_data.get("content", {})
            payload["content"] = data.get("content")
            payload["components"] = [action_row]
            if image_url := data.get("image_url"):
                if "http" in image_url:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as resp:
                                if resp.status == 200:
                                    image_bytes = await resp.read()
                                    payload["file"] = disnake.File(io.BytesIO(image_bytes), filename="image.png")
                    except Exception:
                        pass # Ignora erro no download para o preview

        elif style == "container":
            data = panel_data.get("container", {})
            content = data.get("content")
            image_url = data.get("image_url")
            thumbnail_url = data.get("thumbnail_url")
            color_hex = data.get("color")

            if not content and not image_url and not thumbnail_url:
                payload["content"] = "Não há nada para mostrar."
                return payload

            container = ContainerUtils.montar_container(
                conteudo=content, 
                imagem_url=image_url, 
                cor_hex=color_hex,
                thumbnail_url=thumbnail_url
            )
            payload["components"] = [container]
            payload["flags"] = disnake.MessageFlags(is_components_v2=True)
        
        return payload
    
    async def _build_open_message_preview_payload(self, inter: disnake.Interaction, panel_data: dict, option_id: str) -> dict:
        options = panel_data.get("options", [])
        option_data = next((opt for opt in options if str(opt.get("id")) == option_id), {})
        if not option_data:
            return {"content": "Erro: Opção não encontrada para o preview.", "ephemeral": True}

        open_message_data = option_data.get("open_message", {})
        style = open_message_data.get("style", "embed")
        payload = {}

        if style == "embed":
            data = open_message_data.get("embed", {})
            color_str = data.get("color") or "#2F3136"
            try:
                color = disnake.Color(int(color_str.lstrip("#"), 16))
            except (ValueError, TypeError):
                color = disnake.Color.default()
            
            embed = disnake.Embed(
                title=data.get("title"),
                description=data.get("description"),
                color=color
            )
            if image_url := data.get("image_url"):
                embed.set_image(url=image_url)
            if thumbnail_url := data.get("thumbnail_url"):
                embed.set_thumbnail(url=thumbnail_url)
            
            payload["embed"] = embed

        elif style == "content":
            data = open_message_data.get("content", {})
            payload["content"] = data.get("content")
            if image_url := data.get("image_url"):
                if "http" in image_url:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_url) as resp:
                                if resp.status == 200:
                                    image_bytes = await resp.read()
                                    payload["file"] = disnake.File(io.BytesIO(image_bytes), filename="image.png")
                    except Exception:
                        pass # Ignora erro no download para o preview

        elif style == "container":
            data = open_message_data.get("container", {})
            content = data.get("content")
            image_url = data.get("image_url")
            thumbnail_url = data.get("thumbnail_url")
            color_hex = data.get("color")

            if not content and not image_url and not thumbnail_url:
                payload["content"] = "Não há nada para mostrar."
                return payload

            container = ContainerUtils.montar_container(
                conteudo=content,
                imagem_url=image_url,
                cor_hex=color_hex,
                thumbnail_url=thumbnail_url
            )
            payload["components"] = [container]
            payload["flags"] = disnake.MessageFlags(is_components_v2=True)
            
        return payload

    # O listener de dropdown permanece o mesmo por enquanto
    @commands.Cog.listener("on_dropdown")
    async def ticket_dropdown_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id.startswith("select_panel_to_edit_"):
            await self._mode_aware_wait(inter)
            panel_id = inter.values[0]
            if panel_id != "disabled":
                
                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=SpecificPanelView_components(inter, panel_id))
                else:
                    embed, components = SpecificPanelView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketRoles_Select_"):
            try:
                _, _, panel_id, option_id = custom_id.split("_", 3)
            except ValueError:
                return
            role_type = inter.values[0]

            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")

            if mode == "components":
                await inter.edit_original_message(components=RoleSelectView_components(inter, panel_id, option_id, role_type))
            else:
                embed, components = RoleSelectView_embed(inter, panel_id, option_id, role_type)
                await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketRoles_SelectOption_"):
            try:
                _, _, panel_id = custom_id.split("_", 2)
            except ValueError:
                return
            option_id = inter.values[0]
            
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")

            if mode == "components":
                await inter.edit_original_message(components=RolesConfigView_components(inter, panel_id, option_id))
            else:
                embed, components = RolesConfigView_embed(inter, panel_id, option_id)
                await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketOpenMsg_SelectOption_"):
            try:
                _, _, panel_id = custom_id.split("_", 2)
            except ValueError:
                return
            option_id = inter.values[0]
            if option_id == "disabled": return

            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")

            if mode == "components":
                await inter.edit_original_message(components=OpenMessageEditView_components(inter, panel_id, option_id))
            else:
                embed, components = OpenMessageEditView_embed(inter, panel_id, option_id)
                await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketMsgEdit_SelectType_"):
            try:
                _, _, panel_id = custom_id.split("_", 2)
            except IndexError:
                return
            action = inter.values[0]
            await self.handle_message_edit_actions(inter, action, panel_id)

        elif custom_id.startswith("TicketOptions_SelectToEdit_"):
            try:
                parts = custom_id.split("_")
                panel_id = "_".join(parts[2:])
            except IndexError:
                return
            
            option_id = inter.values[0]
            await inter.response.send_modal(EditOptionModal(inter, panel_id, option_id))

        elif custom_id.startswith("TicketOptions_SelectToRemove_"):
            await self._mode_aware_wait(inter)
            try:
                parts = custom_id.split("_")
                panel_id = "_".join(parts[2:])
            except IndexError:
                return

            options_to_remove = inter.values
            config = db.get_document("tickets_config") or {}
            if panel_id in config.get("panels", {}):
                panel = config["panels"][panel_id]
                if "options" in panel:
                    # Make sure the IDs are strings for comparison, as inter.values are strings
                    panel["options"] = [opt for opt in panel.get("options", []) if str(opt.get("id")) not in options_to_remove]
                    db.save_document("tickets_config", config)
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=config_options_components(inter, panel_id))
            else:
                embed, components = config_options_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketForm_SelectOption_"):
            await self._mode_aware_wait(inter)
            try:
                panel_id = custom_id.split("_")[-1]
            except IndexError:
                return
            
            option_id = inter.values[0]
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=config_form_editor_components(inter, panel_id, option_id))
            else:
                embed, view = config_form_editor_embed(inter, panel_id, option_id)
                await self._handle_embed_edit(inter, embed, view)

        elif custom_id.startswith("TicketForm_SelectToEdit_"):
            try:
                parts = custom_id.split("_")
                option_id = parts[-1]
                panel_id = "_".join(parts[2:-1])
            except (ValueError, IndexError):
                return

            question_id = inter.values[0]
            await inter.response.send_modal(QuestionModal(inter, panel_id, option_id, question_id))

        elif custom_id.startswith("TicketForm_SelectToRemove_"):
            await self._mode_aware_wait(inter)
            try:
                parts = custom_id.split("_")
                option_id = parts[-1]
                panel_id = "_".join(parts[2:-1])
            except (ValueError, IndexError):
                return

            questions_to_remove = inter.values
            config = db.get_document("tickets_config") or {}
            if panel_id in config.get("panels", {}):
                forms = config["panels"][panel_id].setdefault("forms", {})
                if option_id in forms:
                    forms[option_id] = [q for q in forms[option_id] if str(q.get("id")) not in questions_to_remove]
                    db.save_document("tickets_config", config)
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=config_form_editor_components(inter, panel_id, option_id))
            else:
                embed, view = config_form_editor_embed(inter, panel_id, option_id)
                await self._handle_embed_edit(inter, embed, view)

        elif custom_id.startswith("TicketPreferences_Select_"):
            try:
                _, _, panel_id = custom_id.split("_", 2)
            except ValueError:
                return
            selection = inter.values[0]
            
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")

            if selection == "Forms":
                config = db.get_document("tickets_config") or {}
                panel_data = config.get("panels", {}).get(panel_id, {})
                options = panel_data.get("options", [])

                if len(options) == 1:
                    option_id = str(options[0].get("id"))
                    if mode == "components":
                        await inter.edit_original_message(components=config_form_editor_components(inter, panel_id, option_id))
                    else:
                        embed, view = config_form_editor_embed(inter, panel_id, option_id)
                        await self._handle_embed_edit(inter, embed, view)
                else:
                    if mode == "components":
                        await inter.edit_original_message(components=config_form_select_components(inter, panel_id))
                    else:
                        embed, view = config_form_select_embed(inter, panel_id)
                        await self._handle_embed_edit(inter, embed, view)
                return

            if selection == "ProductSupport":
                config = db.get_document("tickets_config") or {}
                preferences = config["panels"][panel_id].setdefault("preferences", {})
                product_support_prefs = preferences.setdefault("product_support", {})
                product_support_prefs["enabled"] = not product_support_prefs.get("enabled", False)
                db.save_document("tickets_config", config)

                if mode == "components":
                    await inter.edit_original_message(components=PreferenciasView_components(inter, panel_id))
                else:
                    embed, components = PreferenciasView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)
                return

            view_map = {
                "Transcripts": (TranscriptsView_components, TranscriptsView_embed),
                "MemberSetup": (MemberSetupView_components, MemberSetupView_embed),
                "AttendantSetup": (TeamSetupView_components, TeamSetupView_embed),
                "CloseTickets": (CloseTicketsView_components, CloseTicketsView_embed)
            }

            if selection in view_map:
                comp_view, embed_view = view_map[selection]
                if mode == "components":
                    await inter.edit_original_message(components=comp_view(inter, panel_id))
                else:
                    embed, components = embed_view(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)
            else:
                # Seleção desconhecida: edita de volta para a tela de preferências
                # para evitar que a interação fique carregando indefinidamente
                if mode == "components":
                    await inter.edit_original_message(components=PreferenciasView_components(inter, panel_id))
                else:
                    embed, components = PreferenciasView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketPref_CloseTickets_Select_"):
            try:
                _, _, _, panel_id = custom_id.split("_", 3)
            except ValueError:
                return
            selection = inter.values[0]

            config = db.get_document("tickets_config") or {}
            if not config.get("panels", {}).get(panel_id):
                return await message.error(inter, "Painel não encontrado.")
        
            preferences = config["panels"][panel_id].setdefault("preferences", {})
            auto_close_prefs = preferences.setdefault("auto_close", {})
            inactive = auto_close_prefs.setdefault("inactive", {})

            if selection == "UserLeft":
                await self._mode_aware_wait(inter)
                
                config = db.get_document("tickets_config") or {} # Re-obter
                preferences = config["panels"][panel_id].setdefault("preferences", {})
                auto_close_prefs = preferences.setdefault("auto_close", {})
                user_left_prefs = auto_close_prefs.setdefault("user_left", {})
                user_left_prefs["enabled"] = not user_left_prefs.get("enabled", False)
                db.save_document("tickets_config", config)
                
                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=CloseTicketsView_components(inter, panel_id))
                else:
                    embed, components = CloseTicketsView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)

            elif selection == "Inactive":
                inactive_prefs = auto_close_prefs.setdefault("inactive", {})
                modal = SetInactiveModal(panel_id, inactive_prefs)
                await inter.response.send_modal(modal)
                
            elif selection == "AtTime":
                at_time_prefs = auto_close_prefs.setdefault("at_time", {})
                modal = SetTimeCloseModal(panel_id, at_time_prefs)
                await inter.response.send_modal(modal)

            elif selection == "RequireReason":
                await self._mode_aware_wait(inter)
                
                config = db.get_document("tickets_config") or {} # Re-obter
                preferences = config["panels"][panel_id].setdefault("preferences", {})
                require_reason_prefs = preferences.setdefault("require_reason", {})
                require_reason_prefs["enabled"] = not require_reason_prefs.get("enabled", False)
                db.save_document("tickets_config", config)

                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=CloseTicketsView_components(inter, panel_id))
                else:
                    embed, components = CloseTicketsView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)
            
            elif selection == "SendCloseMessage":
                await self._mode_aware_wait(inter)
                
                config = db.get_document("tickets_config") or {} # Re-obter
                preferences = config["panels"][panel_id].setdefault("preferences", {})
                send_close_message_prefs = preferences.setdefault("send_close_message", {})
                send_close_message_prefs["enabled"] = not send_close_message_prefs.get("enabled", True)
                db.save_document("tickets_config", config)

                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=CloseTicketsView_components(inter, panel_id))
                else:
                    embed, components = CloseTicketsView_embed(inter, panel_id)
                    await self._handle_embed_edit(inter, embed, components)
        
        elif custom_id.startswith("TicketRoles_RoleSelect_"):
            await self._mode_aware_wait(inter)
            
            try:
                # Format: TicketRoles_RoleSelect_{panel_id}_{option_id}_{role_type}
                parts = custom_id.split("_")
                role_type = parts[-1]
                option_id = parts[-2]
                panel_id = "_".join(parts[2:-2])
            except (ValueError, IndexError):
                return

            config = db.get_document("tickets_config") or {}
            panels = config.get("panels", {})
            if panel_id not in panels: return
            
            options = panels[panel_id].get("options", [])
            option_found = False
            for i, opt in enumerate(options):
                if str(opt.get("id")) == option_id:
                    if "roles" not in panels[panel_id]["options"][i]:
                        panels[panel_id]["options"][i]["roles"] = {}
                    
                    selected_role_ids = [int(role_id) for role_id in inter.values]
                    panels[panel_id]["options"][i]["roles"][role_type] = selected_role_ids
                    option_found = True
                    break
            
            if not option_found:
                # Tratar caso a opção não seja encontrada, se necessário
                return

            db.save_document("tickets_config", config)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=RoleSelectView_components(inter, panel_id, option_id, role_type))
            else:
                embed, components = RoleSelectView_embed(inter, panel_id, option_id, role_type)
                await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketPref_MemberSetup_Select_"):
            await self._mode_aware_wait(inter)
            try:
                _, _, _, panel_id = custom_id.split("_", 3)
            except ValueError:
                return
            config = db.get_document("tickets_config") or {}
            preferences = config["panels"][panel_id].setdefault("preferences", {})
            member_setup = preferences.setdefault("member_setup", {})
            member_setup["disabled_buttons"] = inter.values
            db.save_document("tickets_config", config)
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=MemberSetupView_components(inter, panel_id))
            else:
                embed, components = MemberSetupView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
            
        elif custom_id.startswith("TicketPref_TeamSetup_Select_"):
            await self._mode_aware_wait(inter)
            try:
                _, _, _, panel_id = custom_id.split("_", 3)
            except ValueError:
                return
            config = db.get_document("tickets_config") or {}
            preferences = config["panels"][panel_id].setdefault("preferences", {})
            team_setup = preferences.setdefault("team_setup", {})
            team_setup["disabled_buttons"] = inter.values
            db.save_document("tickets_config", config)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=TeamSetupView_components(inter, panel_id))
            else:
                embed, components = TeamSetupView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketEdit_SelectChannel_"):
            try:
                _, _, panel_id = custom_id.split("_", 2)
            except ValueError:
                return
            new_channel_id = int(inter.values[0])
            
            config = db.get_document("tickets_config") or {}
            if panel_id in config.get("panels", {}):
                panel_data = config["panels"][panel_id]
                old_channel_id = panel_data.get("channel_id")
                old_message_id = panel_data.get("message_id")

                # Se havia uma mensagem publicada em um canal diferente, apaga a antiga
                if old_channel_id and old_message_id and old_channel_id != new_channel_id:
                    try:
                        channel = await self.bot.fetch_channel(old_channel_id)
                        msg = await channel.fetch_message(old_message_id)
                        await msg.delete()
                    except (disnake.NotFound, disnake.Forbidden):
                        pass  # Ignora se não encontrar ou não tiver permissão

                # Atualiza para o novo canal e reseta o ID da mensagem para forçar um novo envio
                config["panels"][panel_id]["channel_id"] = new_channel_id
                config["panels"][panel_id]["message_id"] = None
                
                # Esta não é mais considerada uma "alteração pendente" para publicação
                db.save_document("tickets_config", config)
            
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=SpecificPanelView_components(inter, panel_id))
            else:
                embed, components = SpecificPanelView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)

        elif custom_id.startswith("TicketEdit_SelectCategory_"):
            try:
                _, _, panel_id = custom_id.split("_", 2)
            except ValueError:
                return
            category_id = int(inter.values[0])
            
            config = db.get_document("tickets_config") or {}
            if panel_id in config.get("panels", {}):
                config["panels"][panel_id]["category_id"] = category_id
                db.save_document("tickets_config", config)
            
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=SpecificPanelView_components(inter, panel_id))
            else:
                embed, components = SpecificPanelView_embed(inter, panel_id)
                await self._handle_embed_edit(inter, embed, components)
    
    @commands.Cog.listener("on_modal_submit")
    async def ticket_modal_listener(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id
        
        if custom_id == "create_ticket_modal":
            # Isso é tratado no próprio modal, mas podemos adicionar lógica aqui se necessário
            pass
        
        elif custom_id.startswith("SetInactiveModal_"):
            try:
                _, panel_id = custom_id.split("_", 1)
            except ValueError:
                return

            config = db.get_document("tickets_config") or {}
            if panel_id in config.get("panels", {}):
                preferences = config["panels"][panel_id].setdefault("preferences", {})
                auto_close = preferences.setdefault("auto_close", {})
                inactive = auto_close.setdefault("inactive", {})
                
                minutes_str = inter.text_values["minutes"].strip()
                warn_message = inter.text_values["warn_message"].strip()
                close_message = inter.text_values["close_message"].strip()
                
                minutes = int(minutes_str) if minutes_str.isdigit() else 0
                
                # Desativa se qualquer campo obrigatório estiver vazio
                if not minutes_str or not warn_message or not close_message or minutes == 0:
                    inactive["enabled"] = False
                else:
                    inactive["enabled"] = True
                
                inactive["minutes"] = minutes
                inactive["warn_message"] = warn_message
                inactive["close_message"] = close_message
                
                db.save_document("tickets_config", config)

                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.response.edit_message(components=CloseTicketsView_components(inter, panel_id))
                else:
                    embed, components = CloseTicketsView_embed(inter, panel_id)
                    await inter.response.edit_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("SetTimeCloseModal_"):
            try:
                _, panel_id = custom_id.split("_", 1)
            except ValueError:
                return

            config = db.get_document("tickets_config") or {}
            if panel_id in config.get("panels", {}):
                preferences = config["panels"][panel_id].setdefault("preferences", {})
                auto_close = preferences.setdefault("auto_close", {})
                at_time = auto_close.setdefault("at_time", {})
                
                time_str = inter.text_values["time"].strip()
                close_message = inter.text_values["close_message"].strip()
                
                # Desativa se qualquer campo obrigatório estiver vazio ou formato inválido
                if not time_str or not close_message:
                    at_time["enabled"] = False
                elif len(time_str) == 5 and time_str[2] == ":" and time_str.replace(":", "").isdigit():
                    at_time["time"] = time_str
                    at_time["enabled"] = True
                else:
                    at_time["enabled"] = False

                at_time.pop("warn_message", None)
                at_time["close_message"] = close_message
                
                db.save_document("tickets_config", config)

                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.response.edit_message(components=CloseTicketsView_components(inter, panel_id))
                else:
                    embed, components = CloseTicketsView_embed(inter, panel_id)
                    await inter.response.edit_message(content=None, embed=embed, components=components)
        
        elif custom_id.startswith("question_modal_"):
            try:
                _, _, panel_id, option_id, question_id = custom_id.split("_", 4)
            except ValueError:
                return

            config = db.get_document("tickets_config") or {}
            panel = config.get("panels", {}).get(panel_id, {})
            forms = panel.setdefault("forms", {})
            questions = forms.setdefault(option_id, [])

            label = inter.text_values["question_label"]
            placeholder = inter.text_values["question_placeholder"]
            style = inter.text_values["question_style"].lower()
            required = inter.text_values["question_required"].lower()

            if style not in ["short", "paragraph"]:
                style = "short"
            
            if question_id: # Editing
                question = next((q for q in questions if str(q.get("id")) == question_id), None)
                if question:
                    question["label"] = label
                    question["placeholder"] = placeholder
                    question["style"] = style
                    question["required"] = required == "sim"
            else: # Adding
                import random, string
                new_id = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                questions.append({
                    "id": new_id,
                    "label": label,
                    "placeholder": placeholder,
                    "style": style,
                    "required": required == "sim"
                })

            db.save_document("tickets_config", config)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.response.edit_message(components=config_form_editor_components(inter, panel_id, option_id))
            else:
                embed, components = config_form_editor_embed(inter, panel_id, option_id)
                await inter.response.edit_message(embed=embed, components=components)

        elif custom_id.startswith("TicketMsgPreview_SelectCat_"):
            try:
                _, _, panel_id = custom_id.split("_", 2)
            except ValueError:
                return
            
            category = inter.values[0]
            await self.handle_message_preview_selection(inter, panel_id, category)

        elif custom_id.startswith("TicketMsgPreview_SelectSub_"):
            try:
                parts = custom_id.split("_")
                panel_id = parts[2]
                category = parts[3]
            except (ValueError, IndexError):
                return
            
            message_key = inter.values[0]
            await self.send_message_preview(inter, panel_id, message_key)

        elif custom_id.startswith("TicketMsgPreview_Open_SelectOption_"):
            try:
                _, _, _, panel_id = custom_id.split("_", 3)
            except ValueError:
                return
            
            option_id = inter.values[0]
            config = db.get_document("tickets_config") or {}
            panel_data = config.get("panels", {}).get(panel_id, {})
            if not panel_data:
                return await inter.response.send_message("Painel não encontrado.", ephemeral=True)
            
            payload = await self._build_open_message_preview_payload(inter, panel_data, option_id)
            await inter.response.send_message(**payload, ephemeral=True)

        elif custom_id.startswith("EditOptionModal_"):
            try:
                _, panel_id, option_id = custom_id.split("_", 2)
            except ValueError:
                return
            
            config = db.get_document("tickets_config") or {}
            if panel_id in config.get("panels", {}):
                panel = config["panels"][panel_id]
                if "options" in panel:
                    for opt in panel["options"]:
                        if str(opt.get("id")) == option_id:
                            opt["name"] = inter.text_values.get("option_name")
                            opt["description"] = inter.text_values.get("option_description")
                            opt["emoji"] = inter.text_values.get("option_emoji")
                            break
                    db.save_document("tickets_config", config)
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.response.edit_message(components=config_options_components(inter, panel_id))
            else:
                embed, components = config_options_embed(inter, panel_id)
                await inter.response.edit_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("AddOptionModal_"):
            try:
                # Format: AddOptionModal_{panel_id}_{from_edit}
                _, panel_id, from_edit_str = custom_id.split("_", 2)
            except ValueError:
                return

            from_edit = from_edit_str == "True"
            config = db.get_document("tickets_config") or {}
            
            if panel_id in config.get("panels", {}):
                panel = config["panels"][panel_id]
                if "options" not in panel:
                    panel["options"] = []
                
                new_option_id = 1
                if panel.get("options"):
                    new_option_id = max(opt.get("id", 0) for opt in panel["options"]) + 1
                
                label = inter.text_values.get("option_name")
                description = inter.text_values.get("option_description")
                emoji_str = inter.text_values.get("option_emoji")

                if not (label and description and emoji_str):
                    # Handle error: missing values
                    return 

                new_option = {
                    "id": new_option_id,
                    "name": label,
                    "description": description,
                    "emoji": emoji_str
                }
                panel["options"].append(new_option)
                db.save_document("tickets_config", config)
            
            mode = db.get_document("custom_mode").get("mode")
            if from_edit:
                if mode == "components":
                    await inter.response.edit_message(components=config_options_components(inter, panel_id))
                else:
                    embed, components = config_options_embed(inter, panel_id)
                    await inter.response.edit_message(content=None, embed=embed, components=components)
            else:
                if mode == "components":
                    components = create_options_components(panel_id, panel.get("name", ""), panel.get("options", []))
                    await inter.response.edit_message(components=components)
                else:
                    embed, components = create_options_embed(panel_id, panel.get("name", ""), panel.get("options", []))
                    await inter.response.edit_message(embed=embed, components=components)

def setup(bot: commands.Bot):
    bot.add_cog(TicketConfigCog(bot))