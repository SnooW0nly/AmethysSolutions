import disnake
from disnake.ext import commands
import json
from functions.message import message, embed_message
from functions.emoji import emoji
from . import helpers
from functions.database import database as db
from typing import Union

class ThreadMessageModal(disnake.ui.Modal):
    def __init__(self, ui_cog: 'SuggestionsCog'):
        self.ui_cog = ui_cog
        self.db = ui_cog.db
        current_message = self.db.get_config().get("thread_message", "{user}, este tópico foi criado para discutir a sua sugestão.")
        
        components = [
            disnake.ui.TextInput(
                label="Mensagem do Tópico",
                placeholder="Use {user} para mencionar o autor.",
                custom_id="thread_message_input",
                style=disnake.TextInputStyle.paragraph,
                value=current_message,
                max_length=2000
            )
        ]
        super().__init__(title="Editar Mensagem do Tópico", components=components, custom_id="thread_message_modal")

    async def callback(self, inter: disnake.ModalInteraction):
        new_message = inter.text_values["thread_message_input"]
        self.db.set_thread_message(new_message)
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await inter.response.defer()
            embed, components = self.ui_cog.ui.PainelEmbed(inter.guild)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.response.edit_message(components=self.ui_cog.ui.Painel(inter.guild))

class AutoModerationModal(disnake.ui.Modal):
    def __init__(self, ui_cog: 'SuggestionsCog'):
        self.ui_cog = ui_cog
        self.db = ui_cog.db
        config = self.db.get_config().get("auto_moderation", {})

        components = [
            disnake.ui.TextInput(
                label="Modo (quantidade/porcentagem)",
                custom_id="mode",
                value=config.get("mode", "porcentagem"),
                placeholder="Ex: quantidade, porcentagem",
                max_length=11,
            ),
            disnake.ui.TextInput(
                label="Votos de Aprovação (Apenas números)",
                custom_id="approval_threshold",
                value=str(config.get("approval_threshold", "75")),
                placeholder="Ex: 60",
                max_length=6,
            ),
            disnake.ui.TextInput(
                label="Votos de Rejeição (Apenas números)",
                custom_id="rejection_threshold",
                value=str(config.get("rejection_threshold", "75")),
                placeholder="Ex: 40",
                max_length=6,
            ),
            disnake.ui.TextInput(
                label="Tempo mínimo para moderação (horas)",
                custom_id="approval_delay_hours",
                value=str(config.get("approval_delay_hours", "24")),
                placeholder="Ex: 24",
                max_length=4,
            ),
        ]
        super().__init__(title="Configurar Limites", components=components, custom_id="auto_moderation_modal")

    async def callback(self, inter: disnake.ModalInteraction):
        values = inter.text_values
        mode = values["mode"].lower()
        approval_str = values["approval_threshold"]
        rejection_str = values["rejection_threshold"]
        approval_delay_hours_str = values["approval_delay_hours"]

        errors = []
        if mode not in ["quantidade", "porcentagem"]:
            errors.append(f"{emoji.arrow} O modo deve ser 'quantidade' ou 'porcentagem'.")
        
        approval_val = 0
        if not approval_str.isdigit():
            errors.append(f"{emoji.arrow} Votos de aprovação deve ser um número inteiro (Exemplo: 75).")
        else:
            approval_val = int(approval_str)
            if not 1 <= approval_val <= 100000:
                errors.append(f"{emoji.arrow} Votos de aprovação deve estar entre 1 e 100000.")

        rejection_val = 0
        if not rejection_str.isdigit():
            errors.append(f"{emoji.arrow} Votos de rejeição deve ser um número inteiro (Exemplo: 75).")
        else:
            rejection_val = int(rejection_str)
            if not 1 <= rejection_val <= 100000:
                errors.append("- Votos de rejeição deve estar entre 1 e 100.000.")

        approval_delay_hours_val = 0
        if not approval_delay_hours_str.isdigit():
            errors.append(f"{emoji.arrow} O tempo mínimo para moderação deve ser um número inteiro (Ex: 24).")
        else:
            approval_delay_hours_val = int(approval_delay_hours_str)
            if not 0 <= approval_delay_hours_val <= 8760:
                errors.append(f"{emoji.arrow} O tempo mínimo para moderação deve estar entre 0 e 8760 horas.")

        if mode == "porcentagem" and approval_val + rejection_val != 100:
            errors.append(f"{emoji.arrow} Em modo 'porcentagem', a soma da aprovação e rejeição deve ser exatamente 100.")

        if errors:
            await inter.response.send_message(f"{emoji.wrong} **Erros de Validação:**\n" + "\n".join(errors), ephemeral=True)
            return

        current_config = self.db.get_config().get("auto_moderation", {})
        new_config = {
            "enabled": current_config.get("enabled", False),
            "mode": mode,
            "approval_threshold": int(approval_str),
            "rejection_threshold": int(rejection_str),
            "approval_delay_hours": int(approval_delay_hours_str)
        }

        self.db.set_auto_moderation(new_config)
        
        db_mode = db.get_document("custom_mode").get("mode")
        if db_mode == "embed":
            await inter.response.defer()
            embed, components = self.ui_cog.ui.PainelEmbed(inter.guild)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.response.edit_message(components=self.ui_cog.ui.Painel(inter.guild))

def has_moderation_permission(user: disnake.User | disnake.Member) -> bool:
    """Verifica se o usuário tem permissão para moderar sugestões usando a classe perms."""
    from functions.perms import perms as perms_module
    import asyncio
    
    # Verificar se é owner ou tem permissão via perms
    try:
        # Usar run_coroutine_threadsafe para chamar a função async de forma síncrona
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Se já está em um event loop, criar uma task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, perms_module.check(user.id))
                has_perm = future.result(timeout=5)
        else:
            has_perm = asyncio.run(perms_module.check(user.id))
        
        if has_perm:
            return True
    except Exception:
        pass

    if isinstance(user, disnake.Member):
        try:
            cargos_data = db.get_document("cargos")
            admin_role_id = cargos_data.get('cargo_admin')
            if admin_role_id and any(role.id == int(admin_role_id) for role in user.roles):
                return True
        except ValueError:
            pass

    return False

class ModerationActionsView(disnake.ui.View):
    def __init__(self, bot: commands.Bot, db: helpers.SuggestionsDB, sugestao_id: str):
        super().__init__(timeout=180)
        self.bot = bot
        self.db = db
        self.sugestao_id = sugestao_id

    async def perform_action(self, inter: disnake.MessageInteraction, action: str):
        for child in self.children:
            child.disabled = True
        await inter.response.edit_message(content=f"{emoji.loading} Processando sua ação...", view=None)

        config = self.db.get_config()
        sugestao = config.get("sugestoes", {}).get(self.sugestao_id)

        if not sugestao:
            await inter.edit_original_message(content="Esta sugestão não foi encontrada.", view=None)
            return

        channel = self.bot.get_channel(config.get("channel"))
        original_message = None
        if channel:
            try:
                original_message = await channel.fetch_message(sugestao.get("message_id"))
            except (disnake.NotFound, disnake.Forbidden):
                pass
        
        thread = original_message.thread if original_message else None

        action_messages = {
            "approve": f"{emoji.correct} Sugestão aprovada pelo moderador {inter.author.mention}.",
            "reject": f"{emoji.wrong} Sugestão reprovada pelo moderador {inter.author.mention}.",
        }
        
        if action == "approve":
            self.db.update_status(self.sugestao_id, "aprovada", inter.author.id)
        elif action == "reject":
            self.db.update_status(self.sugestao_id, "reprovada", inter.author.id)
        
        if original_message:
            sugestao_obj = self.db.get_config().get("sugestoes", {}).get(self.sugestao_id, {})
            mode_val = sugestao_obj.get("message_type", db.get_document("custom_mode").get("mode"))
            mode = mode_val.get("mode") if isinstance(mode_val, dict) else mode_val
            if mode == "embed":
                embed, components = await inter.bot.get_cog("SuggestionsCog").ui.gerar_msg_sugestao(original_message, self.sugestao_id)
                await original_message.edit(embed=embed, components=components)
            else:
                components = await inter.bot.get_cog("SuggestionsCog").ui.gerar_msg_sugestao(original_message, self.sugestao_id)
                await original_message.edit(components=components)

        notification = action_messages.get(action)
        if thread and notification:
            try:
                components = [
                    disnake.ui.ActionRow(
                        disnake.ui.Button(label="Mensagem do Sistema", style=disnake.ButtonStyle.grey, disabled=True)
                    )
                ]
                await thread.send(notification, components=components)
            except disnake.Forbidden:
                pass
        
        feedback_messages = {
            "approve": f"{emoji.correct} **Sugestão Aprovada!**\nO status foi atualizado e uma notificação foi enviada no tópico.",
            "reject": f"{emoji.wrong} **Sugestão Reprovada!**\nO status foi atualizado e uma notificação foi enviada no tópico.",
        }
        await inter.edit_original_message(content=feedback_messages.get(action), view=None)
        self.stop()

    @disnake.ui.button(label="Aprovar", style=disnake.ButtonStyle.green, emoji=emoji.correct)
    async def approve_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.perform_action(inter, "approve")

    @disnake.ui.button(label="Reprovar", style=disnake.ButtonStyle.red, emoji=emoji.wrong)
    async def reject_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await self.perform_action(inter, "reject")

    @disnake.ui.button(label="Apagar", style=disnake.ButtonStyle.grey, emoji=emoji.delete)
    async def delete_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        await inter.response.edit_message(content=f"{emoji.loading} Apagando sugestão...", view=None)

        config = self.db.get_config()
        sugestao = config.get("sugestoes", {}).get(self.sugestao_id)

        if not sugestao:
            await inter.edit_original_message(content="Esta sugestão não foi encontrada.", view=None)
            return

        channel = self.bot.get_channel(config.get("channel"))
        original_message = None
        if channel:
            try:
                original_message = await channel.fetch_message(sugestao.get("message_id"))
            except (disnake.NotFound, disnake.Forbidden):
                pass
        
        thread = original_message.thread if original_message else None

        self.db.delete_suggestion(self.sugestao_id)
        if thread:
            try:
                await thread.delete()
            except disnake.HTTPException: pass
        if original_message:
            try:
                await original_message.delete()
            except disnake.HTTPException: pass

        await inter.edit_original_message(
            content=f"{emoji.delete} **Sugestão Apagada!**\nA mensagem original e seu tópico foram removidos.", 
            view=None
        )
        self.stop()
    
class SuggestionsUI:
    def __init__(self, bot):
        self.bot = bot
        self.db = helpers.SuggestionsDB()

    def Painel(self, guild: disnake.Guild) -> list[disnake.ui.Container]:
        config = self.db.get_config()
        status = config.get("status", False)
        channel_id = config.get("channel")
        channel = self.bot.get_channel(channel_id) if channel_id else None
        immune_role_id = config.get("immune_role_id")
        immune_role = guild.get_role(immune_role_id) if immune_role_id else None
        create_threads = config.get("create_threads", True)
        auto_mod_config = config.get("auto_moderation", {})
        auto_mod_enabled = auto_mod_config.get("enabled", False)

        resumo = (
            f"{emoji.on if status else emoji.off} **Status:** `{'Ativado' if status else 'Desativado'}`\n"
            f"{emoji.on if create_threads else emoji.off} **Criar Tópicos:** `{'Ativado' if create_threads else 'Desativado'}`\n"
            f"{emoji.on if auto_mod_enabled else emoji.off} **Moderação Automática:** `{'Ativado' if auto_mod_enabled else 'Desativado'}`\n"
            f"{emoji.textc} **Canal Configurado:** {channel.mention if channel else '`Nenhum`'}\n"
            f"{emoji.role} **Cargo Imune:** {immune_role.mention if immune_role else '`Nenhum`'}"
        )

        resumo_auto_mod = (
            f"{emoji.like} **Aprovação:** "
            f"`{auto_mod_config.get('approval_threshold', 0)}{'%' if auto_mod_config.get('mode') == 'porcentagem' else ' votos'}`\n"
            f"{emoji.deslike} **Rejeição:** "
            f"`{auto_mod_config.get('rejection_threshold', 0)}{'%' if auto_mod_config.get('mode') == 'porcentagem' else ' votos'}`\n"
            f"{emoji.clock} **Tempo Mínimo:** `{auto_mod_config.get('approval_delay_hours', 24)} hr`"
        )
        botoes_config = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Sugestoes_ToggleStatus"),
            disnake.ui.Button(label="Configurar Canal", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id="Sugestoes_SetChannel", disabled=not status),
            disnake.ui.Button(label="Cargo Imune", style=disnake.ButtonStyle.blurple, emoji=emoji.role, custom_id="Sugestoes_SetImmuneRole", disabled=not status)
        ]
        
        botoes_topico = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Sugestoes_ToggleCreateThreads", disabled=not status),
            disnake.ui.Button(label="Editar Mensagem", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Sugestoes_EditThreadMessage", disabled=not status or not create_threads)
        ]

        botoes_auto_mod = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Sugestoes_ToggleAutoMod", disabled=not status),
            disnake.ui.Button(label="Configurar Limites", style=disnake.ButtonStyle.blurple, emoji=emoji.config, custom_id="Sugestoes_AutoModModal", disabled=not status or not auto_mod_enabled)
        ]
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > **Sugestões**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.large),
                disnake.ui.TextDisplay("-# Configurar Sistema de Sugestões"),
                disnake.ui.ActionRow(*botoes_config),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.large),
                disnake.ui.TextDisplay("-# Configurar Criação de Tópicos"),
                disnake.ui.ActionRow(*botoes_topico),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.large),
                disnake.ui.TextDisplay("-# Moderação Automática\n" + resumo_auto_mod),
                disnake.ui.ActionRow(*botoes_auto_mod),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]

    def PainelEmbed(self, guild: disnake.Guild) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = self.db.get_config()
        status = config.get("status", False)
        channel_id = config.get("channel")
        channel = self.bot.get_channel(channel_id) if channel_id else None
        immune_role_id = config.get("immune_role_id")
        immune_role = guild.get_role(immune_role_id) if immune_role_id else None
        create_threads = config.get("create_threads", True)
        auto_mod_config = config.get("auto_moderation", {})
        auto_mod_enabled = auto_mod_config.get("enabled", False)

        resumo = (
            f"{emoji.on if status else emoji.off} **Status:** `{'Ativado' if status else 'Desativado'}`\n"
            f"{emoji.on if create_threads else emoji.off} **Criar Tópicos:** `{'Ativado' if create_threads else 'Desativado'}`\n"
            f"{emoji.on if auto_mod_enabled else emoji.off} **Moderação Automática:** `{'Ativado' if auto_mod_enabled else 'Desativado'}`\n"
            f"{emoji.textc} **Canal Configurado:** {channel.mention if channel else '`Nenhum`'}\n"
            f"{emoji.role} **Cargo Imune:** {immune_role.mention if immune_role else '`Nenhum`'}"
        )

        resumo_auto_mod = (
            f"{emoji.like} **Aprovação:** "
            f"`{auto_mod_config.get('approval_threshold', 0)}{'%' if auto_mod_config.get('mode') == 'porcentagem' else ' votos'}`\n"
            f"{emoji.deslike} **Rejeição:** "
            f"`{auto_mod_config.get('rejection_threshold', 0)}{'%' if auto_mod_config.get('mode') == 'porcentagem' else ' votos'}`\n"
            f"{emoji.clock} **Tempo Mínimo:** `{auto_mod_config.get('approval_delay_hours', 24)} hr`"
        )
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Sistema de Sugestões",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        embed.add_field(name="Configurações Gerais", value=resumo, inline=False)
        embed.add_field(name="Moderação Automática", value=resumo_auto_mod, inline=False)

        botoes_config = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Sugestoes_ToggleStatus"),
            disnake.ui.Button(label="Configurar Canal", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id="Sugestoes_SetChannel", disabled=not status),
            disnake.ui.Button(label="Cargo Imune", style=disnake.ButtonStyle.blurple, emoji=emoji.role, custom_id="Sugestoes_SetImmuneRole", disabled=not status)
        ]
        
        botoes_topico = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Sugestoes_ToggleCreateThreads", disabled=not status),
            disnake.ui.Button(label="Editar Mensagem", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Sugestoes_EditThreadMessage", disabled=not status or not create_threads)
        ]
        
        botoes_auto_mod = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Sugestoes_ToggleAutoMod", disabled=not status),
            disnake.ui.Button(label="Configurar Limites", style=disnake.ButtonStyle.blurple, emoji=emoji.config, custom_id="Sugestoes_AutoModModal", disabled=not status or not auto_mod_enabled)
        ]

        components = [
            disnake.ui.ActionRow(*botoes_config),
            disnake.ui.ActionRow(*botoes_topico),
            disnake.ui.ActionRow(*botoes_auto_mod),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações")
            )
        ]
        return embed, components

    def PainelCanal(self) -> list[disnake.ui.Container]:
         colors = db.get_document("custom_colors")
         primary_color_hex = colors.get("primary")
         container_kwargs = {}
         if primary_color_hex:
             primary_color = int(primary_color_hex.replace("#", ""), 16)
             container_kwargs["accent_colour"] = disnake.Colour(primary_color)

         return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sugestões > Configurar Canal"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Selecione abaixo o canal onde as sugestões serão enviadas."),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="Sugestoes_ChannelSelect",
                        placeholder="Selecione o canal de sugestões",
                        channel_types=[disnake.ChannelType.text]
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Sugestoes_VoltarPainel"),
            )
        ]

    def PainelCanalEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Sugestões > Configurar Canal",
            description="Selecione abaixo o canal onde as sugestões serão enviadas.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Sugestoes_ChannelSelect",
                    placeholder="Selecione o canal de sugestões",
                    channel_types=[disnake.ChannelType.text]
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Sugestoes_VoltarPainel")
            )
        ]
        return embed, components

    def PainelCargoImune(self) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Sugestões > Configurar Cargo Imune"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Selecione abaixo o cargo que não poderá criar sugestões."),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        custom_id="Sugestoes_ImmuneRoleSelect",
                        placeholder="Selecione o cargo imune",
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Sugestoes_VoltarPainel"),
            )
        ]

    def PainelCargoImuneEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Sugestões > Configurar Cargo Imune",
            description="Selecione abaixo o cargo que não poderá criar sugestões.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        components = [
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    custom_id="Sugestoes_ImmuneRoleSelect",
                    placeholder="Selecione o cargo imune",
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Sugestoes_VoltarPainel")
            )
        ]
        return embed, components

    async def gerar_msg_sugestao(self, message: disnake.Message, sugestao_id: str) -> Union[list[disnake.ui.Container], tuple[disnake.Embed, list[disnake.ui.ActionRow]]]:
        config = self.db.get_config()
        sugestao = config.get("sugestoes", {}).get(sugestao_id)
        if not sugestao:
            return []
        
        author = await self.bot.fetch_user(sugestao["author_id"]) if sugestao.get("author_id") else None

        if not author:
            class MockUser:
                def __init__(self, user_id):
                    self.id = user_id
                    self.name = f"ID: {self.id}"
                    self.mention = f"<@{self.id}>"
                    class MockAvatar:
                        url = "https://cdn.discordapp.com/embed/avatars/0.png"
                    self.display_avatar = MockAvatar()
            author = MockUser(sugestao.get("author_id", 0))

        upvotes = len(sugestao["upvotes"])
        downvotes = len(sugestao["downvotes"])
        
        status = sugestao.get("status", "aberta")
        is_closed = status in ["aprovada", "reprovada"]

        status_colors = {"aprovada": disnake.ButtonStyle.green, "reprovada": disnake.ButtonStyle.red}
        status_emojis = {"aprovada": emoji.correct, "reprovada": emoji.wrong}
        status_labels = {"aprovada": "Aprovada", "reprovada": "Reprovada"}

        action_row_items = [
            disnake.ui.Button(label=f"{upvotes}", style=disnake.ButtonStyle.green, custom_id=f"sug_upvote_{sugestao_id}", emoji=emoji.like, disabled=is_closed),
            disnake.ui.Button(label=f"{downvotes}", style=disnake.ButtonStyle.red, custom_id=f"sug_downvote_{sugestao_id}", emoji=emoji.deslike, disabled=is_closed),
        ]

        if not is_closed:
            action_row_items.append(
                disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, custom_id=f"sug_moderate_{sugestao_id}", emoji=emoji.ban)
            )
        else: # Aprovada ou Reprovada
            action_row_items.append(
                disnake.ui.Button(label=status_labels[status], style=status_colors[status], emoji=status_emojis[status], custom_id=f"sug_status_{sugestao_id}", disabled=True)
            )
        
        components = [disnake.ui.ActionRow(*action_row_items)]

        mode_val = sugestao.get("message_type", db.get_document("custom_mode").get("mode"))
        mode = mode_val.get("mode") if isinstance(mode_val, dict) else mode_val

        if mode == "embed":
            colors = db.get_document("custom_colors")
            primary_color_hex = colors.get("primary")
            
            # Truncar conteúdo para embed description (limite seguro: 2000 caracteres)
            # Considerando que temos "```\n" no início e "\n```" no final (7 caracteres)
            conteudo_truncado = helpers.truncar_para_embed_description(sugestao['content'])
            
            embed = disnake.Embed(
                description=f"```\n{conteudo_truncado}\n```",
            )
            if primary_color_hex:
                embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            embed.set_thumbnail(url=author.display_avatar.url)
            embed.set_author(name=f"{author.name}")

            if is_closed:
                moderator = await self.bot.fetch_user(sugestao["moderator_id"])
                status_text = "Aprovada" if status == "aprovada" else "Reprovada"
            
            return embed, components
        else:
            # Truncar conteúdo para TextDisplay (limite seguro: 2000 caracteres)
            conteudo_truncado = helpers.truncar_para_mensagem(sugestao['content'])
            
            container_items = [
                disnake.ui.Section(f"### **{author.name}**",
                disnake.ui.TextDisplay(f"```\n{conteudo_truncado}\n```"),
                accessory=disnake.ui.Thumbnail(media=author.display_avatar.url)),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(*action_row_items)
            ]

        if is_closed:
            moderator = await self.bot.fetch_user(sugestao["moderator_id"])
            status_text = "Aprovada" if status == "aprovada" else "Reprovada"

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [disnake.ui.Container(*container_items, **container_kwargs)]


class SuggestionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = helpers.SuggestionsDB()
        self.ui = SuggestionsUI(bot)

    @staticmethod
    def PainelEmbed(bot: commands.Bot, guild: disnake.Guild) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        ui_instance = SuggestionsUI(bot)
        return ui_instance.PainelEmbed(guild)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if cid.startswith("Sugestoes_"):
            if cid == "Sugestoes_EditThreadMessage":
                await inter.response.send_modal(ThreadMessageModal(self))
                return
            if cid == "Sugestoes_AutoModModal":
                await inter.response.send_modal(AutoModerationModal(self))
                return

            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)

            if cid == "Sugestoes_ToggleStatus":
                self.db.set_status(not self.db.get_config().get("status", False))
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed(inter.guild)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel(inter.guild))
            elif cid == "Sugestoes_ToggleCreateThreads":
                self.db.set_create_threads(not self.db.get_config().get("create_threads", True))
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed(inter.guild)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel(inter.guild))
            elif cid == "Sugestoes_ToggleAutoMod":
                config = self.db.get_config()
                auto_mod_config = config.get("auto_moderation", {})
                auto_mod_config["enabled"] = not auto_mod_config.get("enabled", False)
                self.db.set_auto_moderation(auto_mod_config)
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed(inter.guild)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel(inter.guild))
            
            elif cid == "Sugestoes_SetChannel":
                if mode == "embed":
                    embed, components = self.ui.PainelCanalEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.PainelCanal())

            elif cid == "Sugestoes_SetImmuneRole":
                if mode == "embed":
                    embed, components = self.ui.PainelCargoImuneEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.PainelCargoImune())

            elif cid == "Sugestoes_VoltarPainel":
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed(inter.guild)
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel(inter.guild))
        
        elif cid.startswith("sug_"):
            action_part = cid.replace("sug_", "")
            action, sugestao_id = action_part.split("_", 1)

            if action == "moderate":
                if not has_moderation_permission(inter.author):
                    await inter.response.send_message(f"{emoji.wrong} Você não tem permissão para moderar sugestões.", ephemeral=True)
                    return
                
                view = ModerationActionsView(self.bot, self.db, sugestao_id)
                await inter.response.send_message("Escolha uma ação de moderação:", view=view, ephemeral=True)

            elif action in ["upvote", "downvote"]:
                await inter.response.defer()
                self.db.update_vote(sugestao_id, inter.author.id, is_upvote=(action == "upvote"))
                
                sugestao = self.db.get_config().get("sugestoes", {}).get(sugestao_id, {})
                mode_val = sugestao.get("message_type", db.get_document("custom_mode").get("mode"))
                mode = mode_val.get("mode") if isinstance(mode_val, dict) else mode_val
                
                if mode == "embed":
                    embed, components = await self.ui.gerar_msg_sugestao(inter.message, sugestao_id)
                    if not components and not embed:
                         await inter.response.send_message("Sugestão não encontrada.", ephemeral=True)
                         return
                    await inter.edit_original_message(embed=embed, components=components)
                else:
                    components = await self.ui.gerar_msg_sugestao(inter.message, sugestao_id)
                    if not components:
                         await inter.response.send_message("Sugestão não encontrada.", ephemeral=True)
                         return
                    await inter.edit_original_message(components=components)
            
    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id
        if cid in ["Sugestoes_ChannelSelect", "Sugestoes_ImmuneRoleSelect"]:
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)

            if cid == "Sugestoes_ChannelSelect":
                channel_id = int(inter.values[0])
                self.db.set_channel(channel_id)
            elif cid == "Sugestoes_ImmuneRoleSelect":
                role_id = int(inter.values[0])
                self.db.set_immune_role(role_id)

            if mode == "embed":
                embed, components = self.ui.PainelEmbed(inter.guild)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.Painel(inter.guild))

    @commands.Cog.listener("on_message")
    async def on_message(self, message: disnake.Message):
        if not message.guild or message.author.bot:
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

        await message.delete()

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
    bot.add_cog(SuggestionsCog(bot))
