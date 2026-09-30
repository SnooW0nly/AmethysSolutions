import disnake
from disnake.ext import commands
import asyncio
import time
from disnake.ui import Modal, TextInput
from functions.database import database as db
from functions.transcript_cache import delete_link_from_cache, save_link_to_cache
from ..logs_tickets import log_ticket_closure
from functions.emoji import emoji
import traceback
import os
from ...transcripts import generate_transcript
from ...transcripts.host_transcript import log_transcript, upload_transcript_to_api
from ...utils import SafeFormatter
from .. import ticket_index
from .. import tickets_data_cache


class CloseTicketModal(Modal):
    def __init__(self, bot, channel: disnake.TextChannel, require_reason: bool = False):
        self.bot = bot
        self.channel = channel

        reason_label = "Motivo do Fechamento"
        if not require_reason:
            reason_label += " (Opcional)"

        components = [
            TextInput(
                label=reason_label,
                placeholder="Digite o motivo do fechamento do ticket.",
                custom_id="reason",
                style=disnake.TextInputStyle.paragraph,
                max_length=2000,
                required=require_reason
            )
        ]
        super().__init__(title="Fechar Ticket", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        reason = inter.text_values.get("reason")
        await close_ticket(bot=self.bot, channel=inter.channel, closed_by=inter.author, reason=reason, inter=inter)


async def close_ticket(
    bot: commands.Bot,
    channel: disnake.TextChannel,
    closed_by: disnake.Member,
    reason: str = None,
    inter: disnake.Interaction = None
):
    if inter:
        await inter.response.defer(ephemeral=True)

    config = db.get_document("tickets_config") or {}

    # ── Usar cache para evitar hit MongoDB desnecessário ──────────────────────
    tickets_data = tickets_data_cache.get(db)

    found_panel_id = None
    ticket_found = False
    ticket_owner_id = None
    ticket = None

    for panel_id, users in tickets_data.get("panels", {}).items():
        for user_id, tickets in users.items():
            for t in tickets:
                if t.get("ticket_id") == channel.id and t.get("status") == "open":
                    t["status"] = "closed"
                    t["closed_at"] = int(time.time())
                    t["closed_by"] = closed_by.id
                    t["channel_name"] = channel.name
                    if reason:
                        t["close_reason"] = reason

                    details = {"channel_name": channel.name}
                    if reason:
                        details["reason"] = reason

                    if "history" not in t:
                        t["history"] = []

                    t["history"].append({
                        "type": "close",
                        "author_id": closed_by.id,
                        "timestamp": int(time.time()),
                        "details": details,
                    })

                    ticket_found = True
                    ticket_owner_id = user_id
                    found_panel_id = panel_id
                    ticket = t
                    break
            if ticket_found:
                break
        if ticket_found:
            break

    if not ticket_found:
        if inter:
            await inter.followup.send("Este canal não parece ser um ticket aberto.", ephemeral=True)
        return

    # ── Remover do índice imediatamente ──────────────────────────────────────
    ticket_index.unregister(channel.id)

    # ── Apagar call de voz se existir ─────────────────────────────────────────
    call_channel_id = ticket.get("call_channel_id") if ticket else None
    if call_channel_id:
        try:
            call_channel = await bot.fetch_channel(call_channel_id)
            if call_channel:
                await call_channel.delete(reason="Ticket fechado")
        except disnake.NotFound:
            pass
        except disnake.Forbidden:
            pass
        except Exception:
            traceback.print_exc()

    # ── Limpar ai_silenced ────────────────────────────────────────────────────
    if "ai_silenced" in tickets_data:
        tickets_data["ai_silenced"].pop(str(channel.id), None)

    # ── Salvar via cache (write-through) ──────────────────────────────────────
    tickets_data_cache.save(db, tickets_data)

    panel_data = config.get("panels", {}).get(found_panel_id, {})
    ticket_mode = panel_data.get("mode") or "channel"
    ticket_owner = bot.get_user(int(ticket_owner_id)) if ticket_owner_id else None

    # ── Gerar transcript ──────────────────────────────────────────────────────
    delete_link_from_cache(channel.id)
    transcript_file = await generate_transcript(channel, bot)

    final_transcript_url = None
    if transcript_file:
        transcript_file.fp.seek(0)
        transcript_html = transcript_file.fp.read().decode("utf-8")
        final_transcript_url = await upload_transcript_to_api(transcript_html, channel.name)
        if final_transcript_url:
            save_link_to_cache(channel.id, final_transcript_url)

    # ── Log de fechamento ─────────────────────────────────────────────────────
    closure_log_message = await log_ticket_closure(bot, channel, closed_by, ticket_owner, ticket_mode, reason)

    if final_transcript_url and closure_log_message:
        try:
            await closure_log_message.reply(
                content=f"Aqui está o transcript que você solicitou para o ticket **{channel.name}**:",
                components=[
                    disnake.ui.ActionRow(
                        disnake.ui.Button(
                            label="Ver transcript",
                            style=disnake.ButtonStyle.link,
                            url=final_transcript_url,
                        )
                    )
                ],
            )
        except Exception as e:
            print(f"[TRANSCRIPT] Erro ao enviar link final nos logs: {e}")

    # ── Notificar dono do ticket via DM ───────────────────────────────────────
    notification_sent = False
    send_dm_pref = panel_data.get("preferences", {}).get("send_close_message", {})
    send_dm_enabled = send_dm_pref.get("enabled", True)

    if ticket_owner and send_dm_enabled:
        messages = panel_data.get("messages", {})
        send_transcript = panel_data.get("preferences", {}).get("transcripts", {}).get("send_on_close", False)

        if reason:
            base_message = messages.get(
                "close_message_reason",
                "Seu ticket `{channel_name}` foi fechado por `{autor_mention}`.\n**Motivo:** {reason}"
            )
        else:
            base_message = messages.get(
                "close_message",
                "Seu ticket `{channel_name}` foi fechado por `{autor_mention}`."
            )

        placeholders = SafeFormatter(
            channel_name=channel.name,
            guild_name=channel.guild.name,
            autor_mention=closed_by.mention,
            autor_name=closed_by.name,
            user_mention=ticket_owner.mention,
            user_name=ticket_owner.name,
            reason=reason,
        )
        close_message_content = base_message.format_map(placeholders)

        payload = {
            "content": close_message_content,
            "components": [
                disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, disabled=True)
            ],
        }

        if send_transcript and final_transcript_url:
            transcript_message_template = messages.get(
                "transcript_message",
                "Aqui está o transcript do seu ticket `{channel_name}`."
            )
            transcript_message_content = transcript_message_template.format_map(placeholders)
            payload["content"] = f"{close_message_content}\n\n{transcript_message_content}"
            payload["components"] = [
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Ver transcript",
                        style=disnake.ButtonStyle.link,
                        url=final_transcript_url,
                    )
                )
            ]

        try:
            await ticket_owner.send(**payload)
            notification_sent = True
        except (disnake.Forbidden, disnake.HTTPException):
            pass

    # ── Limpar cache de transcript ────────────────────────────────────────────
    delete_link_from_cache(channel.id)

    # ── Feedback e exclusão do canal ──────────────────────────────────────────
    feedback_message = f"Ticket fechado por {closed_by.mention}. "
    if send_dm_enabled:
        if notification_sent:
            feedback_message += "O usuário foi notificado na DM."
        else:
            feedback_message += "Não foi possível notificar o usuário (DM fechada ou não encontrado)."

    delete_timestamp = int(time.time()) + 5
    if inter:
        await inter.followup.send(
            f"{feedback_message} Este canal será excluído <t:{delete_timestamp}:R>."
        )

    await asyncio.sleep(5)
    try:
        await channel.delete()
    except disnake.NotFound:
        pass
