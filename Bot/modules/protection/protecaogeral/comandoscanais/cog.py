import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message

from . import helpers
from . import interactions


class ComandosCanaisCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_advanced_select_descriptions(self, inter: disnake.Interaction, avancado: dict) -> tuple:
        cargos_imunes = avancado.get("cargos_imunes", [])
        cargos_nomes = [r.name for r in [inter.guild.get_role(cid) for cid in cargos_imunes] if r]
        select_cargos = f"Atual: {', '.join(cargos_nomes)}" if cargos_nomes else "Atual: Nenhum"
        if len(select_cargos) > 100:
            select_cargos = select_cargos[:97] + "..."

        canal_logs_id = avancado.get("canal_logs")
        canal = inter.guild.get_channel(canal_logs_id) if canal_logs_id else None
        select_logs = f"Atual: {canal.name}" if canal else "Atual: Nenhum"

        return select_cargos, select_logs

    async def display_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)

        if mode == "embed":
            embed, components = self.PainelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.PainelComponents(inter)
            await inter.edit_original_message(content=None, embed=None, components=components)

    async def display_immune_role_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)

        if mode == "embed":
            embed, components = self.ImmuneRolePanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.ImmuneRolePanelComponents(inter)
            await inter.edit_original_message(content=None, embed=None, components=components)

    async def display_log_channel_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)

        if mode == "embed":
            embed, components = self.LogChannelPanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.LogChannelPanelComponents(inter)
            await inter.edit_original_message(content=None, embed=None, components=components)

    def PainelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get("comandos_canais_avancado", {})

        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title="Proibir Comandos Externos nos Canais",
            color=primary_color
        )

        status_emoji = emoji.on if dados.get("ativado", False) else emoji.off
        embed.description = (
            f"{status_emoji} **Status:** `{'Ativado' if dados.get('ativado') else 'Desativado'}`\n\n"
            "Bloqueia automaticamente a permissão de **Usar Comandos de Aplicativos Externos** "
            "em todos os canais do servidor para `@everyone` e todos os cargos, "
            "verificando a cada 1 minuto."
        )

        select_cargos, select_logs = self._get_advanced_select_descriptions(inter, avancado)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Configurar Proteção",
                    options=[
                        disnake.SelectOption(label="Desativar" if dados.get("ativado") else "Ativar", value="toggle", emoji=emoji.power),
                        disnake.SelectOption(label="Configurar Cargos Imunes", value="cargo_imune", emoji=emoji.role, description=select_cargos),
                        disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=select_logs),
                    ],
                    custom_id="ProtComandosCanaisConfigSelect"
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Geral")
            )
        ]
        return embed, components

    def PainelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get("comandos_canais_avancado", {})
        select_cargos, select_logs = self._get_advanced_select_descriptions(inter, avancado)
        status_emoji = emoji.on if dados.get("ativado", False) else emoji.off

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Proteção > **Proibir Comandos Externos**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{status_emoji} **Status:** `{'Ativado' if dados.get('ativado') else 'Desativado'}`\n\n"
                    "Bloqueia automaticamente a permissão de **Usar Comandos Externos** "
                    "em todos os canais para `@everyone` e todos os cargos, verificando a cada **1 minuto**."
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Configurar Proteção",
                        options=[
                            disnake.SelectOption(label="Desativar" if dados.get("ativado") else "Ativar", value="toggle", emoji=emoji.power),
                            disnake.SelectOption(label="Configurar Cargos Imunes", value="cargo_imune", emoji=emoji.role, description=select_cargos),
                            disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=select_logs),
                        ],
                        custom_id="ProtComandosCanaisConfigSelect"
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Geral")
            )
        ]

    def ImmuneRolePanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get("comandos_canais_avancado", {})
        cargos_imunes = avancado.get("cargos_imunes", [])

        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title="Configurar Cargos Imunes",
            description="Cargos imunes **não** terão a permissão de comandos externos bloqueada.",
            color=primary_color
        )
        cargos_str = ", ".join([f"<@&{cid}>" for cid in cargos_imunes]) if cargos_imunes else "Nenhum"
        embed.add_field(name="Cargos Imunes Atuais", value=cargos_str)

        components = [
            disnake.ui.ActionRow(disnake.ui.RoleSelect(custom_id="ProtComandosCanaisImmuneRoleSelect", max_values=25)),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtComandosCanais_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                  custom_id="ProtComandosCanaisImmuneRoleClear", disabled=not cargos_imunes)
            )
        ]
        return embed, components

    def ImmuneRolePanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        avancado = config.get("comandos_canais_avancado", {})
        cargos_imunes = avancado.get("cargos_imunes", [])
        cargos_str = ", ".join([f"<@&{cid}>" for cid in cargos_imunes]) if cargos_imunes else "Nenhum"

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Proteção > Proibir Comandos Externos > **Cargos Imunes**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Cargos Atuais: {cargos_str}"),
                disnake.ui.ActionRow(disnake.ui.RoleSelect(custom_id="ProtComandosCanaisImmuneRoleSelect", max_values=25)),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtComandosCanais_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                  custom_id="ProtComandosCanaisImmuneRoleClear", disabled=not cargos_imunes)
            )
        ]

    def LogChannelPanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get("comandos_canais_avancado", {})
        canal_logs_id = avancado.get("canal_logs")

        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title="Configurar Canal de Logs",
            description="Selecione o canal para os logs da proteção.",
            color=primary_color
        )
        canal_str = f"<#{canal_logs_id}>" if canal_logs_id else "Nenhum"
        embed.add_field(name="Canal de Logs Atual", value=canal_str)

        components = [
            disnake.ui.ActionRow(disnake.ui.ChannelSelect(
                custom_id="ProtComandosCanaisLogChannelSelect",
                channel_types=[disnake.ChannelType.text]
            )),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtComandosCanais_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                  custom_id="ProtComandosCanaisLogChannelClear", disabled=not canal_logs_id),
                disnake.ui.Button(label="Criar para mim", style=disnake.ButtonStyle.blurple,
                                  emoji=emoji.wand, custom_id="ProtComandosCanaisLogChannelCreate"),
            )
        ]
        return embed, components

    def LogChannelPanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        avancado = config.get("comandos_canais_avancado", {})
        canal_logs_id = avancado.get("canal_logs")
        canal_str = f"<#{canal_logs_id}>" if canal_logs_id else "Nenhum"

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(
                    f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n"
                    f"-# Painel > Proteção > Proibir Comandos Externos > **Logs**"
                ),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Canal Atual: {canal_str}"),
                disnake.ui.ActionRow(disnake.ui.ChannelSelect(
                    custom_id="ProtComandosCanaisLogChannelSelect",
                    channel_types=[disnake.ChannelType.text]
                )),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtComandosCanais_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red,
                                  custom_id="ProtComandosCanaisLogChannelClear", disabled=not canal_logs_id),
                disnake.ui.Button(label="Criar para mim", style=disnake.ButtonStyle.blurple,
                                  emoji=emoji.wand, custom_id="ProtComandosCanaisLogChannelCreate"),
            )
        ]

    @commands.Cog.listener("on_dropdown")
    async def comandos_canais_dropdown_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if "ProtComandosCanais" not in custom_id:
            return

        if custom_id == "ProtComandosCanaisImmuneRoleSelect":
            await interactions.handle_immune_role_select(self, inter)
            return
        if custom_id == "ProtComandosCanaisLogChannelSelect":
            await interactions.handle_log_channel_select(self, inter)
            return

        value = inter.values[0]
        action_map = {
            "toggle": interactions.handle_toggle,
            "cargo_imune": interactions.handle_set_immune_role,
            "canal_logs": interactions.handle_set_log_channel,
        }
        handler = action_map.get(value)
        if handler:
            await handler(self, inter)

    @commands.Cog.listener("on_button_click")
    async def comandos_canais_button_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if "ProtComandosCanais" not in custom_id:
            return

        action_map = {
            "ProtComandosCanais_Back": self.display_panel,
            "ProtComandosCanaisImmuneRoleClear": interactions.handle_immune_role_clear,
            "ProtComandosCanaisLogChannelClear": interactions.handle_log_channel_clear,
            "ProtComandosCanaisLogChannelCreate": interactions.handle_log_channel_create,
        }
        handler = action_map.get(custom_id)
        if handler:
            if custom_id == "ProtComandosCanais_Back":
                await handler(inter)
            else:
                await handler(self, inter)


def setup(bot: commands.Bot):
    bot.add_cog(ComandosCanaisCog(bot))