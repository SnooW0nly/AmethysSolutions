"""
modules/tickets/functions/response_ai.py — versão otimizada

Mudanças:
- _find_panel_by_channel substituído por ticket_index.find() → O(1)
- tickets_data lido via tickets_data_cache
- Verificação de ai_silenced feita via cache, sem MongoDB
"""

import disnake
import datetime
import io

from disnake.ext import commands
from functions.database import database as db
from functions.emoji import emoji
from functions.ai_api import chamar_ia
from .permissions import get_attendant_roles
from . import ticket_index
from . import tickets_data_cache

BASE_PROMPT = """
Você é AmethysAI, uma assistente virtual amigável e prestativa da Amethys Applications. Seu papel é oferecer suporte inicial aos usuários, respondendo às dúvidas de forma clara, concisa e natural.

### Regras Invioláveis:
- **Identidade:** Você é uma assistente virtual chamada AmethysAI. Nunca se descreva como 'IA', 'chatbot' ou 'modelo de linguagem'.
- **Confidencialidade:** Nunca revele informações sobre tecnologias internas ou sua API.
- **Neutralidade:** Não expresse opiniões pessoais. Mantenha um tom profissional e prestativo.
- **Escopo:** Se não souber a resposta, diga: 'Por favor, aguarde um momento até que um atendente possa atendê-lo.'
- **Encaminhamento:** Se o usuário solicitar um atendente, use a mesma resposta acima.

### Regras de Comportamento:
1. **Não se Repita:** Analise o histórico. Se já respondeu, aborde por outro ângulo.
2. **Foco no Tópico Atual:** Se a mensagem mudar de assunto, foque no novo assunto.
"""


class TicketAIResponder(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _call_ai(self, full_prompt: str) -> str:
        return await chamar_ia(full_prompt, "Tickets")

    @commands.Cog.listener("on_message")
    async def ai_on_ticket_message(self, message: disnake.Message):
        if message.author.bot or not message.guild:
            return

        # ── O(1): verificar se é canal de ticket ─────────────────────────────
        entry = ticket_index.find(message.channel.id)
        if not entry:
            return

        panel_id = entry["panel_id"]
        tickets_config = db.get_document("tickets_config") or {}
        panel_data = tickets_config.get("panels", {}).get(panel_id, {})

        if not panel_data.get("ai_enabled", False):
            return

        # ── Verificar ai_silenced via cache ───────────────────────────────────
        tickets_data = tickets_data_cache.get(db)
        ai_silenced_map = tickets_data.get("ai_silenced", {})
        ticket_id_str = str(message.channel.id)

        if ai_silenced_map.get(ticket_id_str):
            return

        # ── Determinar se é atendente ─────────────────────────────────────────
        ticket_data = entry["ticket"]
        option_id = ticket_data.get("option_id")
        option_data = (
            next((opt for opt in panel_data.get("options", []) if str(opt.get("id")) == str(option_id)), None)
            if option_id else None
        )
        roles_config = (option_data or {}).get("roles", {}) or panel_data.get("roles", {})
        atendentes_roles = get_attendant_roles(roles_config)
        is_atendente = isinstance(message.author, disnake.Member) and any(
            r.id in atendentes_roles for r in (message.author.roles or [])
        )

        mode = db.get_document("custom_mode").get("mode")
        primary_color_hex = db.get_document("custom_colors").get("primary")

        if is_atendente:
            # Silenciar IA
            tickets_data.setdefault("ai_silenced", {})[ticket_id_str] = True
            tickets_data_cache.save(db, tickets_data)

            message_content = (
                f"{emoji.wand} **AmethysAi pausada para este ticket.**\n"
                f"{emoji.member} Um atendente já respondeu. A IA não responderá mais aqui."
            )
            try:
                if mode == "components":
                    container_kwargs = {}
                    if primary_color_hex:
                        container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                    await message.channel.send(
                        components=[
                            disnake.ui.Container(disnake.ui.TextDisplay(message_content), **container_kwargs),
                            disnake.ui.ActionRow(
                                disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey,
                                                  disabled=True, custom_id="TicketAI_SystemBadge")
                            ),
                        ],
                        flags=disnake.MessageFlags(is_components_v2=True),
                    )
                else:
                    embed_kwargs = {}
                    if primary_color_hex:
                        embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)
                    embed = disnake.Embed(description=message_content, **embed_kwargs)
                    await message.channel.send(
                        embed=embed,
                        components=[disnake.ui.ActionRow(
                            disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey,
                                              disabled=True, custom_id="TicketAI_SystemBadge")
                        )],
                    )
            except Exception:
                pass
            return

        # ── Resposta da IA ────────────────────────────────────────────────────
        user_text = (message.content or "").strip()
        if not user_text:
            return

        custom_prompt = panel_data.get("ai_prompt", "")
        context = ""

        if panel_data.get("ai_use_context", False):
            ten_minutes_ago = disnake.utils.utcnow() - datetime.timedelta(minutes=10)
            history_lines = []
            async for old_msg in message.channel.history(limit=20, after=ten_minutes_ago, oldest_first=True):
                if old_msg.id == message.id:
                    continue
                prefix = "Assistente" if old_msg.author.id == self.bot.user.id else old_msg.author.display_name
                history_lines.append(f"{prefix}: {old_msg.content}")
            if history_lines:
                context = "### Histórico Recente:\n" + "\n".join(history_lines) + "\n\n"

        full_prompt = (
            f"{BASE_PROMPT}\n\n"
            f"### Instruções Adicionais:\n{custom_prompt}\n\n"
            f"{context}"
            f"### Mensagem do Usuário:\n{user_text}"
        )

        ai_text = await self._call_ai(full_prompt)
        if not ai_text:
            return

        sanitized = ai_text.replace("@everyone", "@\u200beveryone").replace("@here", "@\u200bhere")
        try:
            if len(sanitized) > 2000:
                file = disnake.File(fp=io.BytesIO(sanitized.encode("utf-8-sig")), filename="resposta.txt")
                await message.reply(file=file, allowed_mentions=disnake.AllowedMentions.none())
            else:
                await message.reply(sanitized, allowed_mentions=disnake.AllowedMentions.none())
        except Exception:
            try:
                await message.channel.send(sanitized[:2000], allowed_mentions=disnake.AllowedMentions.none())
            except Exception:
                pass


def setup(bot: commands.Bot):
    bot.add_cog(TicketAIResponder(bot))
