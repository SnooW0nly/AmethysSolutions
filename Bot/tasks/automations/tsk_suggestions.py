import disnake
from disnake.ext import commands, tasks
from modules.automations.suggestions.helpers import SuggestionsDB
from modules.automations.suggestions.cog import SuggestionsUI
from functions.database import database as db
from functions.emoji import emoji
from datetime import datetime, timedelta

class SuggestionsTaskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = SuggestionsDB()
        self.ui = SuggestionsUI(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.check_suggestions_votes.is_running():
            self.check_suggestions_votes.start()

    def cog_unload(self):
        self.check_suggestions_votes.cancel()

    @tasks.loop(minutes=5)
    async def check_suggestions_votes(self):
        config = self.db.get_config()
        auto_mod_config = config.get("auto_moderation", {})

        if not auto_mod_config.get("enabled"):
            return

        approval_delay_hours = auto_mod_config.get("approval_delay_hours", 24)
        min_creation_time = datetime.utcnow() - timedelta(hours=approval_delay_hours)

        open_suggestions = {
            s_id: s_data for s_id, s_data in config.get("sugestoes", {}).items()
            if s_data.get("status") == "aberta"
        }

        mode = auto_mod_config.get("mode", "porcentagem")

        for s_id, s_data in open_suggestions.items():
            created_at_str = s_data.get("created_at")
            if not created_at_str:
                continue

            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                continue

            if created_at > min_creation_time:
                continue

            upvotes = len(s_data.get("upvotes", []))
            downvotes = len(s_data.get("downvotes", []))
            total_votes = upvotes + downvotes
            
            if total_votes == 0:
                continue

            action = None

            approval_threshold = auto_mod_config.get("approval_threshold", 75)
            if mode == "porcentagem":
                approval_percentage = (upvotes / total_votes) * 100
                if approval_percentage >= approval_threshold:
                    action = "approve"
            elif mode == "quantidade":
                if upvotes >= approval_threshold:
                    action = "approve"
            
            if action is None:
                rejection_threshold = auto_mod_config.get("rejection_threshold", 75)
                if mode == "porcentagem":
                    rejection_percentage = (downvotes / total_votes) * 100
                    if rejection_percentage >= rejection_threshold:
                        action = "reject"
                elif mode == "quantidade":
                    if downvotes >= rejection_threshold:
                        action = "reject"

            if action:
                await self.moderate_suggestion(s_id, action)

    async def moderate_suggestion(self, sugestao_id: str, action: str):
        self.db.update_status(sugestao_id, "aprovada" if action == "approve" else "reprovada", self.bot.user.id)
        
        config = self.db.get_config()
        sugestao = config.get("sugestoes", {}).get(sugestao_id)
        if not sugestao: return

        channel = self.bot.get_channel(config.get("channel"))
        original_message = None
        if channel:
            try:
                original_message = await channel.fetch_message(sugestao.get("message_id"))
            except (disnake.NotFound, disnake.Forbidden):
                pass
        
        if original_message:
            mode = sugestao.get("message_type", db.get_document("custom_mode").get("mode"))
            render_data = await self.ui.gerar_msg_sugestao(original_message, sugestao_id)
            if mode == "embed":
                embed, components = render_data
                await original_message.edit(embed=embed, components=components)
            else:
                components = render_data
                await original_message.edit(components=components)

            thread = original_message.thread
            if thread:
                action_message = f"{emoji.correct} Sugestão aprovada automaticamente." if action == "approve" else f"{emoji.wrong} Sugestão reprovada automaticamente."
                try:
                    components = [
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, disabled=True)
                        )
                    ]
                    await thread.send(action_message, components=components)
                except disnake.Forbidden: pass

    @check_suggestions_votes.before_loop
    async def before_check_suggestions_votes(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: disnake.Message):
        if not message.guild or message.author.bot:
            return

        # Se o SuggestionsCog principal estiver carregado, não processar aqui para evitar duplicidade
        if self.bot.get_cog("SuggestionsCog") is not None:
            return

        config = self.db.get_config()
        if not config.get("status") or message.channel.id != config.get("channel"):
            return

        immune_role_id = config.get("immune_role_id")
        if immune_role_id and isinstance(message.author, disnake.Member):
            if any(role.id == immune_role_id for role in message.author.roles):
                return

        # Capturar conteúdo de forma robusta antes de deletar a mensagem
        content_text = (message.content or "").strip()
        if not content_text:
            parts = []
            try:
                # Referência (resposta)
                if message.reference and getattr(message.reference, "resolved", None):
                    ref = message.reference.resolved
                    if isinstance(ref, disnake.Message):
                        ref_snippet = (ref.content or "").strip()
                        if ref_snippet:
                            parts.append(f"Respondendo: {ref_snippet[:200]}")
            except Exception:
                pass
            # Anexos
            if getattr(message, "attachments", None):
                if len(message.attachments) > 0:
                    parts.append("Anexos:\n" + "\n".join(att.url for att in message.attachments))
            # Figurinhas (stickers)
            if getattr(message, "stickers", None):
                if len(message.stickers) > 0:
                    parts.append("Stickers: " + ", ".join(st.name for st in message.stickers))
            # Embeds (não há conteúdo textual primário)
            if getattr(message, "embeds", None):
                if len(message.embeds) > 0 and not parts:
                    parts.append("(Mensagem contendo embeds)")
            content_text = "\n".join(parts).strip() or "[sem conteúdo]"

        # Tentar deletar a mensagem original, ignorando NotFound
        try:
            await message.delete()
        except disnake.NotFound:
            pass

        mode = db.get_document("custom_mode").get("mode")
        sugestao_id = self.db.add_suggestion(message.author.id, content_text, mode)

        # Renderizar e enviar a sugestão conforme o modo
        sugestao_render_data = await self.ui.gerar_msg_sugestao(message, sugestao_id)
        sugestao_msg = None

        if mode == "embed":
            embed, components = sugestao_render_data
            sugestao_msg = await message.channel.send(embed=embed, components=components)
        else:
            components = sugestao_render_data
            sugestao_msg = await message.channel.send(components=components)

        # Salvar message_id e criar tópico se configurado
        if sugestao_msg:
            self.db.update_suggestion_message_id(sugestao_id, sugestao_msg.id)

            if config.get("create_threads", True):
                try:
                    thread_message = config.get("thread_message", "{user}, este tópico foi criado para discutir a sua sugestão.")
                    formatted_message = thread_message.replace("{user}", message.author.mention)

                    thread = await sugestao_msg.create_thread(name=f"Discussão da sugestão de {message.author.name}")
                    await thread.send(formatted_message)
                except disnake.HTTPException:
                    pass 

def setup(bot: commands.Bot):
    bot.add_cog(SuggestionsTaskCog(bot))
