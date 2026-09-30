"""
modules/tickets/functions/cog.py  — versão otimizada

Mudanças principais:
1. _find_panel_by_channel substituído por ticket_index.find() → O(1)
2. on_ticket_message consolidado: atualiza last_activity e delega AI ao response_ai.py
   (elimina o listener duplicado que rodava 2× por mensagem)
3. tickets_data lido via tickets_data_cache (evita hit MongoDB por mensagem)
4. Índice reconstruído no startup via on_ready
"""

import disnake
from disnake.ext import commands

from .create_ticket import create_ticket_handler
from .setup_functions.close_ticket import CloseTicketModal, close_ticket
from functions.database import database as db
from functions.emoji import emoji
from functions.perms import perms
from functions.ai_api import chamar_ia
from .setup_team import AttendantSetupView
from .setup_member import UserSetupView
from . import setup_functions as sfp
from .setup_functions.transfer import transfer_ticket
from .permissions import check_attendant_permissions, get_attendant_roles

from .info import ticket_info
from .setup_functions.show_history import show_history
from .create_ticket import check_and_create_ticket
from .open_ticket import open_ticket
from functions.message import embed_message as message

# ── Novos módulos de otimização ──────────────────────────────────────────────
from . import ticket_index
from . import tickets_data_cache

BASE_PROMPT_FALLBACK = (
    "Você é AmethysAI, uma assistente virtual amigável e prestativa. "
    "Responda de forma direta, útil e educada."
)


class TicketFunctionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ── Startup: constrói o índice uma única vez ──────────────────────────────
    @commands.Cog.listener("on_ready")
    async def _build_index_on_ready(self):
        tickets_data = tickets_data_cache.get(db)
        ticket_index.rebuild_index(tickets_data)
        print("[TicketFunctionsCog] Índice de tickets reconstruído.")

    # ── Helper O(1) ───────────────────────────────────────────────────────────
    @staticmethod
    def _find_panel_by_channel(channel_id: int):
        """
        Substitui o antigo loop O(n³).
        Retorna (panel_id, panel_data, ticket_dict) ou (None, {}, None).
        """
        entry = ticket_index.find(channel_id)
        if not entry:
            return None, {}, None
        panel_id = entry["panel_id"]
        tickets_config = db.get_document("tickets_config") or {}
        panel_data = tickets_config.get("panels", {}).get(panel_id, {})
        return panel_id, panel_data, entry["ticket"]

    async def _call_ai(self, full_prompt: str) -> str:
        return await chamar_ia(full_prompt, "Tickets")

    # ── Listeners de botão ────────────────────────────────────────────────────
    @commands.Cog.listener("on_button_click")
    async def ticket_actions_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        if custom_id.startswith("ticket_form_open:"):
            parts = custom_id.split(":")
            panel_id = parts[1] if len(parts) >= 2 else None
            option_id = parts[2] if len(parts) >= 3 else None
            if not panel_id or not option_id:
                await inter.response.send_message("Erro ao processar solicitação.", ephemeral=True)
                return
            config = db.get_document("tickets_config") or {}
            panel_data = config.get("panels", {}).get(panel_id)
            if not panel_data:
                await inter.response.send_message("Painel de ticket não encontrado.", ephemeral=True)
                return
            questions = panel_data.get("forms", {}).get(option_id, [])
            if not questions:
                await inter.response.send_message("Formulário não encontrado.", ephemeral=True)
                return
            option_data = next(
                (opt for opt in panel_data.get("options", []) if str(opt.get("id")) == str(option_id)),
                None
            )
            from .open_ticket import TicketFormModal
            modal = TicketFormModal(inter, self.bot, panel_data, panel_id, questions, option_data)
            await inter.response.send_modal(modal)
            return

        if custom_id.startswith("create_ticket_"):
            panel_id = custom_id.split("_")[-1]
            await create_ticket_handler(inter, self.bot, panel_id)

        elif custom_id in ["close_ticket", "ticket_close_ticket", "ticket_close_ticket_user"]:
            panel_id, panel_data, _ = self._find_panel_by_channel(inter.channel.id)
            require_reason = panel_data.get("preferences", {}).get("require_reason", {}).get("enabled", False)
            if require_reason:
                await inter.response.send_modal(CloseTicketModal(self.bot, inter.channel, require_reason=True))
            else:
                await close_ticket(bot=self.bot, channel=inter.channel, closed_by=inter.author, inter=inter)

        elif custom_id == "ticket_attendant_setup":
            await inter.response.defer(ephemeral=True)
            panel_id, panel_data, ticket_data = self._find_panel_by_channel(inter.channel.id)
            if not panel_data:
                return await inter.followup.send(
                    f"{emoji.wrong} Não foi possível encontrar a configuração para este ticket.", ephemeral=True
                )
            has_permission = await check_attendant_permissions(inter.author, inter.channel.id)
            if not has_permission:
                return await inter.followup.send(
                    f"{emoji.wrong} Você não tem permissão para usar este botão.", ephemeral=True
                )
            option_id = ticket_data.get("option_id") if ticket_data else None
            option_data = (
                next((opt for opt in panel_data.get("options", []) if str(opt.get("id")) == str(option_id)), None)
                if option_id else None
            )
            view = AttendantSetupView(panel_data, option_data)
            if not view.children:
                await inter.followup.send("Essa função está desativada.", ephemeral=True)
            else:
                await inter.followup.send(view=view, ephemeral=True)

        elif custom_id == "ticket_user_setup":
            await inter.response.defer(ephemeral=True)
            panel_id, panel_data, ticket_data = self._find_panel_by_channel(inter.channel.id)
            if not panel_data:
                return await inter.followup.send(
                    f"{emoji.wrong} Não foi possível encontrar a configuração para este ticket.", ephemeral=True
                )
            option_id = ticket_data.get("option_id") if ticket_data else None
            option_data = (
                next((opt for opt in panel_data.get("options", []) if str(opt.get("id")) == str(option_id)), None)
                if option_id else None
            )
            view = UserSetupView(panel_data, option_data)
            if not view.children:
                await inter.followup.send("Essa função está desativada.", ephemeral=True)
            else:
                await inter.followup.send(view=view, ephemeral=True)

        elif custom_id == "ticket_info":
            await ticket_info(inter)
        elif custom_id == "ticket_rename":
            await sfp.rename_ticket(inter)
        elif custom_id == "ticket_set_priority":
            await sfp.set_priority(inter, self.bot)
        elif custom_id == "ticket_resolved":
            await sfp.resolved_ticket(inter)
        elif custom_id == "ticket_claim":
            await sfp.assume_ticket(inter)
        elif custom_id == "ticket_add_user":
            await sfp.add_user(inter)
        elif custom_id == "ticket_remove_user":
            await sfp.remove_user(inter)
        elif custom_id == "ticket_notify":
            await sfp.notify(inter)
        elif custom_id == "ticket_create_call":
            await sfp.create_call(inter)
        elif custom_id == "ticket_transcript":
            await sfp.transcript(inter, self.bot)
        elif custom_id == "ticket_history":
            await sfp.show_history(inter)
        elif custom_id == "ticket_notes":
            await sfp.notes(inter)
        elif custom_id == "ticket_transfer":
            await transfer_ticket(inter)
        elif custom_id == "ticket_payment":
            await sfp.generate_pay(inter)
        elif custom_id == "ticket_add_user_user":
            await sfp.add_user(inter)
        elif custom_id == "ticket_remove_user_user":
            await sfp.remove_user(inter)
        elif custom_id == "ticket_transcript_user":
            await sfp.transcript(inter, self.bot)
        elif custom_id == "ticket_review":
            await sfp.review(inter)
        elif custom_id == "ticket_notify_user":
            await sfp.notify(inter)
        elif custom_id == "ticket_transfer_user":
            await transfer_ticket(inter)
        elif custom_id == "ticket_payment_user":
            await sfp.generate_pay(inter)
        elif custom_id == "ticket_request_call_user":
            await sfp.request_call(inter)
        elif custom_id == "ticket_approve_call_request":
            await sfp.approve_call_request(inter)
        elif custom_id == "ticket_archive":
            await sfp.archive_ticket(inter)
        elif custom_id == "ticket_unarchive":
            await sfp.unarchive_ticket(inter)

    @commands.Cog.listener("on_dropdown")
    async def ticket_dropdown_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("ticket_panel_option_select_"):
            return

        # Defer imediato antes de qualquer I/O para não expirar a interação (3s limit)
        await inter.response.defer(ephemeral=True)

        panel_id = custom_id.replace("ticket_panel_option_select_", "")
        option_id = inter.values[0]
        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id)
        if not panel_data:
            await inter.followup.send("Painel de ticket não encontrado.", ephemeral=True)
            return
        options = panel_data.get("options", [])
        selected_option = next((opt for opt in options if str(opt.get("id")) == option_id), None)
        if not selected_option:
            await inter.followup.send("Opção selecionada inválida.", ephemeral=True)
            return
        await check_and_create_ticket(inter, self.bot, panel_id, selected_option)

    # ── on_message: apenas atualiza last_activity ─────────────────────────────
    # A resposta de IA fica exclusivamente em response_ai.py para evitar
    # processamento duplicado que travava o bot sob carga.
    @commands.Cog.listener("on_message")
    async def on_ticket_message(self, message_obj: disnake.Message):
        if message_obj.author.bot or not message_obj.guild:
            return

        entry = ticket_index.find(message_obj.channel.id)
        if not entry:
            return

        # Atualiza last_activity de forma eficiente (sem recarregar tickets_data)
        ticket = entry["ticket"]
        ticket["last_activity_timestamp"] = int(message_obj.created_at.timestamp())

        # Salva de forma assíncrona sem bloquear o event loop principal
        tickets_data = tickets_data_cache.get(db)
        tickets_data_cache.save(db, tickets_data)

        # ── Auto-assumir na primeira mensagem do staff ─────────────────────────
        # Só executa se o ticket ainda não foi assumido por ninguém
        if ticket.get("assumed_by"):
            return

        panel_id = entry.get("panel_id")
        if not panel_id:
            return

        config = db.get_document("tickets_config") or {}
        panel_data = config.get("panels", {}).get(panel_id, {})

        if not panel_data.get("auto_assume_on_first_message", False):
            return

        # Verificar se o autor da mensagem é um atendente/staff do painel
        from .permissions import check_attendant_permissions, get_attendant_roles
        has_permission = await check_attendant_permissions(message_obj.author, message_obj.channel.id)
        if not has_permission:
            return

        # Assumir o ticket automaticamente
        ticket["assumed_by"] = message_obj.author.id
        tickets_data_cache.save(db, tickets_data)

        from .history import log_ticket_event
        log_ticket_event(message_obj.channel.id, "assume", message_obj.author.id)

        from ...utils import SafeFormatter
        messages = panel_data.get("messages", {})
        message_template = messages.get("assume_message", "{autor_mention} assumiu o atendimento deste ticket.")

        ticket_owner_id = entry.get("user_id") or entry.get("owner_id")
        ticket_owner = message_obj.guild.get_member(int(ticket_owner_id)) if ticket_owner_id else None

        placeholders = SafeFormatter(
            autor_mention=message_obj.author.mention,
            autor_name=message_obj.author.name,
            channel_name=message_obj.channel.name,
            guild_name=message_obj.guild.name,
            user_mention=ticket_owner.mention if ticket_owner else "usuário desconhecido",
            user_name=ticket_owner.name if ticket_owner else "usuário desconhecido"
        )
        formatted_message = message_template.format_map(placeholders)

        try:
            await message_obj.channel.send(formatted_message)
        except Exception:
            pass

        try:
            if ticket_owner:
                dm_template = messages.get("assume_dm_message", "Olá {user_mention}, o atendente {autor_mention} assumiu seu ticket `{channel_name}`.")
                dm_message = dm_template.format_map(placeholders)
                button = disnake.ui.Button(label="Ir para o Ticket", style=disnake.ButtonStyle.link, url=message_obj.channel.jump_url)
                await ticket_owner.send(dm_message, components=[button])
        except Exception:
            pass


def setup(bot: commands.Bot):
    bot.add_cog(TicketFunctionsCog(bot))
