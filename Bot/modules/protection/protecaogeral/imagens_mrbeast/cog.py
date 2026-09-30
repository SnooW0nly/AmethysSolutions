import disnake
from disnake.ext import commands

from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message

from . import helpers, interactions


def _opcoes_punicao(atual: str) -> list[disnake.SelectOption]:
    opcoes = [
        ("ban",           "Banir",           emoji.ban),
        ("kick",          "Expulsar",        emoji.group),
        ("remover_cargos","Remover Cargos",  emoji.role),
        ("none",          "Nenhuma",         emoji.off),
    ]
    return [
        disnake.SelectOption(label=label, value=value, emoji=emj, default=(value == atual))
        for value, label, emj in opcoes
    ]


def _opcoes_limite(atual: int) -> list[disnake.SelectOption]:
    return [
        disnake.SelectOption(label=f"{n} detecção{'' if n == 1 else 'ões'}", value=str(n), default=(n == atual))
        for n in [1, 2, 3, 5]
    ]


def _opcoes_intervalo(atual: int) -> list[disnake.SelectOption]:
    opcoes = [
        (30,  "30 segundos"),
        (60,  "1 minuto"),
        (120, "2 minutos"),
        (300, "5 minutos"),
    ]
    return [
        disnake.SelectOption(label=label, value=str(valor), default=(valor == atual))
        for valor, label in opcoes
    ]


class ImagensMrBeastCog(commands.Cog):
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

    async def display_cargos_imunes_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)

        if mode == "embed":
            embed, comps = self.CargosImunesEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(content=None, embed=None, components=self.CargosImunesComponents(inter))

    async def display_canal_logs_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)

        if mode == "embed":
            embed, comps = self.CanalLogsEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=comps)
        else:
            await inter.edit_original_message(content=None, embed=None, components=self.CanalLogsComponents(inter))

    # ------------------------------------------------------------------
    # Panel builders — Components mode
    # ------------------------------------------------------------------

    def PainelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get(f"{helpers.CHAVE}_avancado", {})

        ativado   = dados.get("ativado", False)
        punicao   = avancado.get("punicao", "ban")
        limite    = int(avancado.get("limite", 1))
        intervalo = int(avancado.get("intervalo", 60))
        canal_id  = avancado.get("canal_logs")
        n_imunes  = len(avancado.get("cargos_imunes", []))

        status_emoji = emoji.on if ativado else emoji.off
        status_label = "Ativado" if ativado else "Desativado"
        toggle_label = "Desativar proteção" if ativado else "Ativar proteção"

        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        accent = {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))} if hex_color else {}

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Proteção > Proteção Geral > **Proteção MrBeast**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{status_emoji} **Status:** `{status_label}`\n"
                    f"{emoji.ban} **Punição:** `{helpers.formatar_punicao(punicao)}`\n"
                    f"{emoji.chart} **Limite:** `{limite} detecção{'es' if limite > 1 else 'ão'}` em `{intervalo}s`\n"
                    f"{emoji.role} **Cargos imunes:** `{n_imunes} cargo{'s' if n_imunes != 1 else ''}`\n"
                    f"{emoji.textc} **Canal de logs:** {f'<#{canal_id}>' if canal_id else '`Não configurado`'}\n\n"
                    f"-# Detecta e remove imagens de spam MrBeast enviadas por selfbots, comparando via perceptual hash."
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="ProtMrBeast_ActionSelect",
                        placeholder="Selecione uma ação",
                        options=[
                            disnake.SelectOption(
                                label=toggle_label,
                                value="toggle",
                                emoji=status_emoji,
                                description=f"Proteção está {status_label.lower()}",
                            ),
                            disnake.SelectOption(
                                label="Cargos imunes",
                                value="cargos_imunes",
                                emoji=emoji.role,
                                description=f"{n_imunes} cargo(s) configurado(s)",
                            ),
                            disnake.SelectOption(
                                label="Canal de logs",
                                value="canal_logs",
                                emoji=emoji.textc,
                                description="Onde os logs serão enviados",
                            ),
                        ],
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="ProtMrBeast_PunicaoSelect",
                        placeholder=f"Punição — atual: {helpers.formatar_punicao(punicao)}",
                        options=_opcoes_punicao(punicao),
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="ProtMrBeast_LimiteSelect",
                        placeholder=f"Limite — atual: {limite} detecção(ões)",
                        options=_opcoes_limite(limite),
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="ProtMrBeast_IntervaloSelect",
                        placeholder=f"Intervalo — atual: {intervalo}s",
                        options=_opcoes_intervalo(intervalo),
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

    def CargosImunesComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        avancado = config.get(f"{helpers.CHAVE}_avancado", {})
        cargos_imunes = avancado.get("cargos_imunes", [])

        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        accent = {"accent_colour": disnake.Colour(int(hex_color.replace("#", ""), 16))} if hex_color else {}

        mencoes = " ".join(f"<@&{cid}>" for cid in cargos_imunes) if cargos_imunes else "`Nenhum`"

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Proteção > Proteção MrBeast > **Cargos Imunes**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"{emoji.role} **Cargos imunes atuais:** {mencoes}\n\n"
                    f"-# Membros com esses cargos não serão punidos ao enviar imagens detectadas."
                ),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        custom_id="ProtMrBeast_CargosImunesSelect",
                        placeholder="Selecione os cargos imunes",
                        min_values=1,
                        max_values=10,
                    )
                ),
                **accent,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtMrBeast_Back"),
                disnake.ui.Button(label="Limpar todos", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                                  custom_id="ProtMrBeast_CargosImunesClear", disabled=not cargos_imunes),
            ),
        ]

    def CanalLogsComponents(self, inter: disnake.MessageInteraction) -> list:
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
                    f"-# Painel > Proteção > Proteção MrBeast > **Canal de Logs**"
                ),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(
                    f"{emoji.textc} **Canal atual:** {f'<#{canal_id}>' if canal_id else '`Não configurado`'}"
                ),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="ProtMrBeast_CanalLogsSelect",
                        placeholder="Selecione o canal de logs",
                        channel_types=[disnake.ChannelType.text],
                    )
                ),
                **accent,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtMrBeast_Back"),
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                                  custom_id="ProtMrBeast_CanalLogsClear", disabled=canal_id is None),
                disnake.ui.Button(label="Criar para mim", style=disnake.ButtonStyle.blurple, emoji=emoji.wand,
                                  custom_id="ProtMrBeast_CanalLogsCreate"),
            ),
        ]

    # ------------------------------------------------------------------
    # Panel builders — Embed mode
    # ------------------------------------------------------------------

    def PainelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get(f"{helpers.CHAVE}_avancado", {})

        ativado   = dados.get("ativado", False)
        punicao   = avancado.get("punicao", "ban")
        limite    = int(avancado.get("limite", 1))
        intervalo = int(avancado.get("intervalo", 60))
        canal_id  = avancado.get("canal_logs")
        n_imunes  = len(avancado.get("cargos_imunes", []))

        status_emoji = emoji.on if ativado else emoji.off
        status_label = "Ativado" if ativado else "Desativado"
        toggle_label = "Desativar proteção" if ativado else "Ativar proteção"

        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        color = int(hex_color.replace("#", ""), 16) if hex_color else None

        embed = disnake.Embed(title="Proteção MrBeast", color=color)
        embed.description = (
            f"{status_emoji} **Status:** `{status_label}`\n"
            f"{emoji.ban} **Punição:** `{helpers.formatar_punicao(punicao)}`\n"
            f"{emoji.chart} **Limite:** `{limite}` detecção(ões) em `{intervalo}s`\n"
            f"{emoji.role} **Cargos imunes:** `{n_imunes}`\n"
            f"{emoji.textc} **Canal de logs:** {f'<#{canal_id}>' if canal_id else '`Não configurado`'}"
        )

        comps = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="ProtMrBeast_ActionSelect",
                    placeholder="Selecione uma ação",
                    options=[
                        disnake.SelectOption(label=toggle_label, value="toggle", emoji=status_emoji),
                        disnake.SelectOption(label="Cargos imunes", value="cargos_imunes", emoji=emoji.role),
                        disnake.SelectOption(label="Canal de logs", value="canal_logs", emoji=emoji.textc),
                    ],
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="ProtMrBeast_PunicaoSelect",
                    placeholder=f"Punição — atual: {helpers.formatar_punicao(punicao)}",
                    options=_opcoes_punicao(punicao),
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="ProtMrBeast_LimiteSelect",
                    placeholder=f"Limite — atual: {limite} detecção(ões)",
                    options=_opcoes_limite(limite),
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="ProtMrBeast_IntervaloSelect",
                    placeholder=f"Intervalo — atual: {intervalo}s",
                    options=_opcoes_intervalo(intervalo),
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Geral")
            ),
        ]
        return embed, comps

    def CargosImunesEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get(f"{helpers.CHAVE}_avancado", {})
        cargos_imunes = avancado.get("cargos_imunes", [])

        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        color = int(hex_color.replace("#", ""), 16) if hex_color else None

        mencoes = " ".join(f"<@&{cid}>" for cid in cargos_imunes) if cargos_imunes else "Nenhum"

        embed = disnake.Embed(title="Cargos Imunes — Proteção MrBeast", color=color)
        embed.add_field(name="Cargos imunes atuais", value=mencoes)

        comps = [
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    custom_id="ProtMrBeast_CargosImunesSelect",
                    placeholder="Selecione os cargos imunes",
                    min_values=1,
                    max_values=10,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtMrBeast_Back"),
                disnake.ui.Button(label="Limpar todos", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                                  custom_id="ProtMrBeast_CargosImunesClear", disabled=not cargos_imunes),
            ),
        ]
        return embed, comps

    def CanalLogsEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get(f"{helpers.CHAVE}_avancado", {})
        canal_id = avancado.get("canal_logs")

        colors = db.get_document("custom_colors")
        hex_color = colors.get("primary")
        color = int(hex_color.replace("#", ""), 16) if hex_color else None

        embed = disnake.Embed(title="Canal de Logs — Proteção MrBeast", color=color)
        embed.add_field(name="Canal atual", value=f"<#{canal_id}>" if canal_id else "Não configurado")

        comps = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="ProtMrBeast_CanalLogsSelect",
                    channel_types=[disnake.ChannelType.text],
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtMrBeast_Back"),
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.delete,
                                  custom_id="ProtMrBeast_CanalLogsClear", disabled=canal_id is None),
                disnake.ui.Button(label="Criar para mim", style=disnake.ButtonStyle.blurple, emoji=emoji.wand,
                                  custom_id="ProtMrBeast_CanalLogsCreate"),
            ),
        ]
        return embed, comps

    # ------------------------------------------------------------------
    # Listeners
    # ------------------------------------------------------------------

    @commands.Cog.listener("on_dropdown")
    async def mrbeast_dropdown_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if "ProtMrBeast" not in cid:
            return

        if cid == "ProtMrBeast_ActionSelect":
            action_map = {
                "toggle":        interactions.handle_toggle_ativado,
                "cargos_imunes": interactions.handle_nav_cargos_imunes,
                "canal_logs":    interactions.handle_nav_canal_logs,
            }
            handler = action_map.get(inter.values[0])
            if handler:
                await handler(self, inter)
            return

        handler_map = {
            "ProtMrBeast_PunicaoSelect":       interactions.handle_punicao_select,
            "ProtMrBeast_LimiteSelect":         interactions.handle_limite_select,
            "ProtMrBeast_IntervaloSelect":      interactions.handle_intervalo_select,
            "ProtMrBeast_CargosImunesSelect":   interactions.handle_cargos_imunes_select,
            "ProtMrBeast_CanalLogsSelect":      interactions.handle_canal_logs_select,
        }
        handler = handler_map.get(cid)
        if handler:
            await handler(self, inter)

    @commands.Cog.listener("on_button_click")
    async def mrbeast_button_listener(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if "ProtMrBeast" not in cid:
            return

        if cid == "ProtMrBeast_Back":
            await self.display_panel(inter)
            return

        handler_map = {
            "ProtMrBeast_CargosImunesClear": interactions.handle_cargos_imunes_clear,
            "ProtMrBeast_CanalLogsClear":    interactions.handle_canal_logs_clear,
            "ProtMrBeast_CanalLogsCreate":   interactions.handle_canal_logs_create,
        }
        handler = handler_map.get(cid)
        if handler:
            await handler(self, inter)


def setup(bot: commands.Bot):
    bot.add_cog(ImagensMrBeastCog(bot))
