import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from . import helpers

SYSTEM_INSTRUCTION = (
    "Tarefa: Classifique a mensagem do usuário quanto à violação das regras fornecidas.\n"
    "Saída (formato OBRIGATÓRIO): responda EXATAMENTE com um destes tokens: TOS_VIOLATION ou OK. Sem explicações, sem pontuação, sem aspas, sem markdown.\n"
    "Regra de incerteza: se estiver em dúvida ou o caso for borderline, responda OK."
)

DEFAULT_CRITERIA = (
    "Critérios para TOS_VIOLATION (qualquer um): 1) Discurso de ódio, racismo, homofobia, transfobia, xenofobia, discriminação; 2) Assédio, bullying, intimidação, doxxing, stalking; 3) Ameaças de violência, autolesão, suicídio, glorificação da violência; 4) Spam, golpes, phishing, links maliciosos, promoções suspeitas, esquemas financeiros, vendas não autorizadas; 5) Conteúdo sexual explícito, nudez, pornografia, sexualização de menores; 6) Drogas ilegais, armas, atividades criminosas, terrorismo; 7) Desinformação perigosa sobre saúde, política, desastres, conspirações; 8) Incitação à violência, extremismo, radicalização; 9) Violação de direitos autorais, pirataria, conteúdo protegido; 10) Tentativas de contornar moderação, evasão de ban, criação de contas falsas; 11) Comportamento tóxico, linguagem ofensiva excessiva, provocações; 12) Compartilhamento de informações pessoais sem consentimento; 13) Coordenação de ataques ou raids; 14) Conteúdo que promove automutilação ou distúrbios alimentares; 15) Malware, vírus, conteúdo malicioso.\n"
    "Exceções (não considerar violação): denúncias/relatos sem incitação, discussão moderada sobre regras, citações de terceiros, humor leve sem alvo específico, reclamações sem ofensa grave, mensagens fora de contexto sem intenção maliciosa.\n"
    "Atenção: se a mensagem foi editada, analise SOMENTE o conteúdo atual. Não trate o ato de editar como violação.\n"
    "Normalização: considere substituições por números e símbolos que imitam letras (leet). Interprete, por exemplo, 'g0lp3' como 'golpe', 'v!0lênc!a' como 'violência', '@dm!n' como 'admin'. Desconsidere variações de maiúsculas/minúsculas, acentuação e repetição exagerada de caracteres.\n"
    "Idioma: a mensagem pode estar em qualquer idioma."
)

class EditPromptModal(disnake.ui.Modal):
    def __init__(self):
        config = helpers.carregar_config()
        current_prompt = config.get("prompt") or DEFAULT_CRITERIA
        current_rejection_message = config.get("rejection_message") or "violar regras internas."
        
        components = [
            disnake.ui.TextInput(
                label="Critérios de Moderação (Regras)",
                custom_id="tos_prompt",
                value=current_prompt,
                style=disnake.TextInputStyle.paragraph,
                max_length=4000,
                placeholder="Insira aqui as instruções para a IA..."
            ),
            disnake.ui.TextInput(
                label="Mensagem de Remoção (motivo)",
                custom_id="rejection_message",
                value=current_rejection_message,
                style=disnake.TextInputStyle.short,
                max_length=100,
                placeholder="Ex: Sua mensagem foi removida por violar as TOS do Discord."
            ),
        ]
        super().__init__(title="Editar Configurações do Amethys Moderator", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        prompt = inter.text_values.get("tos_prompt")
        rejection_message = inter.text_values.get("rejection_message")
        
        config = helpers.carregar_config()
        config["prompt"] = prompt
        config["rejection_message"] = rejection_message
        helpers.salvar_config(config)
        
        if mode == "embed":
            embed, components = AIModeratorCog.PainelPromptEmbed()
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=AIModeratorCog.PainelPrompt())

class AIModeratorCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def Painel() -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        cargo_imune_id = config.get("cargo_imune_id")
        cargo_imune_txt = f"<@&{int(cargo_imune_id)}>" if cargo_imune_id else "`Não definido`"
        prompt_configurado = config.get("prompt") is not None

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.role} **Cargo imune:** {cargo_imune_txt}\n"
            f"{emoji.sparkles} **Prompt customizado:** `{'Sim' if prompt_configurado else 'Não'}`"
        )

        botoes_principais = [
            disnake.ui.Button(
                label="",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.power,
                custom_id="FiltroTOS_ToggleAtivo"
            ),
            disnake.ui.Button(
                label="Cargo Imune",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.role,
                custom_id="FiltroTOS_AbrirCargoImune",
                disabled=not ativado
            ),
            disnake.ui.Button(
                label="Prompt",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.sparkles,
                custom_id="FiltroTOS_AbrirPrompt",
                disabled=not ativado
            ),
        ]
        
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > **CyM Moderator**
-# Por ser uma IA, ela pode cometer erros, considere isso ao configurar o prompt.
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("""
Exclui automaticamente mensagens que violam o prompt configurado.
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(*botoes_principais),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        cargo_imune_id = config.get("cargo_imune_id")
        cargo_imune_txt = f"<@&{int(cargo_imune_id)}>" if cargo_imune_id else "`Não definido`"
        prompt_configurado = config.get("prompt") is not None

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.role} **Cargo imune:** {cargo_imune_txt}\n"
            f"{emoji.sparkles} **Prompt customizado:** `{'Sim' if prompt_configurado else 'Não'}`"
        )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"CyM Moderator",
            description="Exclui automaticamente mensagens que violam o prompt configurado.\nPor ser uma IA, ela pode cometer erros, considere isso ao configurar o prompt."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        embed.add_field(name="Configurações", value=resumo, inline=False)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.power,
                    custom_id="FiltroTOS_ToggleAtivo"
                ),
                disnake.ui.Button(
                    label="Cargo Imune",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.role,
                    custom_id="FiltroTOS_AbrirCargoImune",
                    disabled=not ativado
                ),
                disnake.ui.Button(
                    label="Prompt",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.sparkles,
                    custom_id="FiltroTOS_AbrirPrompt",
                    disabled=not ativado
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]
        return embed, components

    @staticmethod
    def PainelCargoImune() -> list[disnake.ui.Container]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)
        config = helpers.carregar_config()
        cargo_imune_id = config.get("cargo_imune_id")
        cargo_imune_txt = f"<@&{int(cargo_imune_id)}>" if cargo_imune_id else "`Não definido`"
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > CyM Moderator > **Cargo Imune**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Cargo imune atual: {cargo_imune_txt}"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        placeholder="Selecione o cargo do servidor",
                        custom_id="FiltroTOS_RoleSelectImune",
                        min_values=1,
                        max_values=1,
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="FiltroTOS_Voltar"),
                    disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="FiltroTOS_ClearCargoImune"),
            )
        ]

    @staticmethod
    def PainelCargoImuneEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.carregar_config()
        cargo_imune_id = config.get("cargo_imune_id")
        cargo_imune_txt = f"<@&{int(cargo_imune_id)}>" if cargo_imune_id else "`Não definido`"

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Cargo Imune",
            description=f"Selecione um cargo para não ser afetado pelo moderador.\n\n**Cargo imune atual:** {cargo_imune_txt}"
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        components = [
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Selecione o cargo do servidor",
                    custom_id="FiltroTOS_RoleSelectImune",
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="FiltroTOS_Voltar"),
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="FiltroTOS_ClearCargoImune"),
            )
        ]
        return embed, components

    @staticmethod
    def PainelPrompt() -> list[disnake.ui.Container]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)
        config = helpers.carregar_config()
        prompt = config.get("prompt")
        rejection_message = config.get("rejection_message") or "violar regras internas."

        prompt_display = prompt if prompt else f"O prompt padrão será usado.\nClique em 'Editar' para definir um."
        if len(prompt_display) > 800:
            prompt_display = prompt_display[:797] + "..."
            
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > CyM Moderator > **Prompt**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**Prompt:**\n```\n{prompt_display}```"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**Mensagem de remoção:**\n`{rejection_message}`"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Editar",
                        style=disnake.ButtonStyle.blurple,
                        emoji=emoji.edit,
                        custom_id="FiltroTOS_EditarViaModal"
                    ),
                    disnake.ui.Button(
                        label="Resetar",
                        style=disnake.ButtonStyle.red,
                        emoji=emoji.delete,
                        custom_id="FiltroTOS_ClearPrompt",
                        disabled=not prompt
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="FiltroTOS_Voltar"),
            )
        ]

    @staticmethod
    def PainelPromptEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.carregar_config()
        prompt = config.get("prompt")
        rejection_message = config.get("rejection_message") or "violar regras internas."

        prompt_display = prompt if prompt else "O prompt padrão será usado. Clique em 'Editar' para definir um."
        if len(prompt_display) > 800:
            prompt_display = prompt_display[:797] + "..."

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Configurar Prompt",
            description=f"Edite as regras (prompt) e a mensagem de remoção."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        embed.add_field(name="Prompt Atual", value=f"```\n{prompt_display}```", inline=False)
        embed.add_field(name="Mensagem de Remoção", value=f"`{rejection_message}`", inline=False)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Editar",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="FiltroTOS_EditarViaModal"
                ),
                disnake.ui.Button(
                    label="Resetar",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.delete,
                    custom_id="FiltroTOS_ClearPrompt",
                    disabled=not prompt
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="FiltroTOS_Voltar"),
            )
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def FiltroTOS_Button_Listener(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("FiltroTOS_"):
            return

        custom_id = inter.component.custom_id
        
        # Modals são uma resposta direta, não podem ser adiados.
        if custom_id == "FiltroTOS_EditarViaModal":
            return await inter.response.send_modal(EditPromptModal())

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        
        if custom_id == "FiltroTOS_ToggleAtivo":
            config = helpers.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            helpers.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
        elif custom_id == "FiltroTOS_AbrirCargoImune":
            if mode == "embed":
                embed, components = self.PainelCargoImuneEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelCargoImune())
        elif custom_id == "FiltroTOS_AbrirPrompt":
            if mode == "embed":
                embed, components = self.PainelPromptEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelPrompt())
        elif custom_id == "FiltroTOS_Voltar":
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
        elif custom_id == "FiltroTOS_ClearCargoImune":
            helpers.salvar_config({"cargo_imune_id": None})
            if mode == "embed":
                embed, components = self.PainelCargoImuneEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelCargoImune())
        elif custom_id == "FiltroTOS_ClearPrompt":
            helpers.salvar_config({"prompt": None, "rejection_message": "violar regras internas."})
            if mode == "embed":
                embed, components = self.PainelPromptEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelPrompt())

    @commands.Cog.listener("on_dropdown")
    async def FiltroTOS_Dropdown_Listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id != "FiltroTOS_RoleSelectImune":
            return
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        
        role_id = int(inter.values[0])
        helpers.salvar_config({"cargo_imune_id": role_id})
        
        if mode == "embed":
            embed, components = self.PainelEmbed()
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=self.Painel())

    async def _processar_mensagem_tos(self, message: disnake.Message):
        config = helpers.carregar_config()
        if not config.get("ativado", False):
            return
        
        # Ignora bots e webhooks
        if message.author.bot or message.webhook_id:
            return

        # Verifica cargo imune
        cargo_imune_id = config.get("cargo_imune_id")
        if cargo_imune_id and isinstance(message.author, disnake.Member):
            if any(r.id == cargo_imune_id for r in message.author.roles):
                return
        
        user_criteria = config.get("prompt") or DEFAULT_CRITERIA
        prompt = (
            f"{SYSTEM_INSTRUCTION}\n\n"
            f"Regras a seguir:\n{user_criteria}\n\n"
            f"Mensagem do usuário (entre <<< e >>>):\n<<<\n{message.content}\n>>>\n"
            f"Responda somente com um token válido."
        )
        classification = await helpers.chamar_ia(prompt, "FiltroTOS")
        
        if classification.strip().upper() == "TOS_VIOLATION":
            try:
                await message.delete()

                mode = db.get_document("custom_mode").get("mode")
                rejection_message = config.get("rejection_message") or "violar regras internas."
                full_message = f"{message.author.mention}, {rejection_message}"
                
                if mode == "embed":
                    colors = db.get_document("custom_colors")
                    danger_color = int(colors.get("danger", "#dc3545").replace("#", "0x"), 16)
                    embed = disnake.Embed(
                        description=full_message,
                        color=danger_color
                    )
                    await message.channel.send(embed=embed, delete_after=10)
                else:
                    colors = db.get_document("custom_colors")
                    danger_color_hex = colors.get("danger", "#dc3545")
                    container_kwargs = {}
                    if danger_color_hex:
                        danger_color_int = int(danger_color_hex.replace("#", ""), 16)
                        container_kwargs["accent_colour"] = disnake.Colour(danger_color_int)

                    container = disnake.ui.Container(
                        disnake.ui.TextDisplay(full_message),
                        **container_kwargs
                    )
                    await message.channel.send(components=[container], delete_after=10)

            except disnake.HTTPException as e:
                print(f"Erro ao deletar mensagem TOS ou notificar: {e}")

    @commands.Cog.listener("on_message")
    async def on_tos_message(self, message: disnake.Message):
        await self._processar_mensagem_tos(message)

    @commands.Cog.listener("on_message_edit")
    async def on_tos_message_edit(self, before: disnake.Message, after: disnake.Message):
        if (before.content or "").strip() == (after.content or "").strip():
            return
        await self._processar_mensagem_tos(after)

def setup(bot: commands.Bot):
    bot.add_cog(AIModeratorCog(bot))
