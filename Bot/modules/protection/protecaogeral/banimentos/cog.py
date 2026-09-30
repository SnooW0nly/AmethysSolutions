import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message

from . import helpers
from . import interactions

class BanimentosCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_advanced_select_descriptions(self, inter: disnake.Interaction, avancado: dict) -> tuple:
        punicao_atual = avancado.get("punicao", "ban")
        desc_punicao = f"Atual: {helpers.formatar_punicao(punicao_atual)}"

        cargos_imunes = avancado.get("cargos_imunes", [])
        cargos_nomes = [r.name for r in [inter.guild.get_role(cid) for cid in cargos_imunes] if r]
        select_cargos = f"Atual: {', '.join(cargos_nomes)}" if cargos_nomes else "Atual: Nenhum"
        if len(select_cargos) > 100:
            select_cargos = select_cargos[:97] + "..."

        canal_logs_id = avancado.get("canal_logs")
        canal = inter.guild.get_channel(canal_logs_id) if canal_logs_id else None
        select_logs = f"Atual: {canal.name}" if canal else "Atual: Nenhum"
        
        return desc_punicao, select_cargos, select_logs

    @staticmethod
    def _get_punishment_options(punicao_atual: str) -> list[disnake.SelectOption]:
        return [
            disnake.SelectOption(label="Banimento", value="ban", default=punicao_atual == 'ban', description="Bane o membro que exceder o limite."),
            disnake.SelectOption(label="Expulsão", value="kick", default=punicao_atual == 'kick', description="Expulsa o membro que exceder o limite."),
            disnake.SelectOption(label="Castigo de 30 dias", value="timeout_30d", default=punicao_atual == 'timeout_30d', description="Aplica um castigo de 30 dias ao membro."),
            disnake.SelectOption(label="Remoção dos Cargos", value="remove_roles", default=punicao_atual == 'remove_roles', description="Remove todos os cargos do membro."),
            disnake.SelectOption(label="Reversão da Ação", value="revert_action", default=punicao_atual == 'revert_action', description="Desbane os membros banidos pelo infrator."),
            disnake.SelectOption(label="Nenhuma", value="none", default=punicao_atual == 'none', description="Nenhuma ação será tomada (Apenas logs)."),
        ]

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

    async def display_punishment_panel(self, inter: disnake.MessageInteraction):
        # Como este é um sub-painel, vamos assumir que ele usa o mesmo modo do painel principal.
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        if mode == "embed":
            embed, components = self.PunishmentPanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.PunishmentPanelComponents(inter)
            await inter.edit_original_message(
                content=None,
                embed=None,
                components=components
            )

    async def display_immune_role_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        if mode == "embed":
            embed, components = self.ImmuneRolePanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.ImmuneRolePanelComponents(inter)
            await inter.edit_original_message(
                content=None,
                embed=None,
                components=components
            )

    async def display_log_channel_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        if mode == "embed":
            embed, components = self.LogChannelPanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.LogChannelPanelComponents(inter)
            await inter.edit_original_message(
                content=None,
                embed=None,
                components=components
            )

    def PunishmentPanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get("banimentos_avancado", {})
        punicao_atual = avancado.get("punicao", "ban")

        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title=f"Configurar Punição",
            description="Escolha a punição a ser aplicada quando o limite de banimentos for atingido.",
            color=primary_color
        )

        options = self._get_punishment_options(punicao_atual)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Selecione uma punição",
                    options=options,
                    custom_id="ProtBanimentosPunishmentSelect"
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtBanimentos_Back"),
            )
        ]
        return embed, components

    def PunishmentPanelComponents(self, inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        avancado = config.get("banimentos_avancado", {})
        punicao_atual = avancado.get("punicao", "ban")

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        options = self._get_punishment_options(punicao_atual)
        
        punicao_str = helpers.formatar_punicao(punicao_atual)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Proteção Geral > Banimentos > **Configurar Punição**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Aplique a punição para o infrator do limite."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Selecione uma punição",
                        options=options,
                        custom_id="ProtBanimentosPunishmentSelect"
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtBanimentos_Back"),
            )
        ]

    def ImmuneRolePanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get("banimentos_avancado", {})
        cargos_imunes = avancado.get("cargos_imunes", [])

        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title=f"Configurar Cargos Imunes",
            description="Selecione os cargos que serão imunes à proteção de banimentos.",
            color=primary_color
        )

        cargos_str = ", ".join([f'<@&{cid}>' for cid in cargos_imunes]) if cargos_imunes else "Nenhum"
        embed.add_field(name="Cargos Imunes Atuais", value=cargos_str, inline=False)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    placeholder="Selecione os cargos imunes",
                    custom_id="ProtBanimentosImmuneRoleSelect",
                    min_values=1,
                    max_values=25
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtBanimentos_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtBanimentosImmuneRoleClear", style=disnake.ButtonStyle.red, disabled=not cargos_imunes)
            )
        ]
        return embed, components

    def ImmuneRolePanelComponents(self, inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        avancado = config.get("banimentos_avancado", {})
        cargos_imunes = avancado.get("cargos_imunes", [])

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        cargos_str = ", ".join([f'<@&{cid}>' for cid in cargos_imunes]) if cargos_imunes else "Nenhum"

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Proteção Geral > Banimentos > **Cargos Imunes**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Selecione os cargos que serão imunes à proteção."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**Cargos Imunes Atuais:** {cargos_str}"),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        placeholder="Selecione os cargos imunes",
                        custom_id="ProtBanimentosImmuneRoleSelect",
                        min_values=0,
                        max_values=25
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtBanimentos_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtBanimentosImmuneRoleClear", style=disnake.ButtonStyle.red, disabled=not cargos_imunes)
            )
        ]

    def LogChannelPanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get("banimentos_avancado", {})
        canal_logs_id = avancado.get("canal_logs")

        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title=f"Configurar Canal de Logs",
            description="Selecione o canal para onde os logs de proteção de banimentos serão enviados.",
            color=primary_color
        )

        canal_str = f"<#{canal_logs_id}>" if canal_logs_id else "Nenhum"
        embed.add_field(name="Canal de Logs Atual", value=canal_str, inline=False)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    placeholder="Selecione o canal de logs",
                    custom_id="ProtBanimentosLogChannelSelect",
                    min_values=1,
                    max_values=1,
                    channel_types=[disnake.ChannelType.text],
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtBanimentos_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtBanimentosLogChannelClear", style=disnake.ButtonStyle.red, disabled=canal_logs_id is None),
                disnake.ui.Button(label="Criar para mim", emoji=emoji.wand, custom_id="ProtBanimentosLogChannelCreate", style=disnake.ButtonStyle.blurple),
            )
        ]
        return embed, components

    def LogChannelPanelComponents(self, inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        avancado = config.get("banimentos_avancado", {})
        canal_logs_id = avancado.get("canal_logs")

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        canal_str = f"<#{canal_logs_id}>" if canal_logs_id else "Nenhum"

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Proteção Geral > Banimentos > **Canal de Logs**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Selecione o canal para onde os logs da proteção serão enviados."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**Canal de Logs Atual:** {canal_str}"),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        placeholder="Selecione o canal de logs",
                        custom_id="ProtBanimentosLogChannelSelect",
                        min_values=1,
                        max_values=1,
                        channel_types=[disnake.ChannelType.text],
                    )
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="ProtBanimentos_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtBanimentosLogChannelClear", style=disnake.ButtonStyle.red, disabled=canal_logs_id is None),
                disnake.ui.Button(label="Criar para mim", emoji=emoji.wand, custom_id="ProtBanimentosLogChannelCreate", style=disnake.ButtonStyle.blurple),
            )
        ]

    def PainelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get("banimentos_avancado", {})

        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title=f"Proteção de Banimentos",
            description="Gerencie as configurações de proteção contra banimentos em massa.",
            color=primary_color
        )
        
        status_texto = '`Ativado`' if dados.get('ativado', False) else '`Desativado`'
        status_emoji = emoji.on if dados.get('ativado', False) else emoji.off
        embed.add_field(name="Status", value=f"{status_emoji} {status_texto}", inline=True)
        embed.add_field(name="Limite", value=f"{emoji.chart} `{dados.get('limite', 0)}`", inline=True)
        embed.add_field(name="Intervalo", value=f"{emoji.clock} `{dados.get('intervalo', 0)}s`", inline=True)
        
        desc_punicao, select_cargos, select_logs = self._get_advanced_select_descriptions(inter, avancado)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Configurar Proteção",
                    options=[
                        disnake.SelectOption(label="Desativar" if dados.get('ativado') else "Ativar", value="toggle", emoji=emoji.power),
                        disnake.SelectOption(label="Definir Limite", value="limite", emoji=emoji.chart, description=f"Limite de ações por intervalo"),
                        disnake.SelectOption(label="Definir Intervalo", value="intervalo", emoji=emoji.clock, description=f"Intervalo de tempo para a punição"),
                    ],
                    custom_id="ProtBanimentosConfigSelect"
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Configurações Avançadas",
                    options=[
                        disnake.SelectOption(label="Configurar Punição", value="punicao", emoji=emoji.ban, description=desc_punicao),
                        disnake.SelectOption(label="Configurar Cargos Imunes", value="cargo_imune", emoji=emoji.role, description=select_cargos),
                        disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=select_logs),
                    ],
                    custom_id="ProtBanimentosConfigSelectAvancado"
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Geral"),
            )
        ]
        
        return embed, components

    def PainelComponents(self, inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get("banimentos_avancado", {})

        desc_punicao, select_cargos, select_logs = self._get_advanced_select_descriptions(inter, avancado)

        status_texto = "`Ativado`" if dados.get('ativado', False) else "`Desativado`"
        status_emoji = emoji.on if dados.get('ativado', False) else emoji.off

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Proteção Geral > **Proteção de Banimentos**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"{status_emoji} **Status:** {status_texto}\n"
                                      f"{emoji.chart} **Limite atual:** `{dados.get('limite', 0)}`\n"
                                      f"{emoji.clock} **Intervalo atual:** `{dados.get('intervalo', 0)}s`"),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Configurar Proteção",
                        options=[
                            disnake.SelectOption(label="Desativar" if dados.get('ativado') else "Ativar", value="toggle", emoji=emoji.power),
                            disnake.SelectOption(label="Definir Limite", value="limite", emoji=emoji.chart, description=f"Limite de ações por intervalo"),
                            disnake.SelectOption(label="Definir Intervalo", value="intervalo", emoji=emoji.clock, description=f"Intervalo de tempo para a punição"),
                        ],
                        custom_id="ProtBanimentosConfigSelect"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Configurações Avançadas",
                        options=[
                            disnake.SelectOption(label="Configurar Punição", value="punicao", emoji=emoji.ban, description=desc_punicao),
                            disnake.SelectOption(label="Configurar Cargos Imunes", value="cargo_imune", emoji=emoji.role, description=select_cargos),
                            disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=select_logs),
                        ],
                        custom_id="ProtBanimentosConfigSelectAvancado"
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Geral"),
            )
        ]

    @commands.Cog.listener("on_dropdown")
    async def banimentos_dropdown_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if custom_id not in ["ProtBanimentosConfigSelect", "ProtBanimentosConfigSelectAvancado", "ProtBanimentosPunishmentSelect", "ProtBanimentosImmuneRoleSelect", "ProtBanimentosLogChannelSelect"]:
            return
        
        dropdown_handlers = {
            "ProtBanimentosPunishmentSelect": interactions.handle_punishment_select,
            "ProtBanimentosImmuneRoleSelect": interactions.handle_immune_role_select,
            "ProtBanimentosLogChannelSelect": interactions.handle_log_channel_select,
        }

        if custom_id in dropdown_handlers:
            await dropdown_handlers[custom_id](self, inter)
            return

        value = inter.values[0]

        config_handlers = {
            "toggle": interactions.handle_toggle,
            "limite": interactions.handle_set_limit,
            "intervalo": interactions.handle_set_interval,
            "punicao": interactions.handle_set_punishment,
            "cargo_imune": interactions.handle_set_immune_role,
            "canal_logs": interactions.handle_set_log_channel,
        }

        handler = config_handlers.get(value)
        if handler:
            await handler(self, inter)
        else:
            await inter.response.send_message(f"Ação '{value}' não reconhecida.", ephemeral=True)

    @commands.Cog.listener("on_button_click")
    async def banimentos_button_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        button_handlers = {
            "ProtBanimentos_Back": self.display_panel,
            "ProtBanimentosImmuneRoleClear": interactions.handle_immune_role_clear,
            "ProtBanimentosLogChannelClear": interactions.handle_log_channel_clear,
            "ProtBanimentosLogChannelCreate": interactions.handle_log_channel_create,
        }

        handler = button_handlers.get(custom_id)
        if handler:
            if custom_id == "ProtBanimentos_Back":
                await handler(inter)  # display_panel só precisa de 'inter'
            else:
                await handler(self, inter) # Outros handlers precisam de 'self' e 'inter'

def setup(bot: commands.Bot):
    bot.add_cog(BanimentosCog(bot))
