import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from . import helpers

class MensagensModal(disnake.ui.Modal):
    def __init__(self, bot):
        self.bot = bot
        config = helpers.carregar_config()
        
        # Placeholder simplificado devido ao limite de 100 caracteres do Discord
        # Variáveis: {member}, {membername}, {inviter}, {invitername}, {invites}, {entry_mode}
        
        components = [
            disnake.ui.TextInput(
                label="Mensagem de Entrada (Normal)",
                custom_id="mensagem_entrada",
                style=disnake.TextInputStyle.paragraph,
                required=False,
                max_length=2000,
                placeholder="Variáveis: {member}, {membername}, {inviter}, {invitername}, {invites}, {entry_mode}.",
                value=config.get("welcome_message", ""),
            ),
            disnake.ui.TextInput(
                label="Mensagem de Entrada (Vanity URL)",
                custom_id="mensagem_entrada_vanity",
                style=disnake.TextInputStyle.paragraph,
                required=False,
                max_length=2000,
                placeholder="Variáveis: {member}, {membername}, {inviter}, {invitername}, {invites}, {entry_mode}",
                value=config.get("welcome_message_vanity", ""),
            ),
            disnake.ui.TextInput(
                label="Mensagem de Saída",
                custom_id="mensagem_saida",
                style=disnake.TextInputStyle.paragraph,
                required=False,
                max_length=2000,
                placeholder="Variáveis: {member}, {membername}, {inviter}, {invitername}, {invites}, {entry_mode}",
                value=config.get("leave_message", ""),
            ),
        ]
        super().__init__(title="Configurar Mensagens do Invite Tracker", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        await inter.response.defer(with_message=False)
        
        config = helpers.carregar_config()
        # Salvar as mensagens (podem estar vazias para desativar)
        config["welcome_message"] = inter.text_values.get("mensagem_entrada", "").strip()
        config["welcome_message_vanity"] = inter.text_values.get("mensagem_entrada_vanity", "").strip()
        config["leave_message"] = inter.text_values.get("mensagem_saida", "").strip()
        helpers.salvar_config(config)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            embed, components = InviteTrackerCog.PainelEmbed(self.bot)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=InviteTrackerCog.Painel(self.bot))


class InviteTrackerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def Painel(bot: commands.Bot) -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        channel_id = config.get("channel_id")
        
        channel = bot.get_channel(channel_id) if channel_id else "Não definido"

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.message} **Canal:** {channel.mention if isinstance(channel, disnake.TextChannel) else '`Não definido`'}\n"
        )

        botoes = [
            disnake.ui.Button(
                label="",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.power,
                custom_id="InviteTracker_ToggleAtivo"
            ),
            disnake.ui.Button(
                label="Definir Canal",
                style=disnake.ButtonStyle.blurple,
                emoji=emoji.message,
                custom_id="InviteTracker_DefinirCanal",
                disabled=not ativado
            ),
            disnake.ui.Button(
                label="Configurar Mensagens",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.message,
                custom_id="InviteTracker_ConfigurarMensagens",
                disabled=not ativado
            ),
            disnake.ui.Button(
                label="Extensão: Points Tracker",
                style=disnake.ButtonStyle.blurple,
                emoji=emoji.plus,
                custom_id="InviteTracker_PointsTracker",
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
-# Painel > Automações > **Invite Tracker**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(botoes[0], botoes[1]),
                disnake.ui.ActionRow(botoes[2], botoes[3]),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]

    @staticmethod
    def PainelEmbed(bot: commands.Bot) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        channel_id = config.get("channel_id")
        
        channel = bot.get_channel(channel_id) if channel_id else "Não definido"

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.message} **Canal:** {channel.mention if isinstance(channel, disnake.TextChannel) else '`Não definido`'}\n"
        )
        
        if ativado:
            resumo += (
                f"\n**Variáveis disponíveis:**\n"
                f"• `{{member}}` - Menção do membro\n"
                f"• `{{membername}}` - Nome de exibição\n"
                f"• `{{inviter}}` - Menção do convidador\n"
                f"• `{{invitername}}` - Nome do convidador\n"
                f"• `{{invites}}` - Total de convites válidos\n"
                f"• `{{entry_mode}}` - Modo de entrada (Convite ou Vanity Url)"
            )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Invite Tracker",
            description="Monitore os convites do seu servidor e envie mensagens de boas-vindas e saída."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        embed.add_field(name="Configurações", value=resumo, inline=False)

        botoes = [
            disnake.ui.Button(
                label="",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.power,
                custom_id="InviteTracker_ToggleAtivo"
            ),
            disnake.ui.Button(
                label="Definir Canal",
                style=disnake.ButtonStyle.blurple,
                emoji=emoji.message,
                custom_id="InviteTracker_DefinirCanal",
                disabled=not ativado
            ),
            disnake.ui.Button(
                label="Configurar Mensagens",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.message,
                custom_id="InviteTracker_ConfigurarMensagens",
                disabled=not ativado
            ),
            disnake.ui.Button(
                label="Extensão: Points Tracker",
                style=disnake.ButtonStyle.blurple,
                emoji=emoji.plus,
                custom_id="InviteTracker_PointsTracker",
            ),
        ]

        components = [
            disnake.ui.ActionRow(botoes[0], botoes[1]),
            disnake.ui.ActionRow(botoes[2], botoes[3]),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]
        return embed, components

    @staticmethod
    def PainelCanal() -> list[disnake.ui.Container]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > Invite Tracker > **Definir Canal**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("Selecione o canal para enviar as mensagens de entrada e saída."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="InviteTracker_SelectCanal",
                        placeholder="Selecione um canal de texto",
                        channel_types=[disnake.ChannelType.text],
                        min_values=1,
                        max_values=1,
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="InviteTracker_Voltar"),
            )
        ]

    @staticmethod
    def PainelCanalEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Invite Tracker > Definir Canal",
            description="Selecione o canal para enviar as mensagens de entrada e saída."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
            
        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="InviteTracker_SelectCanal",
                    placeholder="Selecione um canal de texto",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="InviteTracker_Voltar"),
            )
        ]
        return embed, components

    # ── Points Tracker ────────────────────────────────────────────────────────

    @staticmethod
    def _pt_container_kwargs():
        primary_color_hex = db.get_document("custom_colors").get("primary")
        if primary_color_hex:
            return {"accent_colour": disnake.Colour(int(primary_color_hex.replace("#", ""), 16))}
        return {}

    @staticmethod
    def PainelPointsTracker(bot: commands.Bot) -> list:
        ck = InviteTrackerCog._pt_container_kwargs()
        pt = helpers.get_points_config()
        it = helpers.carregar_config()
        ativado = pt.get("ativado", False)
        recompensas = pt.get("recompensas", [])
        channel_id = pt.get("channel_id")
        channel = bot.get_channel(channel_id) if channel_id else None
        it_ativo = it.get("ativado", False)

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.message} **Canal do painel:** {channel.mention if isinstance(channel, disnake.TextChannel) else '`Não definido`'}\n"
            f"{emoji.plus} **Recompensas configuradas:** `{len(recompensas)}`\n"
        )
        if not it_ativo:
            resumo += f"\n⚠️ *O Invite Tracker precisa estar ativo para publicar o painel.*"

        editor_data = pt.get("mensagem", {})
        has_msg = bool(editor_data.get("content") or editor_data.get("container") or editor_data.get("embed", {}).get("description"))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Automações > Invite Tracker > **Points Tracker**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="PT_ToggleAtivo"),
                    disnake.ui.Button(label="Definir Canal", style=disnake.ButtonStyle.blurple, emoji=emoji.message, custom_id="PT_DefinirCanal", disabled=not ativado),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Configurar Recompensas", style=disnake.ButtonStyle.grey, emoji=emoji.plus, custom_id="PT_Recompensas", disabled=not ativado),
                    disnake.ui.Button(label="Personalizar Mensagem", style=disnake.ButtonStyle.grey, emoji=emoji.edit, custom_id="PT_PersonalizarMsg", disabled=not ativado),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(
                        label="Publicar Painel",
                        style=disnake.ButtonStyle.green,
                        emoji=emoji.message,
                        custom_id="PT_PublicarPainel",
                        disabled=not (ativado and it_ativo and len(recompensas) > 0 and channel and has_msg),
                    ),
                ),
                **ck,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="InviteTracker_Voltar"),
            )
        ]

    @staticmethod
    def PainelPTCanal() -> list:
        ck = InviteTrackerCog._pt_container_kwargs()
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Points Tracker > **Definir Canal**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("Selecione o canal onde o painel de recompensas será publicado."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="PT_SelectCanal",
                        placeholder="Selecione um canal de texto",
                        channel_types=[disnake.ChannelType.text],
                        min_values=1, max_values=1,
                    )
                ),
                **ck,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PT_Voltar"),
            )
        ]

    @staticmethod
    def PainelPTRecompensas() -> list:
        ck = InviteTrackerCog._pt_container_kwargs()
        pt = helpers.get_points_config()
        recompensas = pt.get("recompensas", [])

        opcoes = [
            disnake.SelectOption(
                label=f"{r['invites']} convites → {r['nome']}",
                value=r["id"],
                description=r.get("descricao", "")[:100] if r.get("descricao") else None,
                emoji=emoji.plus,
            )
            for r in recompensas
        ] or [disnake.SelectOption(label="Nenhuma recompensa configurada", value="none")]

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Points Tracker > **Recompensas**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"Configure as recompensas por quantidade de convites.\n"
                    f"**Total:** `{len(recompensas)}` recompensa(s)."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="PT_SelecionarRecompensa",
                        placeholder="Selecione uma recompensa para editar/remover",
                        options=opcoes,
                        disabled=len(recompensas) == 0,
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Adicionar Recompensa", style=disnake.ButtonStyle.green, emoji=emoji.plus, custom_id="PT_AdicionarRecompensa"),
                    disnake.ui.Button(label="Limpar Todas", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="PT_LimparRecompensas", disabled=len(recompensas) == 0),
                ),
                **ck,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PT_Voltar"),
            )
        ]

    @staticmethod
    def PainelPTEditarRecompensa(recompensa_id: str) -> list:
        ck = InviteTrackerCog._pt_container_kwargs()
        pt = helpers.get_points_config()
        r = next((x for x in pt.get("recompensas", []) if x["id"] == recompensa_id), None)
        if not r:
            return []
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Points Tracker > Recompensas > **{r['nome']}**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"**Nome:** `{r['nome']}`\n"
                    f"**Invites necessários:** `{r['invites']}`\n"
                    f"**Descrição:** {r.get('descricao') or '`Não definida`'}\n"
                    f"**Cargo:** {'<@&' + str(r['cargo_id']) + '>' if r.get('cargo_id') else '`Não definido`'}"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Editar", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id=f"PT_EditarRecomp:{recompensa_id}"),
                    disnake.ui.Button(label="Definir Cargo", style=disnake.ButtonStyle.grey, emoji=emoji.plus, custom_id=f"PT_RecompCargo:{recompensa_id}"),
                    disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id=f"PT_RemoverRecomp:{recompensa_id}"),
                ),
                **ck,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PT_Recompensas"),
            )
        ]

    @staticmethod
    def PainelPTMensagem(bot: commands.Bot) -> list:
        ck = InviteTrackerCog._pt_container_kwargs()
        editor = helpers.get_points_editor_data()
        has_content = bool(editor.get("content"))
        has_embed = bool(editor.get("embed", {}).get("description"))
        has_container = bool(editor.get("container"))
        has_image = bool(editor.get("externalImage"))
        has_any = has_content or has_embed or has_container or has_image
        other_disabled = has_container

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Points Tracker > **Personalizar Mensagem**\n"
                    f"-# Variáveis: `{{member}}`, `{{invites}}`, `{{recompensas_disponiveis}}`"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="PT_ApagarCampo:content", disabled=not has_content or other_disabled),
                    disnake.ui.Button(label="Definir Mensagem", style=disnake.ButtonStyle.grey, emoji=emoji.message, custom_id="PT_DefMsg", disabled=other_disabled),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="PT_ApagarCampo:embed", disabled=not has_embed or other_disabled),
                    disnake.ui.Button(label="Definir Embed", style=disnake.ButtonStyle.grey, emoji=emoji.embed, custom_id="PT_DefEmbed", disabled=other_disabled),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="PT_ApagarCampo:externalImage", disabled=not has_image),
                    disnake.ui.Button(label="Definir Imagem", style=disnake.ButtonStyle.grey, emoji=emoji.image, custom_id="PT_DefImagem"),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="", style=disnake.ButtonStyle.red, emoji=emoji.delete, custom_id="PT_ApagarCampo:container", disabled=not has_container),
                    disnake.ui.Button(label="Definir Container", style=disnake.ButtonStyle.grey, emoji=emoji.commands, custom_id="PT_DefContainer", disabled=(has_content or has_embed) and not has_container),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Visualizar", style=disnake.ButtonStyle.grey, emoji=emoji.search, custom_id="PT_Visualizar", disabled=not has_any),
                ),
                **ck,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="PT_Voltar"),
            )
        ]

    # ── Modais Points Tracker ─────────────────────────────────────────────────

    @staticmethod
    async def _pt_send_modal(inter, modal):
        await inter.response.send_modal(modal)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("InviteTracker_") and not cid.startswith("PT_"):
            return

        # ── Points Tracker handlers ───────────────────────────────────────────
        if cid == "PT_Voltar":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = InviteTrackerCog.PainelEmbed(self.bot)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.response.defer(with_message=False)
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=InviteTrackerCog.Painel(self.bot))
            return

        if cid == "PT_ToggleAtivo":
            await inter.response.defer(with_message=False)
            pt = helpers.get_points_config()
            pt["ativado"] = not pt.get("ativado", False)
            helpers.save_points_config(pt)
            await inter.edit_original_message(components=self.PainelPointsTracker(self.bot))
            return

        if cid == "PT_DefinirCanal":
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelPTCanal())
            return

        if cid == "PT_Recompensas":
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelPTRecompensas())
            return

        if cid == "PT_AdicionarRecompensa":
            await inter.response.send_modal(PTAdicionarRecompensaModal())
            return

        if cid == "PT_LimparRecompensas":
            await inter.response.defer(with_message=False)
            pt = helpers.get_points_config()
            pt["recompensas"] = []
            helpers.save_points_config(pt)
            await inter.edit_original_message(components=self.PainelPTRecompensas())
            return

        if cid.startswith("PT_EditarRecomp:"):
            recompensa_id = cid.split(":", 1)[1]
            await inter.response.send_modal(PTEditarRecompensaModal(recompensa_id))
            return

        if cid.startswith("PT_RecompCargo:"):
            recompensa_id = cid.split(":", 1)[1]
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self._painel_pt_cargo(recompensa_id))
            return

        if cid.startswith("PT_RemoverRecomp:"):
            recompensa_id = cid.split(":", 1)[1]
            await inter.response.defer(with_message=False)
            pt = helpers.get_points_config()
            pt["recompensas"] = [r for r in pt.get("recompensas", []) if r["id"] != recompensa_id]
            helpers.save_points_config(pt)
            await inter.edit_original_message(components=self.PainelPTRecompensas())
            return

        if cid == "PT_PersonalizarMsg":
            await inter.response.defer(with_message=False)
            await inter.edit_original_message(components=self.PainelPTMensagem(self.bot))
            return

        if cid.startswith("PT_ApagarCampo:"):
            campo = cid.split(":", 1)[1]
            await inter.response.defer(with_message=False)
            editor = helpers.get_points_editor_data()
            editor.pop(campo, None)
            if campo == "embed":
                editor.pop("embed", None)
            helpers.set_points_editor_data(editor)
            await inter.edit_original_message(components=self.PainelPTMensagem(self.bot))
            return

        if cid == "PT_DefMsg":
            editor = helpers.get_points_editor_data()
            await inter.response.send_modal(PTDefMsgModal(editor.get("content", "")))
            return

        if cid == "PT_DefEmbed":
            editor = helpers.get_points_editor_data()
            await inter.response.send_modal(PTDefEmbedModal(editor.get("embed", {})))
            return

        if cid == "PT_DefImagem":
            editor = helpers.get_points_editor_data()
            await inter.response.send_modal(PTDefImagemModal(editor.get("externalImage", "")))
            return

        if cid == "PT_DefContainer":
            editor = helpers.get_points_editor_data()
            await inter.response.send_modal(PTDefContainerModal(editor.get("container", "")))
            return

        if cid == "PT_Visualizar":
            await inter.response.defer(with_message=False)
            from commands.admin.anunciar.builder import Builder
            editor = helpers.get_points_editor_data()
            data = editor.copy()
            built = await Builder.build_from_cfg({"message": data})
            from modules.automations.msg_auto.cog import MsgAutoCog
            await MsgAutoCog._send_built_message(inter, built, ephemeral=True)
            return

        if cid == "PT_PublicarPainel":
            await inter.response.defer(with_message=False)
            pt = helpers.get_points_config()
            channel_id = pt.get("channel_id")
            channel = self.bot.get_channel(channel_id) if channel_id else None
            if not channel:
                await inter.followup.send("Canal não encontrado.", ephemeral=True)
                return
            recompensas = pt.get("recompensas", [])
            editor = pt.get("mensagem", {})

            from commands.admin.anunciar.builder import Builder
            from modules.automations.msg_auto.cog import MsgAutoCog

            # Monta mensagem base
            data = editor.copy()
            built = await Builder.build_from_cfg({"message": data})

            # Adiciona select de recompensas + botão dashboard
            opcoes_recomp = [
                disnake.SelectOption(
                    label=f"{r['invites']} convites → {r['nome']}",
                    value=r["id"],
                    description=r.get("descricao", "")[:100] if r.get("descricao") else None,
                )
                for r in recompensas
            ]
            extra_components = [
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="PT_ResgateRecompensa",
                        placeholder="🎁 Resgatar recompensa...",
                        options=opcoes_recomp,
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Meu Dashboard", style=disnake.ButtonStyle.blurple, emoji=emoji.search, custom_id="PT_Dashboard"),
                ),
            ]

            if built["mode"] == "v2":
                built["components"] = (built.get("components") or []) + extra_components
            else:
                built["components"] = (built.get("components") or []) + extra_components

            msg = await MsgAutoCog._send_built_message(channel, built)
            if msg:
                await inter.followup.send(f"{emoji.correct} Painel publicado em {channel.mention}!", ephemeral=True)
            return

        # ── Dashboard do usuário ──────────────────────────────────────────────
        if cid == "PT_Dashboard":
            await inter.response.defer(ephemeral=True)
            guild_id = str(inter.guild.id)
            member_id = str(inter.user.id)
            valid = helpers.get_member_invites_valid(guild_id, member_id)
            convidados = helpers.get_member_invited_list(guild_id, member_id)
            pt = helpers.get_points_config()
            recompensas = pt.get("recompensas", [])
            disponiveis = [r for r in recompensas if valid >= r["invites"]]

            texto = (
                f"**Seus convites válidos:** `{valid}`\n"
                f"**Pessoas que você convidou:** `{len(convidados)}`\n\n"
                f"**Recompensas disponíveis para resgate:** `{len(disponiveis)}`\n"
            )
            for r in disponiveis:
                texto += f"• `{r['invites']}` convites → **{r['nome']}**\n"
            if not disponiveis:
                prox = min((r for r in recompensas if r["invites"] > valid), key=lambda r: r["invites"], default=None)
                if prox:
                    faltam = prox["invites"] - valid
                    texto += f"\n📍 Próxima recompensa: **{prox['nome']}** — faltam `{faltam}` convites."

            ck = InviteTrackerCog._pt_container_kwargs()
            await inter.followup.send(
                components=[disnake.ui.Container(disnake.ui.TextDisplay(f"# 📊 Seu Dashboard\n{texto}"), **ck)],
                flags=disnake.MessageFlags(is_components_v2=True),
                ephemeral=True,
            )
            return

        # ── Resgate de recompensa ─────────────────────────────────────────────
        if cid == "InviteTracker_PointsTracker":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await inter.response.defer(with_message=False)
                await message.wait(inter, send=False)
            await inter.edit_original_message(
                content=None,
                embed=None,
                components=self.PainelPointsTracker(self.bot)
            )
            return

        # ── Invite Tracker handlers originais ────────────────────────────────
        if cid == "InviteTracker_ConfigurarMensagens":
            await inter.response.send_modal(MensagensModal(bot=self.bot))
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await inter.response.defer(with_message=False)
            await message.wait(inter, send=False)

        if cid == "InviteTracker_ToggleAtivo":
            config = helpers.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            helpers.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed(inter.bot)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel(inter.bot))
        elif cid == "InviteTracker_DefinirCanal":
            if mode == "embed":
                embed, components = self.PainelCanalEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelCanal())
        elif cid == "InviteTracker_Voltar":
            if mode == "embed":
                embed, components = self.PainelEmbed(self.bot)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel(self.bot))

    @staticmethod
    def _painel_pt_cargo(recompensa_id: str) -> list:
        ck = InviteTrackerCog._pt_container_kwargs()
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Points Tracker > Recompensas > **Definir Cargo**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay("Selecione o cargo que será concedido ao resgatar esta recompensa."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        custom_id=f"PT_SelectCargo:{recompensa_id}",
                        placeholder="Selecione um cargo",
                        min_values=1, max_values=1,
                    )
                ),
                **ck,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id=f"PT_EditRecompBack:{recompensa_id}"),
            )
        ]

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        if inter.data.custom_id == "InviteTracker_SelectCanal":
            channel_id = int(inter.values[0])
            
            config = helpers.carregar_config()
            config["channel_id"] = channel_id
            helpers.salvar_config(config)
            
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
                embed, components = self.PainelEmbed(inter.bot)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.response.defer(with_message=False)
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.Painel(inter.bot))

        elif inter.data.custom_id == "PT_SelectCanal":
            await inter.response.defer(with_message=False)
            pt = helpers.get_points_config()
            pt["channel_id"] = int(inter.values[0])
            helpers.save_points_config(pt)
            await inter.edit_original_message(components=self.PainelPointsTracker(self.bot))

        elif inter.data.custom_id.startswith("PT_SelectCargo:"):
            await inter.response.defer(with_message=False)
            recompensa_id = inter.data.custom_id.split(":", 1)[1]
            pt = helpers.get_points_config()
            for r in pt.get("recompensas", []):
                if r["id"] == recompensa_id:
                    r["cargo_id"] = int(inter.values[0])
                    break
            helpers.save_points_config(pt)
            await inter.edit_original_message(components=self.PainelPTEditarRecompensa(recompensa_id))

        elif inter.data.custom_id == "PT_SelecionarRecompensa":
            await inter.response.defer(with_message=False)
            recompensa_id = inter.values[0]
            if recompensa_id == "none":
                return
            await inter.edit_original_message(components=self.PainelPTEditarRecompensa(recompensa_id))

        elif inter.data.custom_id == "PT_ResgateRecompensa":
            await inter.response.defer(ephemeral=True)
            recompensa_id = inter.values[0]
            guild_id = str(inter.guild.id)
            member_id = str(inter.user.id)
            valid = helpers.get_member_invites_valid(guild_id, member_id)
            pt = helpers.get_points_config()
            r = next((x for x in pt.get("recompensas", []) if x["id"] == recompensa_id), None)
            if not r:
                await inter.followup.send("Recompensa não encontrada.", ephemeral=True)
                return
            if valid < r["invites"]:
                await inter.followup.send(
                    f"{emoji.wrong} Você precisa de `{r['invites']}` convites válidos para resgatar **{r['nome']}**. "
                    f"Você tem `{valid}`.", ephemeral=True
                )
                return
            cargo_id = r.get("cargo_id")
            if cargo_id:
                role = inter.guild.get_role(int(cargo_id))
                if role and role not in inter.user.roles:
                    try:
                        await inter.user.add_roles(role, reason=f"Points Tracker: resgate de {r['nome']}")
                        await inter.followup.send(f"🎉 Você resgatou **{r['nome']}** e recebeu o cargo {role.mention}!", ephemeral=True)
                        return
                    except disnake.Forbidden:
                        await inter.followup.send(f"{emoji.correct} Resgate de **{r['nome']}** registrado, mas não consegui adicionar o cargo (sem permissão).", ephemeral=True)
                        return
                elif role and role in inter.user.roles:
                    await inter.followup.send(f"ℹ️ Você já possui o cargo {role.mention} desta recompensa.", ephemeral=True)
                    return
            await inter.followup.send(f"🎉 Você resgatou **{r['nome']}**!", ephemeral=True)

        elif inter.data.custom_id.startswith("PT_EditRecompBack:"):
            await inter.response.defer(with_message=False)
            recompensa_id = inter.data.custom_id.split(":", 1)[1]
            await inter.edit_original_message(components=self.PainelPTEditarRecompensa(recompensa_id))

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit_pt(self, inter: disnake.ModalInteraction):
        cid = inter.custom_id
        if not cid.startswith("PT_"):
            return

        if cid == "PT_AdicionarRecompensaModal":
            try:
                nome = inter.text_values.get("nome", "").strip()
                invites = int(inter.text_values.get("invites", "0").strip())
                descricao = inter.text_values.get("descricao", "").strip() or None
                if not nome or invites < 1:
                    raise ValueError
            except ValueError:
                await inter.response.defer(with_message=False)
                await inter.edit_original_message(components=self.PainelPTRecompensas())
                await inter.followup.send(f"{emoji.wrong} Dados inválidos. O nome não pode ser vazio e os invites devem ser ≥ 1.", ephemeral=True)
                return
            import uuid
            pt = helpers.get_points_config()
            pt.setdefault("recompensas", []).append({
                "id": str(uuid.uuid4()),
                "nome": nome,
                "invites": invites,
                "descricao": descricao,
                "cargo_id": None,
            })
            pt["recompensas"].sort(key=lambda r: r["invites"])
            helpers.save_points_config(pt)
            await inter.response.edit_message(components=self.PainelPTRecompensas())
            return

        if cid.startswith("PT_EditarRecompensaModal:"):
            recompensa_id = cid.split(":", 1)[1]
            try:
                nome = inter.text_values.get("nome", "").strip()
                invites = int(inter.text_values.get("invites", "0").strip())
                descricao = inter.text_values.get("descricao", "").strip() or None
                if not nome or invites < 1:
                    raise ValueError
            except ValueError:
                await inter.response.defer(with_message=False)
                await inter.edit_original_message(components=self.PainelPTEditarRecompensa(recompensa_id))
                await inter.followup.send(f"{emoji.wrong} Dados inválidos.", ephemeral=True)
                return
            pt = helpers.get_points_config()
            for r in pt.get("recompensas", []):
                if r["id"] == recompensa_id:
                    r["nome"] = nome
                    r["invites"] = invites
                    r["descricao"] = descricao
                    break
            pt["recompensas"].sort(key=lambda r: r["invites"])
            helpers.save_points_config(pt)
            await inter.response.edit_message(components=self.PainelPTEditarRecompensa(recompensa_id))
            return

        if cid == "PT_DefMsgModal":
            editor = helpers.get_points_editor_data()
            editor["content"] = inter.text_values.get("content", "").strip() or None
            editor.pop("container", None)
            helpers.set_points_editor_data(editor)
            await inter.response.edit_message(components=self.PainelPTMensagem(self.bot))
            return

        if cid == "PT_DefEmbedModal":
            editor = helpers.get_points_editor_data()
            editor["embed"] = {
                "title": inter.text_values.get("title", "").strip() or None,
                "description": inter.text_values.get("description", "").strip() or None,
                "color": inter.text_values.get("color", "").strip() or None,
                "footer": inter.text_values.get("footer", "").strip() or None,
            }
            editor.pop("container", None)
            helpers.set_points_editor_data(editor)
            await inter.response.edit_message(components=self.PainelPTMensagem(self.bot))
            return

        if cid == "PT_DefImagemModal":
            editor = helpers.get_points_editor_data()
            editor["externalImage"] = inter.text_values.get("url", "").strip() or None
            helpers.set_points_editor_data(editor)
            await inter.response.edit_message(components=self.PainelPTMensagem(self.bot))
            return

        if cid == "PT_DefContainerModal":
            editor = helpers.get_points_editor_data()
            editor["container"] = inter.text_values.get("container", "").strip() or None
            editor.pop("content", None)
            editor.pop("embed", None)
            helpers.set_points_editor_data(editor)
            await inter.response.edit_message(components=self.PainelPTMensagem(self.bot))
            return


# ── Modais Points Tracker (fora da classe para simplicidade) ──────────────────

class PTAdicionarRecompensaModal(disnake.ui.Modal):
    def __init__(self):
        super().__init__(
            title="Adicionar Recompensa",
            custom_id="PT_AdicionarRecompensaModal",
            components=[
                disnake.ui.TextInput(label="Nome da recompensa", custom_id="nome", required=True, max_length=50),
                disnake.ui.TextInput(label="Invites necessários", custom_id="invites", required=True, max_length=5, placeholder="Ex: 10"),
                disnake.ui.TextInput(label="Descrição (opcional)", custom_id="descricao", required=False, max_length=100, style=disnake.TextInputStyle.short),
            ]
        )


class PTEditarRecompensaModal(disnake.ui.Modal):
    def __init__(self, recompensa_id: str):
        pt = helpers.get_points_config()
        r = next((x for x in pt.get("recompensas", []) if x["id"] == recompensa_id), {})
        super().__init__(
            title="Editar Recompensa",
            custom_id=f"PT_EditarRecompensaModal:{recompensa_id}",
            components=[
                disnake.ui.TextInput(label="Nome", custom_id="nome", required=True, max_length=50, value=r.get("nome", "")),
                disnake.ui.TextInput(label="Invites necessários", custom_id="invites", required=True, max_length=5, value=str(r.get("invites", ""))),
                disnake.ui.TextInput(label="Descrição (opcional)", custom_id="descricao", required=False, max_length=100, value=r.get("descricao", "") or ""),
            ]
        )


class PTDefMsgModal(disnake.ui.Modal):
    def __init__(self, current: str = ""):
        super().__init__(
            title="Definir Mensagem do Painel",
            custom_id="PT_DefMsgModal",
            components=[
                disnake.ui.TextInput(
                    label="Mensagem",
                    custom_id="content",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    max_length=2000,
                    value=current,
                    placeholder="Variáveis: {member}, {invites}, {recompensas_disponiveis}",
                )
            ]
        )


class PTDefEmbedModal(disnake.ui.Modal):
    def __init__(self, embed: dict = None):
        embed = embed or {}
        super().__init__(
            title="Definir Embed do Painel",
            custom_id="PT_DefEmbedModal",
            components=[
                disnake.ui.TextInput(label="Título", custom_id="title", required=False, max_length=256, value=embed.get("title", "") or ""),
                disnake.ui.TextInput(label="Descrição", custom_id="description", required=True, max_length=4000, style=disnake.TextInputStyle.paragraph, value=embed.get("description", "") or "", placeholder="Variáveis: {member}, {invites}, {recompensas_disponiveis}"),
                disnake.ui.TextInput(label="Cor (Hex)", custom_id="color", required=False, max_length=7, placeholder="#FFFFFF", value=embed.get("color", "") or ""),
                disnake.ui.TextInput(label="Footer", custom_id="footer", required=False, max_length=256, value=embed.get("footer", "") or ""),
            ]
        )


class PTDefImagemModal(disnake.ui.Modal):
    def __init__(self, current: str = ""):
        super().__init__(
            title="Definir Imagem Externa",
            custom_id="PT_DefImagemModal",
            components=[
                disnake.ui.TextInput(label="URL da imagem", custom_id="url", required=False, max_length=500, value=current or "")
            ]
        )


class PTDefContainerModal(disnake.ui.Modal):
    def __init__(self, current: str = ""):
        super().__init__(
            title="Definir Container do Painel",
            custom_id="PT_DefContainerModal",
            components=[
                disnake.ui.TextInput(
                    label="Conteúdo do container",
                    custom_id="container",
                    style=disnake.TextInputStyle.paragraph,
                    required=True,
                    max_length=4000,
                    value=current or "",
                    placeholder="Use {{separator}}, {{color:#...}}, {{image url=...}}",
                )
            ]
        )




    # Removido: cache_invites - não é mais necessário pois o tsk_invite_tracker.py gerencia o cache
    
    # Removido: on_member_join duplicado
    # O listener de entrada está implementado em tasks/automations/tsk_invite_tracker.py
    # que também gerencia as estatísticas de convites e é mais preciso

    # Removido: on_member_remove duplicado
    # O listener de saída está implementado em tasks/automations/tsk_invite_tracker.py
    # que também gerencia as estatísticas de convites

def setup(bot: commands.Bot):
    bot.add_cog(InviteTrackerCog(bot))
