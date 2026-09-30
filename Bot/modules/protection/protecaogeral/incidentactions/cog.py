import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message

from . import helpers, interactions


def _duracoes_options(chave_atual: str, prefixo: str) -> list[disnake.SelectOption]:
    """Gera as opções de duração para o select."""
    opcoes_visiveis = [
        ("15m",  "15 minutos"),
        ("30m",  "30 minutos"),
        ("1h",   "1 hora"),
        ("3h",   "3 horas"),
        ("6h",   "6 horas"),
        ("12h",  "12 horas"),
        ("1d",   "24 horas (máx. Discord)"),
    ]
    return [
        disnake.SelectOption(
            label=label,
            value=value,
            default=(value == chave_atual),
            description="Duração máxima permitida pelo Discord" if value == "1d" else None,
        )
        for value, label in opcoes_visiveis
    ]


class IncidentActionsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    async def display_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)

        if mode == "embed":
            embed, comps = self.PainelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(content=None, embed=None, components=self.PainelComponents(inter))

    async def display_log_channel_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)

        if mode == "embed":
            embed, comps = self.LogChannelPanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(content=None, embed=None, components=self.LogChannelPanelComponents(inter))

    # ------------------------------------------------------------------
    # Panel builders — Components mode
    # ------------------------------------------------------------------

    def PainelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})

        dms_ativo      = dados.get("dms_ativado", False)
        invites_ativo  = dados.get("invites_ativado", False)
        dur_dms        = dados.get("duracao_dms", "1h")
        dur_invites    = dados.get("duracao_invites", "1h")

        dms_emoji     = emoji.on  if dms_ativo    else emoji.off
        inv_emoji     = emoji.on  if invites_ativo else emoji.off
        dms_label     = "Desativar DMs bloqueadas"   if dms_ativo    else "Ativar DMs bloqueadas"
        inv_label     = "Desativar Invites bloqueados" if invites_ativo else "Ativar Invites bloqueados"

        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        accent = {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))} if hex_color else {}

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Proteção > Proteção Geral > **Incident Actions**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{dms_emoji} **DMs bloqueadas:** `{'Ativo' if dms_ativo else 'Inativo'}`  "
                    f"— Duração: `{helpers.formatar_duracao(dur_dms)}`\n"
                    f"{inv_emoji} **Invites bloqueados:** `{'Ativo' if invites_ativo else 'Inativo'}`  "
                    f"— Duração: `{helpers.formatar_duracao(dur_invites)}`\n\n"
                    f"-# As ações são aplicadas imediatamente via API do Discord e duram o tempo configurado."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),

                # Linha 1 — toggle DMs
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="ProtIncident_ActionSelect",
                        placeholder="Gerenciar DMs e Invites",
                        options=[
                            disnake.SelectOption(
                                label=dms_label,
                                value="toggle_dms",
                                emoji=dms_emoji,
                                description=f"Duração configurada: {helpers.formatar_duracao(dur_dms)}",
                            ),
                            disnake.SelectOption(
                                label=inv_label,
                                value="toggle_invites",
                                emoji=inv_emoji,
                                description=f"Duração configurada: {helpers.formatar_duracao(dur_invites)}",
                            ),
                            disnake.SelectOption(
                                label="Configurar Canal de Logs",
                                value="canal_logs",
                                emoji=emoji.textc,
                                description="Escolha onde os logs serão enviados",
                            ),
                        ],
                    )
                ),

                # Linha 2 — duração DMs
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="ProtIncident_DuracaoDmsSelect",
                        placeholder=f"⏱️  Duração do bloqueio de DMs — atual: {helpers.formatar_duracao(dur_dms)}",
                        options=_duracoes_options(dur_dms, "dms"),
                    )
                ),

                # Linha 3 — duração Invites
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="ProtIncident_DuracaoInvitesSelect",
                        placeholder=f"⏱️  Duração do bloqueio de Invites — atual: {helpers.formatar_duracao(dur_invites)}",
                        options=_duracoes_options(dur_invites, "invites"),
                    )
                ),

                **accent,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label="Voltar",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.back,
                    custom_id="Protecao_Geral",
                )
            ),
        ]

    def LogChannelPanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        avancado = config.get(f"{helpers.CHAVE}_avancado", {})
        canal_id = avancado.get("canal_logs")

        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        accent = {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))} if hex_color else {}

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Proteção > Incident Actions > **Canal de Logs**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"**Canal atual:** {f'<#{canal_id}>' if canal_id else 'Nenhum'}"
                ),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="ProtIncident_LogChannelSelect",
                        placeholder="Selecione o canal de logs",
                        channel_types=[disnake.ChannelType.text],
                    )
                ),
                **accent,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtIncident_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                  custom_id="ProtIncident_LogChannelClear", disabled=canal_id is None),
                disnake.ui.Button(label="Criar para mim", emoji=emoji.wand, style=disnake.ButtonStyle.blurple,
                                  custom_id="ProtIncident_LogChannelCreate"),
            ),
        ]

    # ------------------------------------------------------------------
    # Panel builders — Embed mode
    # ------------------------------------------------------------------

    def PainelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})

        dms_ativo     = dados.get("dms_ativado", False)
        invites_ativo = dados.get("invites_ativado", False)
        dur_dms       = dados.get("duracao_dms", "1h")
        dur_invites   = dados.get("duracao_invites", "1h")

        dms_emoji    = emoji.on  if dms_ativo    else emoji.off
        inv_emoji    = emoji.on  if invites_ativo else emoji.off
        dms_label    = "Desativar DMs bloqueadas"    if dms_ativo    else "Ativar DMs bloqueadas"
        inv_label    = "Desativar Invites bloqueados" if invites_ativo else "Ativar Invites bloqueados"

        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        color = int(hex_color.replace("#", ""), 16) if hex_color else None

        embed = disnake.Embed(title="Incident Actions", color=color)
        embed.description = (
            f"{dms_emoji} **DMs bloqueadas:** `{'Ativo' if dms_ativo else 'Inativo'}` "
            f"— `{helpers.formatar_duracao(dur_dms)}`\n"
            f"{inv_emoji} **Invites bloqueados:** `{'Ativo' if invites_ativo else 'Inativo'}` "
            f"— `{helpers.formatar_duracao(dur_invites)}`"
        )

        comps = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="ProtIncident_ActionSelect",
                    placeholder="Gerenciar DMs e Invites",
                    options=[
                        disnake.SelectOption(label=dms_label,   value="toggle_dms",    emoji=dms_emoji,
                                             description=f"Duração: {helpers.formatar_duracao(dur_dms)}"),
                        disnake.SelectOption(label=inv_label,   value="toggle_invites", emoji=inv_emoji,
                                             description=f"Duração: {helpers.formatar_duracao(dur_invites)}"),
                        disnake.SelectOption(label="Canal de Logs", value="canal_logs", emoji=emoji.textc),
                    ],
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="ProtIncident_DuracaoDmsSelect",
                    placeholder=f"Duração DMs — atual: {helpers.formatar_duracao(dur_dms)}",
                    options=_duracoes_options(dur_dms, "dms"),
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="ProtIncident_DuracaoInvitesSelect",
                    placeholder=f"Duração Invites — atual: {helpers.formatar_duracao(dur_invites)}",
                    options=_duracoes_options(dur_invites, "invites"),
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Geral")
            ),
        ]
        return embed, comps

    def LogChannelPanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get(f"{helpers.CHAVE}_avancado", {})
        canal_id = avancado.get("canal_logs")

        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        color = int(hex_color.replace("#", ""), 16) if hex_color else None

        embed = disnake.Embed(title="Canal de Logs — Incident Actions", color=color)
        embed.add_field(name="Canal atual", value=f"<#{canal_id}>" if canal_id else "Nenhum")

        comps = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(custom_id="ProtIncident_LogChannelSelect",
                                         channel_types=[disnake.ChannelType.text])
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtIncident_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                  custom_id="ProtIncident_LogChannelClear", disabled=canal_id is None),
                disnake.ui.Button(label="Criar para mim", emoji=emoji.wand, style=disnake.ButtonStyle.blurple,
                                  custom_id="ProtIncident_LogChannelCreate"),
            ),
        ]
        return embed, comps

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    @commands.Cog.listener("on_dropdown")
    async def incident_dropdown_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if "ProtIncident" not in cid:
            return

        if cid == "ProtIncident_DuracaoDmsSelect":
            await interactions.handle_duracao_dms_select(self, inter)
            return

        if cid == "ProtIncident_DuracaoInvitesSelect":
            await interactions.handle_duracao_invites_select(self, inter)
            return

        if cid == "ProtIncident_LogChannelSelect":
            await interactions.handle_log_channel_select(self, inter)
            return

        if cid == "ProtIncident_ActionSelect":
            value = inter.values[0]
            action_map = {
                "toggle_dms":    interactions.handle_toggle_dms,
                "toggle_invites": interactions.handle_toggle_invites,
                "canal_logs":    interactions.handle_set_log_channel_nav,
            }
            handler = action_map.get(value)
            if handler:
                await handler(self, inter)

    @commands.Cog.listener("on_button_click")
    async def incident_button_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if "ProtIncident" not in cid:
            return

        action_map = {
            "ProtIncident_Back":             self.display_panel,
            "ProtIncident_LogChannelClear":  interactions.handle_log_channel_clear,
            "ProtIncident_LogChannelCreate": interactions.handle_log_channel_create,
        }
        handler = action_map.get(cid)
        if handler:
            if cid == "ProtIncident_Back":
                await handler(inter)
            else:
                await handler(self, inter)


def setup(bot: commands.Bot):
    bot.add_cog(IncidentActionsCog(bot))