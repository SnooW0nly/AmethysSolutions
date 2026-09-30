import disnake
from disnake.ext import commands
import io

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message
from .config_giveaways import (
    CreateGiveawayModal,
    EditGiveawayView_components,
    EditGiveawayView_embed,
    SpecificGiveawayView_components,
    SpecificGiveawayView_embed,
    SelectModeView_components,
    SelectModeView_embed,
    LogChannelSelectView_components,
    LogChannelSelectView_embed
)
from .config_preferences import PreferencesView_components, PreferencesView_embed
from .preferences.award import PrizeView_components, PrizeView_embed, PrizeContentModal
from .preferences.winner import (
    WinnerView_components, WinnerView_embed
)
from .preferences.requirements import (
    RequirementsView_components, RequirementsView_embed, REQUIREMENTS_CONFIG, RequirementModal,
    check_giveaway_requirements
)
from .preferences.monitor import MonitorView_components, MonitorView_embed
from .preferences.rifa import (
    RifaView_components, RifaView_embed, RifaConfigModal, process_rifa_ticket_purchase
)
from .preferences.roles import (
    RolesView_components, RolesView_embed,
    ForbiddenRolesView_components, ForbiddenRolesView_embed,
    BonusRolesView_components, BonusRolesView_embed,
    SelectBonusRoleView_components, SelectBonusRoleView_embed,
    BonusEntriesModal,
    RemoveBonusRoleView_components, RemoveBonusRoleView_embed,
    AllowedRolesView_components, AllowedRolesView_embed
)
from .config_tasks import (
    ManageTasksView_components, ManageTasksView_embed, TaskEditorView_components, TaskEditorView_embed,
    SelectTaskView_components, SelectTaskView_embed, CreateTaskModal,
    RepostConfirmationView_components, RepostConfirmationView_embed
)
from .tasks_config.config_channel import ChannelSelectView_components, ChannelSelectView_embed
from .tasks_config.config_mode import ModeSelectView_components, ModeSelectView_embed, KeywordModal
from .tasks_config.participantes import (
    ParticipantsConfigView_components, ParticipantsConfigView_embed,
    LimitsModal
)
from .tasks_config.duration import DurationModal
from . import config_message
from functions.utils import utils
from .container_utils import ContainerUtils
from tasks.giveaways.logger_giveaways import log_giveaway_event
from tasks.giveaways.roll_giveaways import process_giveaway_roll

class Giveaways(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def GiveawaysComponents(self, inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        giveaways = db.obter("database/giveaways/giveaways_data.json") or {}
        num_giveaways = len(giveaways)

        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > **Sorteios**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"{emoji.giveaway} **Sorteios Criados:** `{num_giveaways}`"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Criar Sorteio", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Giveaways_CriarSorteio"),
                    disnake.ui.Button(label="Editar Sorteio", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Giveaways_VerSorteios", disabled=not giveaways),
                    disnake.ui.Button(label="Estatísticas", style=disnake.ButtonStyle.grey, emoji=emoji.chart, custom_id="Giveaways_Stats", disabled=True),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PainelInicial"),
            )
        ]

    def GiveawaysEmbed(self, inter: disnake.MessageInteraction):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        giveaways = db.obter("database/giveaways/giveaways_data.json") or {}
        num_giveaways = len(giveaways)

        embed = disnake.Embed(
            title=f"Sorteios",
            description=f"{emoji.giveaway} **Sorteios Criados:** `{num_giveaways}`",
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Criar Sorteio", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="Giveaways_CriarSorteio"),
                disnake.ui.Button(label="Editar Sorteio", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="Giveaways_VerSorteios", disabled=not giveaways),
                disnake.ui.Button(label="Estatísticas", style=disnake.ButtonStyle.grey, emoji=emoji.chart, custom_id="Giveaways_Stats", disabled=True),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PainelInicial"),
            )
        ]
        return embed, components

    async def display_giveaways_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        await self._mode_aware_wait(inter)

        if mode == "embed":
            embed, components = self.GiveawaysEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(
                components=self.GiveawaysComponents(inter),
            )

    async def _mode_aware_wait(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        try:
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
        except disnake.errors.NotFound:
            # Interaction expired or unknown; ignore to avoid crashing listeners
            return
        except disnake.errors.HTTPException as e:
            # 10062 Unknown interaction
            if getattr(e, "code", None) == 10062:
                return
            raise

    @commands.Cog.listener("on_button_click")
    async def giveaways_button_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id == "Giveaways_CriarSorteio":
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=SelectModeView_components())
            else:
                embed, components = SelectModeView_embed()
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayCreate_SetMode_"):
            mode = custom_id.split("_")[2]
            await inter.response.send_modal(CreateGiveawayModal(inter, mode))

        elif custom_id == "Giveaways_VerSorteios":
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=EditGiveawayView_components())
            else:
                embed, components = EditGiveawayView_embed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id == "Giveaways_Painel":
            await self.display_giveaways_panel(inter)

        elif custom_id.startswith("GiveawayEdit_"):
            try:
                _, action, giveaway_id = custom_id.split("_", 2)
            except ValueError:
                return

            await self.handle_giveaway_edit_actions(inter, action, giveaway_id)

        elif custom_id.startswith("GiveawayTask_"):
            await self.handle_giveaway_task_actions(inter, custom_id)

        elif custom_id.startswith("GiveawayMsgEdit_"):
            await self.handle_giveaway_message_edit_actions(inter, custom_id)

        elif custom_id.startswith("GiveawayParticipants_"):
            await self.handle_giveaway_participants_actions(inter, custom_id)

        elif custom_id.startswith("GiveawayRoles_"):
            await self.handle_giveaway_roles_actions(inter, custom_id)

        elif custom_id.startswith("Giveaway_Participate_"):
            await self.handle_giveaway_participation(inter, custom_id)

        elif custom_id.startswith("Giveaway_Info_") or custom_id.startswith("Giveaway_GenerateList_"):
            try:
                await inter.response.defer(ephemeral=True)
            except Exception:
                try:
                    await inter.followup.send("A interação expirou. Tente clicar novamente.", ephemeral=True)
                except Exception:
                    pass
                return
            parts = custom_id.split('_', 3)
            if len(parts) < 4:
                await inter.followup.send("Interação inválida ou botão desatualizado. Atualize o painel do sorteio!", ephemeral=True)
                return
            _, _, giveaway_id, task_id = parts
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id)
            task = next((t for t in giveaway.get("tasks", []) if t.get("id") == task_id), None)
            if not giveaway or not task:
                await inter.followup.send("Sorteio ou tarefa não encontrados.", ephemeral=True)
                return
            if custom_id.startswith("Giveaway_Info_"):
                await self.show_giveaway_info(inter, giveaway, task, giveaway_id, task_id)
            else:
                await self.generate_participant_list(inter, giveaway, task, giveaway_id, task_id)

        elif custom_id.startswith("GiveawayRifa_"):
            await self.handle_giveaway_rifa_actions(inter, custom_id)

        elif custom_id.startswith("Giveaway_BuyTicket_"):
            try:
                _, _, giveaway_id, task_id = custom_id.split("_", 3)
            except ValueError:
                return
            await process_rifa_ticket_purchase(inter, giveaway_id, task_id, self.bot)

        elif custom_id.startswith("GiveawayPref_"):
            try:
                parts = custom_id.split("_")
                action = parts[1]
                giveaway_id = parts[2]
            except IndexError:
                return

            await self.handle_giveaway_preferences_actions(inter, custom_id, action, giveaway_id)

        elif custom_id.startswith("GiveawayPrize_"):
            await self.handle_giveaway_prize_actions(inter, custom_id)

    @commands.Cog.listener("on_dropdown")
    async def giveaways_dropdown_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id.startswith("select_giveaway_to_edit_"):
            await self._mode_aware_wait(inter)
            giveaway_id = inter.values[0]
            if giveaway_id != "disabled":
                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=SpecificGiveawayView_components(inter, giveaway_id))
                else:
                    embed, components = SpecificGiveawayView_embed(inter, giveaway_id)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
        
        elif custom_id.startswith("GiveawayTask_SelectToManage_"):
            await self._mode_aware_wait(inter)
            giveaway_id = custom_id.split("_")[-1]
            task_id = inter.values[0]
            if task_id == "disabled":
                return
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=TaskEditorView_components(inter, giveaway_id, task_id))
            else:
                embed, components = TaskEditorView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayWinner_SelectUser_"):
            giveaway_id = custom_id.split("_")[-1]
            selected_users = [int(u) for u in inter.values]
            
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            giveaway["winner_users"] = selected_users
            db.salvar("database/giveaways/giveaways_data.json", config)

            await log_giveaway_event(
                bot=self.bot, giveaway_id=giveaway_id, title="Sorteios - Ganhadores Alterados",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                    f"{emoji.member} **Usuários Ganhadores Definidos:** `{len(selected_users)}`",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )
            
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=WinnerView_components(inter, giveaway_id))
            else:
                embed, components = WinnerView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayWinner_SelectRole_"):
            giveaway_id = custom_id.split("_")[-1]
            selected_roles = [int(r) for r in inter.values]
            
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            giveaway["winner_roles"] = selected_roles
            db.salvar("database/giveaways/giveaways_data.json", config)

            await log_giveaway_event(
                bot=self.bot, giveaway_id=giveaway_id, title="Sorteios - Ganhadores Alterados",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                    f"{emoji.role} **Cargos Ganhadores Definidos:** `{len(selected_roles)}` cargo(s) definido(s)",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )

            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=WinnerView_components(inter, giveaway_id))
            else:
                embed, components = WinnerView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayPrize_SelectType_"):
            giveaway_id = custom_id.split("_")[-1]
            prize_type = inter.values[0]

            if prize_type == "product":
                await inter.response.send_message(f"{emoji.wrong} A premiação por produto da loja ainda não está disponível.", ephemeral=True)
                return
            
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            if "prize" not in giveaway: giveaway["prize"] = {}
            giveaway["prize"]["type"] = prize_type
            db.salvar("database/giveaways/giveaways_data.json", config)

            type_names = {"none": "Nada será entregue", "content": "Conteúdo na DM"}
            await log_giveaway_event(
                bot=self.bot, giveaway_id=giveaway_id, title="Sorteios - Premiação Alterada",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                    f"{emoji.edit} **Tipo de Prêmio:** `{type_names.get(prize_type, 'N/A')}`",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )
            
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=PrizeView_components(inter, giveaway_id))
            else:
                embed, components = PrizeView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayPref_"):
            giveaway_id = custom_id.split("_")[-1]
            selection = inter.values[0]

            if selection == "change_mode":
                config = db.obter("database/giveaways/giveaways_data.json")
                if giveaway_id in config:
                    current_mode = config[giveaway_id].get("mode", "real")
                    new_mode = "falso" if current_mode == "real" else "real"
                    config[giveaway_id]["mode"] = new_mode
                    db.salvar("database/giveaways/giveaways_data.json", config)
                    await log_giveaway_event(
                        bot=self.bot,
                        giveaway_id=giveaway_id,
                        title="Sorteios - Modo Alterado",
                        lines=[
                            f"{emoji.giveaway} **Sorteio:** {config[giveaway_id].get('name')}",
                            f"{emoji.edit} **Novo Modo:** `{new_mode.capitalize()}`",
                            f"{emoji.member} **Executor:** {inter.author.mention}"
                        ]
                    )

                await self._mode_aware_wait(inter)
                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=PreferencesView_components(inter, giveaway_id))
                else:
                    embed, components = PreferencesView_embed(inter, giveaway_id)
                    await inter.edit_original_message(content=None, embed=embed, components=components)

            elif selection == "config_monitor":
                config = db.obter("database/giveaways/giveaways_data.json")
                if giveaway_id in config:
                    current_status = config[giveaway_id].get("monitor_enabled", False)
                    new_status = not current_status
                    config[giveaway_id]["monitor_enabled"] = new_status
                    db.salvar("database/giveaways/giveaways_data.json", config)
                    await log_giveaway_event(
                        bot=self.bot,
                        giveaway_id=giveaway_id,
                        title="Sorteios - Monitor Alterado",
                        lines=[
                            f"{emoji.giveaway} **Sorteio:** {config[giveaway_id].get('name')}",
                            f"{emoji.edit} **Status do Monitor:** `{'Ativado' if new_status else 'Desativado'}`",
                            f"{emoji.member} **Executor:** {inter.author.mention}"
                        ]
                    )

                await self._mode_aware_wait(inter)
                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=PreferencesView_components(inter, giveaway_id))
                else:
                    embed, components = PreferencesView_embed(inter, giveaway_id)
                    await inter.edit_original_message(content=None, embed=embed, components=components)

            view_map = {
                "set_prize": (PrizeView_components, PrizeView_embed),
                "set_winner": (WinnerView_components, WinnerView_embed),
                "set_roles": (RolesView_components, RolesView_embed),
                "set_requirements": (RequirementsView_components, RequirementsView_embed),
            }

            if selection in view_map:
                await self._mode_aware_wait(inter)
                mode = db.get_document("custom_mode").get("mode")
                comp_view, embed_view = view_map[selection]
                if mode == "components":
                    await inter.edit_original_message(components=comp_view(inter, giveaway_id))
                else:
                    embed, components = embed_view(inter, giveaway_id)
                    await inter.edit_original_message(content=None, embed=embed, components=components)


        elif custom_id.startswith("GiveawayReq_Select_"):
            giveaway_id = custom_id.split("_")[-1]
            selection = inter.values[0]

            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            giveaway_name = giveaway.get("name", "N/A")

            is_modal_req = REQUIREMENTS_CONFIG.get(selection, {}).get("modal", False)

            if not is_modal_req:
                # Requisito simples (só clicar para ativar/desativar)
                await self._mode_aware_wait(inter)
                requirements = giveaway.setdefault("requirements", {})
                req_data = requirements.setdefault(selection, {})
                new_status = not req_data.get("enabled", False)
                req_data["enabled"] = new_status
                db.salvar("database/giveaways/giveaways_data.json", config)

                await log_giveaway_event(
                    bot=self.bot,
                    giveaway_id=giveaway_id,
                    title="Sorteios - Requisito Alterado",
                    lines=[
                        f"{emoji.giveaway} **Sorteio:** {giveaway_name}",
                        f"{emoji.settings} **Requisito:** {REQUIREMENTS_CONFIG[selection]['label']}",
                        f"{emoji.edit} **Ação:** {'Ativado' if new_status else 'Desativado'}",
                        f"{emoji.member} **Executor:** {inter.author.mention}"
                    ]
                )

                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=RequirementsView_components(inter, giveaway_id))
                else:
                    embed, components = RequirementsView_embed(inter, giveaway_id)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                # Requisito com modal (configurar texto/valor)
                # O send_modal não pode ter wait antes
                await inter.response.send_modal(RequirementModal(inter, giveaway_id, selection))

        elif custom_id.startswith("GiveawayReq_SetValue_"):
            await inter.response.defer(ephemeral=True)
            parts = custom_id.split("_")
            giveaway_id = parts[2]
            req_key = parts[3]

            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            requirements = giveaway.setdefault("requirements", {})
            req_data = requirements.setdefault(req_key, {})

            if req_key == "specific_voice_channel":
                req_data["value"] = int(inter.values[0]) if inter.values else None
            elif req_key == "invited_by":
                req_data["value"] = [int(v) for v in inter.values]

            req_data["enabled"] = bool(req_data.get("value"))
            db.salvar("database/giveaways/giveaways_data.json", config)

            await inter.followup.send("Requisito atualizado com sucesso!", ephemeral=True)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=RequirementsView_components(inter, giveaway_id))
            else:
                embed, components = RequirementsView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayReq_BackToPanel_"):
            await self._mode_aware_wait(inter)
            giveaway_id = custom_id.split("_")[-1]
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=RequirementsView_components(inter, giveaway_id))
            else:
                embed, components = RequirementsView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)


        elif custom_id.startswith("GiveawayRoles_SelectForbidden_"):
            await inter.response.defer(ephemeral=True)
            parts = custom_id.split("_")
            giveaway_id = parts[2]
            selected_roles = [int(r) for r in (inter.values or [])]

            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            giveaway_name = giveaway.get("name", "N/A")

            giveaway["forbidden_roles"] = selected_roles
            config[giveaway_id] = giveaway
            db.salvar("database/giveaways/giveaways_data.json", config)
            
            await log_giveaway_event(
                bot=self.bot,
                giveaway_id=giveaway_id,
                title="Sorteios - Cargos Alterados",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway_name}",
                    f"{emoji.wrong} **Cargos Proibidos:** `{len(selected_roles)}` cargo(s) definido(s)",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )

            await inter.followup.send(f"{emoji.correct} Lista de cargos proibidos atualizada!", ephemeral=True)

            mode = db.get_document("custom_mode").get("mode")
            giveaway_name = giveaway.get("name", "N/A")
            if mode == "components":
                await inter.edit_original_message(components=ForbiddenRolesView_components(inter, giveaway_id, giveaway_name))
            else:
                embed, components = ForbiddenRolesView_embed(inter, giveaway_id, giveaway_name)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayRoles_SelectAllowed_"):
            await inter.response.defer(ephemeral=True)
            parts = custom_id.split("_")
            giveaway_id = parts[2]
            selected_roles = [int(r) for r in (inter.values or [])]

            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            giveaway_name = giveaway.get("name", "N/A")

            giveaway["allowed_roles"] = selected_roles
            config[giveaway_id] = giveaway
            db.salvar("database/giveaways/giveaways_data.json", config)

            await log_giveaway_event(
                bot=self.bot,
                giveaway_id=giveaway_id,
                title="Sorteios - Cargos Alterados",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway_name}",
                    f"{emoji.double_check} **Cargos Permitidos:** `{len(selected_roles)}` cargo(s) definido(s)",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )

            await inter.followup.send(f"{emoji.correct} Lista de cargos permitidos atualizada!", ephemeral=True)

            mode = db.get_document("custom_mode").get("mode")
            giveaway_name = giveaway.get("name", "N/A")
            if mode == "components":
                await inter.edit_original_message(components=AllowedRolesView_components(inter, giveaway_id, giveaway_name))
            else:
                embed, components = AllowedRolesView_embed(inter, giveaway_id, giveaway_name)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayRoles_SelectBonusRole_"):
            parts = custom_id.split("_")
            giveaway_id = parts[2]
            role_id = inter.values[0]

            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})

            current_entries = str(giveaway.get("bonus_roles", {}).get(role_id, "1"))

            await inter.response.send_modal(BonusEntriesModal(inter, giveaway_id, role_id, current_entries))

        elif custom_id.startswith("GiveawayRoles_SelectRemoveBonusRole_"):
            parts = custom_id.split("_")
            giveaway_id = parts[2]
            roles_to_remove = inter.values

            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})

            if "bonus_roles" in giveaway:
                for role_id in roles_to_remove:
                    giveaway["bonus_roles"].pop(role_id, None)

            db.salvar("database/giveaways/giveaways_data.json", config)

            await log_giveaway_event(
                bot=self.bot,
                giveaway_id=giveaway_id,
                title="Sorteios - Cargos Alterados",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway.get('name', 'N/A')}",
                    f"{emoji.delete} **Cargos Bônus Removidos:** `{len(roles_to_remove)}` cargo(s)",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )

            await inter.response.defer(ephemeral=True)
            await inter.followup.send(f"{emoji.correct} Cargos bônus removidos com sucesso!", ephemeral=True)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=BonusRolesView_components(inter, giveaway_id))
            else:
                embed, components = BonusRolesView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayTask_SelectChannel_"):
            parts = custom_id.split("_")
            giveaway_id = parts[2]
            task_id = parts[3]
            channel_id = int(inter.values[0])

            config = db.obter("database/giveaways/giveaways_data.json")
            task = next((t for t in config[giveaway_id].get("tasks", []) if t["id"] == task_id), None)
            if task:
                task["channel_id"] = channel_id
                db.salvar("database/giveaways/giveaways_data.json", config)

            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=TaskEditorView_components(inter, giveaway_id, task_id))
            else:
                embed, components = TaskEditorView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayTask_SelectMode_"):
            parts = custom_id.split("_")
            giveaway_id = parts[2]
            task_id = parts[3]
            selected_mode = inter.values[0]

            if selected_mode == "keyword":
                await inter.response.send_modal(KeywordModal(inter, giveaway_id, task_id))
            else:
                config = db.obter("database/giveaways/giveaways_data.json")
                task = next((t for t in config[giveaway_id].get("tasks", []) if t["id"] == task_id), None)
                if task:
                    task["participation_mode"] = selected_mode
                    db.salvar("database/giveaways/giveaways_data.json", config)

                await self._mode_aware_wait(inter)
                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=TaskEditorView_components(inter, giveaway_id, task_id))
                else:
                    embed, components = TaskEditorView_embed(inter, giveaway_id, task_id)
                    await inter.edit_original_message(content=None, embed=embed, components=components)

        elif custom_id.startswith("GiveawayEdit_SelectLogChannel_"):
            giveaway_id = custom_id.split("_")[-1]
            new_channel_id = int(inter.values[0])

            config = db.obter("database/giveaways/giveaways_data.json")
            if giveaway_id in config:
                config[giveaway_id]["log_channel_id"] = new_channel_id
                db.salvar("database/giveaways/giveaways_data.json", config)
                await log_giveaway_event(
                    bot=self.bot,
                    giveaway_id=giveaway_id,
                    title="Sorteios - Canal de Logs Alterado",
                    lines=[
                        f"{emoji.giveaway} **Sorteio:** {config[giveaway_id].get('name')}",
                        f"{emoji.edit} **Novo Canal:** <#{new_channel_id}>",
                        f"{emoji.member} **Executor:** {inter.author.mention}"
                    ]
                )

            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=SpecificGiveawayView_components(inter, giveaway_id))
            else:
                embed, components = SpecificGiveawayView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)


    async def handle_giveaway_edit_actions(self, inter, action, giveaway_id):
        mode = db.get_document("custom_mode").get("mode")
        await self._mode_aware_wait(inter)

        if action == "Preferences":
            if mode == "components":
                await inter.edit_original_message(components=PreferencesView_components(inter, giveaway_id))
            else:
                embed, components = PreferencesView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "ManageTasks":
            if mode == "components":
                await inter.edit_original_message(components=ManageTasksView_components(inter, giveaway_id))
            else:
                embed, components = ManageTasksView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "SetLogs":
            if mode == "components":
                await inter.edit_original_message(components=LogChannelSelectView_components(giveaway_id))
            else:
                embed, components = LogChannelSelectView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "SetMessage":
            await config_message.show_panel(inter, giveaway_id)
            return

        elif action == "BackToPanel":
            if mode == "components":
                await inter.edit_original_message(components=SpecificGiveawayView_components(inter, giveaway_id))
            else:
                embed, components = SpecificGiveawayView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "Rifa":
            if mode == "components":
                await inter.edit_original_message(components=RifaView_components(inter, giveaway_id))
            else:
                embed, components = RifaView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "Delete":
            config = db.obter("database/giveaways/giveaways_data.json")
            if giveaway_id in config:
                del config[giveaway_id]
                db.salvar("database/giveaways/giveaways_data.json", config)
                # Note: Logging will fail here as the giveaway data is deleted before logging can fetch the log channel.
                # This is a limitation for now. A possible fix is to pass the log channel ID to the log function.
                # For now, we accept that delete actions are not logged.

            await self.display_giveaways_panel(inter)

    async def handle_giveaway_task_actions(self, inter, custom_id):
        parts = custom_id.split("_")
        action = parts[1]
        giveaway_id = parts[2]
        task_id = parts[3] if len(parts) > 3 else None

        mode = db.get_document("custom_mode").get("mode")

        if action == "Create":
            await inter.response.send_modal(CreateTaskModal(inter, giveaway_id))
            return

        if action not in ["SendMessage", "ResendMessage", "CyclePartMode", "SetDuration", "Roll", "Reroll"] and not action.startswith("ConfirmRepost"):
            await self._mode_aware_wait(inter)

        if action == "Manage":
            if mode == "components":
                await inter.edit_original_message(components=SelectTaskView_components(inter, giveaway_id))
            else:
                embed, components = SelectTaskView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "SetDuration":
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway_data = config.get(giveaway_id, {})
            task_data = next((t for t in giveaway_data.get("tasks", []) if t.get("id") == task_id), {})
            await inter.response.send_modal(DurationModal(inter, giveaway_id, task_id, task_data))

        elif action == "SetChannel":
            if mode == "components":
                await inter.edit_original_message(components=ChannelSelectView_components(giveaway_id, task_id))
            else:
                embed, components = ChannelSelectView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "SetPartMode":
            if mode == "components":
                await inter.edit_original_message(components=ModeSelectView_components(giveaway_id, task_id))
            else:
                embed, components = ModeSelectView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "SetParticipants":
            if mode == "components":
                await inter.edit_original_message(components=await ParticipantsConfigView_components(inter, giveaway_id, task_id))
            else:
                embed, components = await ParticipantsConfigView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(embed=embed, components=components)

        elif action == "Roll":
            await inter.response.defer(ephemeral=True)
            await process_giveaway_roll(self.bot, giveaway_id, task_id, is_reroll=False)
            await inter.followup.send(f"{emoji.correct} O sorteio foi realizado com sucesso!", ephemeral=True)
            # Refresh the panel
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=TaskEditorView_components(inter, giveaway_id, task_id))
            else:
                embed, components = TaskEditorView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "Reroll":
            await inter.response.defer(ephemeral=True)
            await process_giveaway_roll(self.bot, giveaway_id, task_id, is_reroll=True)
            await inter.followup.send(f"{emoji.correct} Um novo sorteio foi realizado com sucesso!", ephemeral=True)
            # Refresh the panel
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=TaskEditorView_components(inter, giveaway_id, task_id))
            else:
                embed, components = TaskEditorView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "SendMessage":
            await self._send_giveaway_message(inter, giveaway_id, task_id)

        elif action == "ResendMessage":
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway_data = config.get(giveaway_id, {})
            task = next((t for t in giveaway_data.get("tasks", []) if t.get("id") == task_id), None)

            if task and task.get("status") in ["finished", "error"]:
                await self._mode_aware_wait(inter)
                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=RepostConfirmationView_components(giveaway_id, task_id))
                else:
                    embed, components = RepostConfirmationView_embed(giveaway_id, task_id)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                return

            await inter.response.defer(ephemeral=True)

            if task and task.get("message_id") and task.get("channel_id"):
                try:
                    channel = await self.bot.fetch_channel(task["channel_id"])
                    message_to_delete = await channel.fetch_message(task["message_id"])
                    await message_to_delete.delete()
                except (disnake.NotFound, disnake.Forbidden):
                    pass # Ignora se a mensagem ou canal não for encontrado ou não tiver permissão

            await self._send_giveaway_message(inter, giveaway_id, task_id, is_resend=True)

        elif action.startswith("ConfirmRepost"):
            await inter.response.defer(ephemeral=True)
            clear_previous_winners = "Clear" in action
            await self.process_repost(inter, giveaway_id, task_id, clear_previous_winners)

        elif action == "Delete":
            config = db.obter("database/giveaways/giveaways_data.json")
            if giveaway_id in config and "tasks" in config[giveaway_id]:
                config[giveaway_id]["tasks"] = [t for t in config[giveaway_id]["tasks"] if t["id"] != task_id]
                db.salvar("database/giveaways/giveaways_data.json", config)

            if mode == "components":
                await inter.edit_original_message(components=ManageTasksView_components(inter, giveaway_id))
            else:
                embed, components = ManageTasksView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "BackToEditor":
            if mode == "components":
                await inter.edit_original_message(components=TaskEditorView_components(inter, giveaway_id, task_id))
            else:
                embed, components = TaskEditorView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "BackToDashboard":
            if mode == "components":
                await inter.edit_original_message(components=ManageTasksView_components(inter, giveaway_id))
            else:
                embed, components = ManageTasksView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

    async def handle_giveaway_prize_actions(self, inter, custom_id):
        parts = custom_id.split("_")
        action = parts[1]
        giveaway_id = parts[2]

        if action == "ToggleDmNotify":
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            if "prize" not in giveaway: giveaway["prize"] = {}
            current_status = giveaway["prize"].get("dm_notify", True)
            new_status = not current_status
            giveaway["prize"]["dm_notify"] = new_status
            db.salvar("database/giveaways/giveaways_data.json", config)

            await log_giveaway_event(
                bot=self.bot, giveaway_id=giveaway_id, title="Sorteios - Premiação Alterada",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                    f"{emoji.edit} **Aviso na DM:** `{'Ativado' if new_status else 'Desativado'}`",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )

        elif action == "SetContent":
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            current_content = giveaway.get("prize", {}).get("content", "")
            await inter.response.send_modal(PrizeContentModal(inter, giveaway_id, current_content))
            return # Modal handles the refresh

        await self._mode_aware_wait(inter)
        mode = db.get_document("custom_mode").get("mode")
        if mode == "components":
            await inter.edit_original_message(components=PrizeView_components(inter, giveaway_id))
        else:
            embed, components = PrizeView_embed(inter, giveaway_id)
            await inter.edit_original_message(content=None, embed=embed, components=components)

    async def handle_giveaway_rifa_actions(self, inter: disnake.MessageInteraction, custom_id: str):
        parts = custom_id.split("_")
        action = parts[1]
        giveaway_id = parts[2]
        mode = db.get_document("custom_mode").get("mode")

        if action == "Config":
            config = db.obter("database/giveaways/giveaways_data.json")
            current_rifa = config.get(giveaway_id, {}).get("rifa", {})
            await inter.response.send_modal(RifaConfigModal(inter, giveaway_id, current_rifa))
            return

        await self._mode_aware_wait(inter)

        if action == "Toggle":
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway = config.get(giveaway_id, {})
            rifa = giveaway.setdefault("rifa", {})
            new_status = not rifa.get("enabled", False)
            rifa["enabled"] = new_status
            db.salvar("database/giveaways/giveaways_data.json", config)
            await log_giveaway_event(
                bot=self.bot, giveaway_id=giveaway_id,
                title="Sorteios - Rifa Alterada",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                    f"{emoji.edit} **Rifa:** `{'Ativada' if new_status else 'Desativada'}`",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )

        if mode == "components":
            await inter.edit_original_message(components=RifaView_components(inter, giveaway_id))
        else:
            embed, components = RifaView_embed(inter, giveaway_id)
            await inter.edit_original_message(content=None, embed=embed, components=components)

    async def handle_giveaway_participants_actions(self, inter, custom_id):
        parts = custom_id.split("_")
        action = parts[1]
        giveaway_id = parts[2]
        task_id = parts[3]

        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway_data = config.get(giveaway_id, {})
        task_data = next((t for t in giveaway_data.get("tasks", []) if t.get("id") == task_id), {})

        if action == "SetLimits":
            await inter.response.send_modal(LimitsModal(inter, giveaway_id, task_id, task_data))
        
        elif action == "Clear":
            await inter.response.defer(ephemeral=True)
            
            if not task_data or "participants" not in task_data:
                await inter.followup.send("Tarefa ou participantes não encontrados.", ephemeral=True)
                return
            
            participant_count = len(task_data["participants"])
            if participant_count == 0:
                await inter.followup.send("Não há participantes para limpar.", ephemeral=True)
                return

            task_data["participants"] = []
            db.salvar("database/giveaways/giveaways_data.json", config)

            await log_giveaway_event(
                bot=self.bot,
                giveaway_id=giveaway_id,
                title="Sorteios - Participantes Removidos",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway_data.get('name')}",
                    f"{emoji.settings} **Tarefa:** {task_data.get('name')}",
                    f"{emoji.delete} **Ação:** `{participant_count}` participante(s) removido(s) manualmente.",
                    f"{emoji.member} **Executor:** {inter.author.mention}"
                ]
            )
            
            # Update the original giveaway message
            if task_data.get("message_id") and task_data.get("channel_id"):
                try:
                    channel = self.bot.get_channel(task_data["channel_id"]) or await self.bot.fetch_channel(task_data["channel_id"])
                    message_to_edit = await channel.fetch_message(task_data["message_id"])

                    button_data = giveaway_data.get("button", {})
                    base_label = button_data.get("label", "Participar")
                    new_label = f"{base_label} (0)"

                    style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}

                    button_kwargs = {
                        "label": new_label,
                        "style": style_map.get(button_data.get("style", "green")),
                        "custom_id": f"Giveaway_Participate_{giveaway_id}_{task_id}"
                    }
                    if button_data.get("emoji"):
                        button_kwargs["emoji"] = button_data.get("emoji")

                    updated_button = disnake.ui.Button(**button_kwargs)
                    info_button = disnake.ui.Button(label="",emoji=emoji.information, style=disnake.ButtonStyle.grey, custom_id=f"Giveaway_Info_{giveaway_id}_{task_id}")

                    style = giveaway_data.get("message_style", "embed")
                    if style == "container":
                        data = giveaway_data.get("container", {})
                        container = ContainerUtils.montar_container(
                            conteudo=data.get("content"),
                            imagem_url=data.get("image_url"),
                            cor_hex=data.get("color"),
                            thumbnail_url=data.get("thumbnail_url")
                        )
                        action_row = disnake.ui.ActionRow(updated_button, info_button)
                        await message_to_edit.edit(components=[container, action_row])
                    else:
                        view = disnake.ui.View(timeout=None)
                        view.add_item(updated_button)
                        view.add_item(info_button)
                        await message_to_edit.edit(view=view)

                except (disnake.NotFound, disnake.Forbidden, KeyError):
                    pass # Silently fail if message cannot be updated

            await inter.followup.send(f"{emoji.correct} `{participant_count}` participante(s) foram removidos com sucesso!", ephemeral=True)
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                components = await ParticipantsConfigView_components(inter, giveaway_id, task_id)
                await inter.edit_original_message(components=components)
            else:
                embed, components = await ParticipantsConfigView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)
        
        elif action == "Back":
            await self._mode_aware_wait(inter)
            mode = db.get_document("custom_mode").get("mode")
            if mode == "components":
                await inter.edit_original_message(components=TaskEditorView_components(inter, giveaway_id, task_id))
            else:
                embed, components = TaskEditorView_embed(inter, giveaway_id, task_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

    async def handle_giveaway_roles_actions(self, inter, custom_id):
        await self._mode_aware_wait(inter)

        parts = custom_id.split("_")
        action = parts[1]
        giveaway_id = parts[2]
        mode = db.get_document("custom_mode").get("mode")

        giveaways = db.obter("database/giveaways/giveaways_data.json") or {}
        giveaway_data = giveaways.get(giveaway_id, {})
        giveaway_name = giveaway_data.get("name", "N/A")

        if action == "Allowed":
            if mode == "components":
                await inter.edit_original_message(components=AllowedRolesView_components(inter, giveaway_id, giveaway_name))
            else:
                embed, components = AllowedRolesView_embed(inter, giveaway_id, giveaway_name)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "Forbidden":
            if mode == "components":
                await inter.edit_original_message(components=ForbiddenRolesView_components(inter, giveaway_id, giveaway_name))
            else:
                embed, components = ForbiddenRolesView_embed(inter, giveaway_id, giveaway_name)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "Bonus":
            if mode == "components":
                await inter.edit_original_message(components=BonusRolesView_components(inter, giveaway_id))
            else:
                embed, components = BonusRolesView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "AddBonusRole":
            if mode == "components":
                await inter.edit_original_message(components=SelectBonusRoleView_components(giveaway_id, giveaway_name))
            else:
                embed, components = SelectBonusRoleView_embed(giveaway_id, giveaway_name)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "RemoveBonusRole":
            if mode == "components":
                await inter.edit_original_message(components=RemoveBonusRoleView_components(inter, giveaway_id, giveaway_name))
            else:
                embed, components = RemoveBonusRoleView_embed(inter, giveaway_id, giveaway_name)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "BackToPanel":
            if mode == "components":
                await inter.edit_original_message(components=RolesView_components(inter, giveaway_id))
            else:
                embed, components = RolesView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

    async def _send_giveaway_message(self, inter, giveaway_id, task_id, is_resend=False, refresh_panel=True):
        if not is_resend and not inter.response.is_done():
            await inter.response.defer(ephemeral=True)

        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway_data = config.get(giveaway_id, {})
        task = next((t for t in giveaway_data.get("tasks", []) if t.get("id") == task_id), None)

        if not task or not task.get("channel_id"):
            await inter.followup.send("O canal do sorteio não foi definido para esta tarefa.", ephemeral=True)
            return

        channel = self.bot.get_channel(task["channel_id"])
        if not channel:
            await inter.followup.send("Canal não encontrado ou eu não tenho acesso a ele.", ephemeral=True)
            return

        # Check if content is configured
        style = giveaway_data.get("message_style", "embed")
        content_configured = False
        if style == "embed":
            content_configured = bool(giveaway_data.get("embed", {}).get("title"))
        elif style == "content":
            content_data = giveaway_data.get("content", {})
            content_configured = bool(content_data.get("content") or content_data.get("image_url"))
        elif style == "container":
            content_configured = bool(giveaway_data.get("container", {}).get("content"))

        if not content_configured:
            await inter.followup.send("O conteúdo da mensagem do sorteio não foi configurado.", ephemeral=True)
            return

        send_kwargs = {}

        if style == "embed":
            embed_data = giveaway_data.get("embed", {})
            normalized_data = utils.normalize_embed_data(embed_data)
            embed = disnake.Embed.from_dict(normalized_data)
            send_kwargs["embed"] = embed
        elif style == "content":
            content_data = giveaway_data.get("content", {})
            send_kwargs["content"] = content_data.get("content")
            if "image_url" in content_data:
                send_kwargs["file"] = await utils.url_to_file(content_data["image_url"], "image.png")
        elif style == "container":
            data = giveaway_data.get("container", {})
            container = ContainerUtils.montar_container(
                conteudo=data.get("content"),
                imagem_url=data.get("image_url"),
                cor_hex=data.get("color"),
                thumbnail_url=data.get("thumbnail_url")
            )
            button_data = giveaway_data.get("button", {})
            style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}

            base_label = button_data.get("label", "Participar")
            participant_count = len(task.get("participants", []))

            button_kwargs = {
                "label": f"{base_label} ({participant_count})",
                "style": style_map.get(button_data.get("style", "green")),
                "custom_id": f"Giveaway_Participate_{giveaway_id}_{task_id}"
            }
            if button_data.get("emoji"):
                button_kwargs["emoji"] = button_data.get("emoji")
            button = disnake.ui.Button(**button_kwargs)
            info_button = disnake.ui.Button(
                label="", emoji=emoji.information, style=disnake.ButtonStyle.grey, custom_id=f"Giveaway_Info_{giveaway_id}_{task_id}"
            )
            action_row = disnake.ui.ActionRow(button, info_button)
            send_kwargs["components"] = [container, action_row]
            send_kwargs["flags"] = disnake.MessageFlags(is_components_v2=True)
            try:
                sent_message = await channel.send(**send_kwargs)
                task["message_id"] = sent_message.id
                task["status"] = "running"
                db.salvar("database/giveaways/giveaways_data.json", config)
                await inter.followup.send(f"Mensagem do sorteio enviada para {channel.mention}!", ephemeral=True)
            except disnake.Forbidden:
                await inter.followup.send("Eu não tenho permissão para enviar mensagens nesse canal.", ephemeral=True)
            except Exception as e:
                await inter.followup.send(f"Ocorreu um erro ao enviar a mensagem: {e}", ephemeral=True)
            finally:
                if refresh_panel:
                    # Refresh the panel
                    mode = db.get_document("custom_mode").get("mode")
                    if mode == "components":
                        await inter.edit_original_message(components=TaskEditorView_components(inter, giveaway_id, task_id))
                    else:
                        embed, components = TaskEditorView_embed(inter, giveaway_id, task_id)
                        await inter.edit_original_message(embed=embed, components=components)
            return

        button_data = giveaway_data.get("button", {})
        style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}

        base_label = button_data.get("label", "Participar")
        participant_count = len(task.get("participants", []))

        button_kwargs = {
            "label": f"{base_label} ({participant_count})",
            "style": style_map.get(button_data.get("style", "green")),
            "custom_id": f"Giveaway_Participate_{giveaway_id}_{task_id}"
        }
        if button_data.get("emoji"):
            button_kwargs["emoji"] = button_data.get("emoji")
        button = disnake.ui.Button(**button_kwargs)
        info_button = disnake.ui.Button(
            label="", emoji=emoji.information, style=disnake.ButtonStyle.grey, custom_id=f"Giveaway_Info_{giveaway_id}_{task_id}"
        )
        action_row = disnake.ui.ActionRow(button, info_button)

        view = disnake.ui.View(timeout=None)
        view.add_item(button)
        view.add_item(info_button)
        send_kwargs["view"] = view

        try:
            sent_message = await channel.send(**send_kwargs)
            task["message_id"] = sent_message.id
            task["status"] = "running"
            db.salvar("database/giveaways/giveaways_data.json", config)
            await inter.followup.send(f"Mensagem do sorteio enviada para {channel.mention}!", ephemeral=True)
        except disnake.Forbidden:
            await inter.followup.send("Eu não tenho permissão para enviar mensagens nesse canal.", ephemeral=True)
        except Exception as e:
            await inter.followup.send(f"Ocorreu um erro ao enviar a mensagem: {e}", ephemeral=True)
        finally:
            if refresh_panel:
                # Refresh the panel
                mode = db.get_document("custom_mode").get("mode")
                if mode == "components":
                    await inter.edit_original_message(components=TaskEditorView_components(inter, giveaway_id, task_id))
                else:
                    embed, components = TaskEditorView_embed(inter, giveaway_id, task_id)
                    await inter.edit_original_message(embed=embed, components=components)

    async def handle_giveaway_preferences_actions(self, inter, custom_id, action, giveaway_id):
        mode = db.get_document("custom_mode").get("mode")
        await self._mode_aware_wait(inter)

        if action == "BackToPreferences":
            if mode == "components":
                await inter.edit_original_message(components=PreferencesView_components(inter, giveaway_id))
            else:
                embed, components = PreferencesView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            return

        config = db.obter("database/giveaways/giveaways_data.json")
        if giveaway_id not in config:
            return

        if action == "SetMode":
            giveaway_mode = custom_id.split("_")[3]
            config[giveaway_id]["mode"] = giveaway_mode
            db.salvar("database/giveaways/giveaways_data.json", config)

            if mode == "components":
                await inter.edit_original_message(components=SpecificGiveawayView_components(inter, giveaway_id))
            else:
                embed, components = SpecificGiveawayView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

        elif action == "BackToPanel":
            if mode == "components":
                await inter.edit_original_message(components=SpecificGiveawayView_components(inter, giveaway_id))
            else:
                embed, components = SpecificGiveawayView_embed(inter, giveaway_id)
                await inter.edit_original_message(content=None, embed=embed, components=components)

    async def handle_giveaway_message_edit_actions(self, inter, custom_id):
        parts = custom_id.split("_", 2)
        action = parts[1]
        giveaway_id = parts[2] if len(parts) > 2 else None

        if action == "CycleStyle":
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway_data = config.get(giveaway_id, {})
            if not giveaway_data: return

            styles = ["embed", "content", "container"]
            current_style = giveaway_data.get("message_style", "embed")
            try:
                current_index = styles.index(current_style)
                new_style = styles[(current_index + 1) % len(styles)]
            except ValueError:
                new_style = "embed"

            giveaway_data["message_style"] = new_style
            db.salvar("database/giveaways/giveaways_data.json", config)
            await self._mode_aware_wait(inter)
            await config_message.show_panel(inter, giveaway_id)

        elif action == "EditButton":
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway_data = config.get(giveaway_id, {})
            button_data = giveaway_data.get("button", {})
            await inter.response.send_modal(config_message.EditButtonModal(giveaway_id=giveaway_id, data=button_data))

        elif action == "EditContent":
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway_data = config.get(giveaway_id, {})
            style = giveaway_data.get("message_style", "embed")

            if style == "embed":
                embed_data = giveaway_data.get("embed", {})
                await inter.response.send_modal(config_message.EditEmbedModal(giveaway_id=giveaway_id, data=embed_data))
            elif style == "content":
                content_data = giveaway_data.get("content", {})
                await inter.response.send_modal(config_message.EditContentModal(giveaway_id=giveaway_id, data=content_data))
            elif style == "container":
                container_data = giveaway_data.get("container", {})
                await inter.response.send_modal(config_message.EditContainerModal(giveaway_id=giveaway_id, data=container_data))

        elif action == "Preview":
            await inter.response.defer(ephemeral=True)
            config = db.obter("database/giveaways/giveaways_data.json")
            giveaway_data = config.get(giveaway_id, {})
            style = giveaway_data.get("message_style", "embed")

            send_kwargs = {}

            if style == "embed":
                embed_data = giveaway_data.get("embed", {})
                if not embed_data:
                    embed_data = {"title": "Título de Exemplo", "description": "Descrição de exemplo."}
                normalized_data = utils.normalize_embed_data(embed_data)
                embed = disnake.Embed.from_dict(normalized_data)
                send_kwargs["embed"] = embed
            elif style == "content":
                content_data = giveaway_data.get("content", {})
                send_kwargs["content"] = content_data.get("content", "Conteúdo de exemplo.")
            elif style == "container":
                data = giveaway_data.get("container", {})
                container = ContainerUtils.montar_container(
                    conteudo=data.get("content"),
                    imagem_url=data.get("image_url"),
                    cor_hex=data.get("color"),
                    thumbnail_url=data.get("thumbnail_url")
                )
                send_kwargs["components"] = [container]
                send_kwargs["flags"] = disnake.MessageFlags(is_components_v2=True)

            button_data = giveaway_data.get("button", {})
            style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}

            button_kwargs = {
                "label": button_data.get("label", "Participar"),
                "style": style_map.get(button_data.get("style", "green")),
                "custom_id": "do_nothing"
            }
            if button_data.get("emoji"):
                button_kwargs["emoji"] = button_data.get("emoji")

            button = disnake.ui.Button(**button_kwargs)
            info_button = disnake.ui.Button(label="",emoji=emoji.information, style=disnake.ButtonStyle.grey, custom_id="do_nothing_info")


            if style != "container":
                view = disnake.ui.View()
                view.add_item(button)
                view.add_item(info_button)
                send_kwargs["view"] = view
            else:
                if "components" not in send_kwargs:
                    send_kwargs["components"] = []
                send_kwargs["components"].append(disnake.ui.ActionRow(button, info_button))

            await inter.followup.send(**send_kwargs, ephemeral=True)

    def find_task_by_message_id(self, message_id):
        config = db.obter("database/giveaways/giveaways_data.json")
        for giveaway_id, giveaway in config.items():
            for task in giveaway.get("tasks", []):
                if str(task.get("message_id")) == str(message_id):
                    return giveaway_id, giveaway, task
        return None, None, None

    async def show_giveaway_info(self, inter, giveaway, task, giveaway_id, task_id):
        participants = task.get("participants", [])
        from .preferences.requirements import REQUIREMENTS_CONFIG
        requirements = giveaway.get("requirements", {})
        req_list = []
        if requirements:
            for req_key, req_data in requirements.items():
                if req_data.get("enabled"):
                    req_config = REQUIREMENTS_CONFIG.get(req_key)
                    if req_config:
                        label = req_config.get("label")
                        value = req_data.get("value")
                        if value:
                            if isinstance(value, list):
                                value_str = ", ".join(f"<@&{v}>" if "role" in req_key else f"<@{v}>" for v in value)
                            elif isinstance(value, int) and "channel" in req_key:
                                value_str = f"<#{value}>"
                            else:
                                value_str = f"`{value}`"
                            req_list.append(f"{emoji.correct} {label}: {value_str}")
                        else:
                            req_list.append(f"{emoji.correct} {label}")
        requirements_str = "\n".join(req_list) if req_list else "`Nenhum requisito`"
        
        bonus_roles = giveaway.get("bonus_roles", {})
        bonus_roles_list = []
        if bonus_roles:
            for role_id, entries in bonus_roles.items():
                role = inter.guild.get_role(int(role_id))
                if role:
                    bonus_roles_list.append(f"{role.mention}: `+{entries} {'entrada' if entries == 1 else 'entradas'}`")
        bonus_roles_str = "\n".join(bonus_roles_list) if bonus_roles_list else "`Nenhum cargo bônus`"

        prize = giveaway.get("prize", {})
        prize_type = prize.get("type", "none")
        prize_str = ""
        if prize_type == "none":
            prize_str = "`Nada será entregue automaticamente.`"
        elif prize_type == "content":
            dm_notify = prize.get("dm_notify", True)
            prize_str = "Conteúdo a ser enviado na DM"
            if not dm_notify:
                prize_str += " (Aviso na DM desativado)"
            if prize.get("content"):
                 prize_str += "\n`Um conteúdo customizado foi configurado.`"
        author_id = task.get("author_id") or giveaway.get("author_id")
        author = inter.guild.get_member(author_id) if author_id else None
        author_str = author.mention if author else "`Desconhecido`"
        created_at = task.get("created_at") or giveaway.get("created_at")
        created_at_str = f"<t:{created_at}:f>" if created_at else "`Desconhecida`"
        start_time = task.get("start_time")
        start_time_str = f"<t:{int(start_time)}:f>" if start_time else "`Não definida`"
        end_time = task.get("end_time")
        end_time_str = f"<t:{int(end_time)}:f>" if end_time else "`Não definida`"
        min_participants = task.get("min_participants", "N/A")
        max_participants = task.get("max_participants", "N/A")
        participants_str = f"`{min_participants}` / `{max_participants}`"
        max_winners = task.get('max_winners', 1)
        info_str = (
            f"**Criador da tarefa:** {author_str}\n"
            f"**Tarefa criada em:** {created_at_str}\n"
            f"**Início:** {start_time_str}\n"
            f"**Sorteio:** {end_time_str}\n"
            f"**Participantes (Mín/Máx):** {participants_str}\n"
            f"**Quantidade de Ganhadores:** `{max_winners}`"
        )
        winners = task.get("winners", [])
        winners_str = ""
        if winners:
            winners_str = "\n".join(f"<@{winner_id}>" for winner_id in winners)
        else:
            winners_str = "`Ainda não sorteado`"
        mode = db.get_document("custom_mode").get("mode")
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        generate_list_button = disnake.ui.Button(
            label="Gerar Lista de Participantes",
            style=disnake.ButtonStyle.secondary,
            custom_id=f"Giveaway_GenerateList_{giveaway_id}_{task_id}",
            disabled=not participants,
            emoji=emoji.members
        )
        if mode == "embed":
            embed = disnake.Embed(title=f"Informações do Sorteio")
            if primary_color_hex:
                try:
                    embed.color = disnake.Color(int(primary_color_hex.lstrip("#"), 16))
                except (ValueError, TypeError):
                    pass
            embed.add_field(name="Detalhes", value=info_str, inline=False)
            embed.add_field(name="Ganhador(es)", value=winners_str, inline=False)
            embed.add_field(name="Requisitos", value=requirements_str, inline=False)
            embed.add_field(name="Cargos Bônus", value=bonus_roles_str, inline=False)
            embed.add_field(name="Premiação", value=prize_str, inline=False)
            await inter.followup.send(embed=embed, components=[generate_list_button], ephemeral=True)
        else:
            full_info_content = (
                f"**Detalhes:**\n{info_str}\n\n"
                f"**Ganhador(es):**\n{winners_str}\n\n"
                f"**Requisitos:**\n{requirements_str}\n\n"
                f"**Cargos Bônus:**\n{bonus_roles_str}\n\n"
                f"**Premiação:**\n{prize_str}"
            )
            container_kwargs = {}
            if primary_color_hex:
                try:
                    container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                except (ValueError, TypeError):
                    pass
            container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# **Informações do Sorteio**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(full_info_content),
                **container_kwargs
            )
            await inter.followup.send(
                components=[container, disnake.ui.ActionRow(generate_list_button)],
                ephemeral=True,
                flags=disnake.MessageFlags(is_components_v2=True)
            )

    async def generate_participant_list(self, inter, giveaway, task, giveaway_id, task_id):
        participants = task.get("participants", [])
        if not participants:
            await inter.followup.send("Não há participantes neste sorteio para gerar uma lista.", ephemeral=True)
            return
        
        # Count entries per user
        from collections import Counter
        entry_counts = Counter(participants)
        
        lines = []
        for user_id, count in entry_counts.items():
            user = inter.guild.get_member(user_id)
            if user:
                if count > 1:
                    lines.append(f"{user.name} - ({user.id}) - {user.mention} ({count}x entradas)")
                else:
                    lines.append(f"{user.name} - ({user.id}) - {user.mention}")
            else:
                try:
                    user_obj = await self.bot.fetch_user(user_id)
                    if count > 1:
                        lines.append(f"{user_obj.name} - ({user_obj.id}) - <@{user_obj.id}> ({count}x entradas) (Fora do servidor)")
                    else:
                        lines.append(f"{user_obj.name} - ({user_obj.id}) - <@{user_obj.id}> (Fora do servidor)")
                except disnake.NotFound:
                    if count > 1:
                        lines.append(f"Usuário não encontrado - ({user_id}) ({count}x entradas)")
                    else:
                        lines.append(f"Usuário não encontrado - ({user_id})")
        
        file_content = "\n".join(lines)
        import io
        file = disnake.File(
            io.BytesIO(file_content.encode('utf-8')),
            filename=f"participantes_{giveaway.get('name', giveaway_id)}.txt"
        )
        await inter.followup.send("Aqui está a lista de participantes:", file=file, ephemeral=True)

    async def handle_giveaway_participation(self, inter, custom_id):
        await inter.response.defer(ephemeral=True)

        try:
            _, _, giveaway_id, task_id = custom_id.split("_")
        except ValueError:
            await inter.followup.send("Ocorreu um erro ao processar sua participação (ID inválido).", ephemeral=True)
            return

        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway = config.get(giveaway_id)
        if not giveaway:
            await inter.followup.send("Este sorteio não foi encontrado.", ephemeral=True)
            return

        task = next((t for t in giveaway.get("tasks", []) if t["id"] == task_id), None)
        if not task:
            await inter.followup.send("A tarefa deste sorteio não foi encontrada.", ephemeral=True)
            return

        # Verificar se o sorteio já foi encerrado
        if task.get("rolled", False):
            await inter.followup.send(f"{emoji.wrong} Este sorteio já foi encerrado! Não é mais possível participar.", ephemeral=True)
            return

        # Verificar se é rifa (participação por pagamento)
        rifa_data = giveaway.get("rifa", {})
        if rifa_data.get("enabled"):
            price = rifa_data.get("ticket_price", 0)
            per_user = rifa_data.get("tickets_per_user", 1)
            participants = task.get("participants", [])
            user_tickets = participants.count(user_id := inter.author.id)
            max_t = rifa_data.get("max_tickets", 0)

            if max_t and len(participants) >= max_t:
                await inter.followup.send(f"{emoji.wrong} Todos os bilhetes já foram vendidos!", ephemeral=True)
                return
            if user_tickets >= per_user:
                await inter.followup.send(
                    f"{emoji.wrong} Você já comprou o máximo de **{per_user}** bilhete(s).", ephemeral=True)
                return

            await inter.followup.send(
                f"**{emoji.giveaway} Sorteio do tipo Rifa**\n"
                f"Preço por bilhete: **R$ {price:.2f}**\n"
                f"Seus bilhetes: **{user_tickets}/{per_user}**",
                components=[disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label=f"Comprar Bilhete — R$ {price:.2f}",
                        style=disnake.ButtonStyle.green,
                        custom_id=f"Giveaway_BuyTicket_{giveaway_id}_{task_id}"
                    )
                )],
                ephemeral=True
            )
            return

        member_roles = {r.id for r in inter.author.roles}
        allowed_roles = set(giveaway.get("allowed_roles", []))
        forbidden_roles = set(giveaway.get("forbidden_roles", []))

        if allowed_roles and not member_roles.intersection(allowed_roles):
            await inter.followup.send(f"{emoji.wrong} Você não tem um dos cargos permitidos para entrar neste sorteio.", ephemeral=True)
            return
        
        if forbidden_roles and member_roles.intersection(forbidden_roles):
            await inter.followup.send(f"{emoji.wrong} Você possui um cargo que não é permitido neste sorteio.", ephemeral=True)
            return

        user_id = inter.author.id
        max_entries = 1
        bonus_roles = giveaway.get("bonus_roles", {})
        if bonus_roles:
            member_role_ids = {str(r.id) for r in inter.author.roles}
            for role_id, bonus_entries in bonus_roles.items():
                if role_id in member_role_ids:
                    max_entries += int(bonus_entries)

        if "participants" not in task:
            task["participants"] = []
        
        current_entries = task["participants"].count(user_id)

        if current_entries < max_entries:
            if current_entries == 0:
                requirements_success, requirements_error = await check_giveaway_requirements(inter.author, giveaway_id, self.bot)
                if not requirements_success:
                    await inter.followup.send(requirements_error, ephemeral=True)
                    return
            
            task["participants"].append(user_id)
            if max_entries > 1:
                feedback_message = f"{emoji.correct} Você adicionou mais uma entrada! Agora você tem **{current_entries + 1}/{max_entries}** entradas."
            else:
                feedback_message = f"{emoji.correct} Você entrou no sorteio com sucesso!"
            
            log_title = "Sorteios - Entrada de Participante" if current_entries == 0 else "Sorteios - Entrada Bônus Adicionada"
            log_action = "Entrou no sorteio" if current_entries == 0 else f"Adicionou entrada bônus ({current_entries + 1}/{max_entries})"
            
            await log_giveaway_event(
                bot=self.bot,
                giveaway_id=giveaway_id,
                title=log_title,
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                    f"{emoji.member} **Membro:** {inter.author.mention} (`{inter.author.id}`)",
                    f"{emoji.correct} **Ação:** {log_action}"
                ]
            )
        else:
            num_removed = task["participants"].count(user_id)
            task["participants"] = [p for p in task["participants"] if p != user_id]
            if max_entries > 1:
                feedback_message = f"{emoji.correct} Você removeu suas **{num_removed}** entradas do sorteio."
            else:
                feedback_message = f"{emoji.correct} Você saiu do sorteio com sucesso!"

            await log_giveaway_event(
                bot=self.bot,
                giveaway_id=giveaway_id,
                title="Sorteios - Saída de Participante",
                lines=[
                    f"{emoji.giveaway} **Sorteio:** {giveaway.get('name')}",
                    f"{emoji.member} **Membro:** {inter.author.mention} (`{inter.author.id}`)",
                    f"{emoji.wrong} **Ação:** {'Saiu do sorteio' if num_removed == 1 else f'Saiu do sorteio (removeu {num_removed} entradas)'}"
                ]
            )

        db.salvar("database/giveaways/giveaways_data.json", config) 
        await inter.followup.send(feedback_message, ephemeral=True)

        # Update the message button
        try:
            message_to_edit = await inter.channel.fetch_message(task["message_id"])

            button_data = giveaway.get("button", {})
            base_label = button_data.get("label", "Participar")
            participant_count = len(task.get("participants", []))
            new_label = f"{base_label} ({participant_count})"

            style_map = {"green": disnake.ButtonStyle.green, "grey": disnake.ButtonStyle.grey, "red": disnake.ButtonStyle.red, "blue": disnake.ButtonStyle.primary}

            button_kwargs = {
                "label": new_label,
                "style": style_map.get(button_data.get("style", "green")),
                "custom_id": custom_id
            }
            if button_data.get("emoji"):
                button_kwargs["emoji"] = button_data.get("emoji")

            updated_button = disnake.ui.Button(**button_kwargs)
            info_button = disnake.ui.Button(label="",emoji=emoji.information, style=disnake.ButtonStyle.grey, custom_id=f"Giveaway_Info_{giveaway_id}_{task_id}")

            style = giveaway.get("message_style", "embed")
            if style == "container":
                data = giveaway.get("container", {})
                container = ContainerUtils.montar_container(
                    conteudo=data.get("content"),
                    imagem_url=data.get("image_url"),
                    cor_hex=data.get("color"),
                    thumbnail_url=data.get("thumbnail_url")
                )
                action_row = disnake.ui.ActionRow(updated_button, info_button)
                await message_to_edit.edit(components=[container, action_row])
            else:
                view = disnake.ui.View(timeout=None)
                view.add_item(updated_button)
                view.add_item(info_button)
                await message_to_edit.edit(view=view)
        except (disnake.NotFound, disnake.Forbidden, KeyError):
            pass # Silently fail if message cannot be edited.

    async def process_repost(self, inter: disnake.MessageInteraction, giveaway_id: str, task_id: str, clear_previous_winners: bool):
        config = db.obter("database/giveaways/giveaways_data.json")
        giveaway_data = config.get(giveaway_id, {})
        task = next((t for t in giveaway_data.get("tasks", []) if t.get("id") == task_id), None)

        if not giveaway_data or not task:
            await inter.followup.send("Sorteio ou tarefa não encontrados ao tentar repostar.", ephemeral=True)
            return

        # 1. Handle winners
        previous_winners = set(task.get("previous_winners", []))
        if clear_previous_winners:
            previous_winners = set()

        current_winners = set(task.get("winners", []))
        previous_winners.update(current_winners)

        task["previous_winners"] = list(previous_winners)
        task["winners"] = []
        task["draws"] = []
        old_message_id = task.get("message_id")
        task["message_id"] = None # Clear old message ID before resending

        # 2. Delete old message
        if old_message_id and task.get("channel_id"):
            try:
                channel = await self.bot.fetch_channel(task["channel_id"])
                message_to_delete = await channel.fetch_message(old_message_id)
                await message_to_delete.delete()
            except (disnake.NotFound, disnake.Forbidden):
                pass # Ignore if message is already gone

        # Save changes before sending new message
        db.salvar("database/giveaways/giveaways_data.json", config)

        await self._send_giveaway_message(inter, giveaway_id, task_id, is_resend=True)

def setup(bot: commands.Bot):
    bot.add_cog(Giveaways(bot))