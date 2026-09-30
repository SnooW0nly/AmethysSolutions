import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message

from . import helpers
from . import interactions

class CanaisCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_advanced_select_descriptions(self, inter: disnake.Interaction, protecoes: dict) -> tuple:
        punicao_atual = protecoes["canais_avancado"].get("punicao", "ban")
        desc_punicao = f"Atual: {helpers.formatar_punicao(punicao_atual)}"

        cargos_imunes = protecoes["canais_avancado"].get("cargos_imunes", [])
        cargos_nomes = [r.name for r in [inter.guild.get_role(cid) for cid in cargos_imunes] if r]
        select_cargos = f"Atual: {', '.join(cargos_nomes)}" if cargos_nomes else "Atual: Nenhum"
        if len(select_cargos) > 100:
            select_cargos = select_cargos[:97] + "..."

        categorias_imunes = protecoes["canais_avancado"].get("categorias_imunes", [])
        categorias_nomes = [c.name for c in [inter.guild.get_channel(cid) for cid in categorias_imunes] if c]
        desc_categorias = f"Atuais: {', '.join(categorias_nomes)}" if categorias_nomes else "Nenhuma"
        if len(desc_categorias) > 100:
            desc_categorias = desc_categorias[:97] + "..."

        canal_logs_id = protecoes["canais_avancado"].get("canal_logs")
        canal = inter.guild.get_channel(canal_logs_id) if canal_logs_id else None
        select_logs = f"Atual: {canal.name}" if canal else "Atual: Nenhum"
        
        return desc_punicao, select_cargos, desc_categorias, select_logs

    # --- Display Handlers ---

    async def display_panel(self, inter: disnake.MessageInteraction, tipo=None):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if mode == "embed":
            embed, components = self.PainelEmbed(inter, tipo)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.PainelComponents(inter, tipo)
            await inter.edit_original_message(content=None, embed=None, components=components)

    async def display_punicao_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if mode == "embed":
            embed, components = self.PunicaoPanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.PunicaoPanelComponents(inter)
            await inter.edit_original_message(content=None, embed=None, components=components)

    async def display_cargo_imune_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if mode == "embed":
            embed, components = self.CargoImunePanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.CargoImunePanelComponents(inter)
            await inter.edit_original_message(content=None, embed=None, components=components)
    
    async def display_categoria_imune_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if mode == "embed":
            embed, components = self.CategoriaImunePanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.CategoriaImunePanelComponents(inter)
            await inter.edit_original_message(content=None, embed=None, components=components)

    async def display_logs_panel(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)
        if mode == "embed":
            embed, components = self.LogsPanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.LogsPanelComponents(inter)
            await inter.edit_original_message(content=None, embed=None, components=components)

    # --- Main Panel Builders ---
    
    def PainelEmbed(self, inter: disnake.MessageInteraction, tipo=None):
        protecoes = helpers.carregar_config()
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        embed = disnake.Embed()
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)

        if tipo in helpers.TIPOS:
            dados = protecoes[tipo]
            nome_map = {"criacao": "Criação", "edicao": "Edição", "exclusao": "Exclusão"}
            nome = nome_map[tipo]
            embed.title = f"Proteção de {nome} de Canais"
            status_emoji = emoji.on if dados['ativado'] else emoji.off
            embed.description = (
                f"{status_emoji} **Status:** `{'Ativado' if dados['ativado'] else 'Desativado'}`\n"
                f"{emoji.chart} **Limite atual:** `{dados['limite']}`\n"
                f"{emoji.clock} **Intervalo atual:** `{dados['intervalo']}s`"
            )
            components = [
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Configurar Proteção",
                        options=[
                            disnake.SelectOption(label="Desativar" if dados['ativado'] else "Ativar", value="toggle", emoji=emoji.power),
                            disnake.SelectOption(label="Definir Limite", value="limite", emoji=emoji.chart, description=f"Limite de ações por intervalo"),
                            disnake.SelectOption(label="Definir Intervalo", value="intervalo", emoji=emoji.clock, description=f"Intervalo de tempo para a punição"),
                        ],
                        custom_id=f"ProtCanaisTipoConfig_{tipo}"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Canais"),
                )
            ]
            return embed, components
        
        embed.title = f"Painel de Proteção de Canais"
        embed.description = "Gerencie as proteções de canais do servidor."

        status_criacao = emoji.on if protecoes['criacao']['ativado'] else emoji.off
        status_edicao = emoji.on if protecoes['edicao']['ativado'] else emoji.off
        status_exclusao = emoji.on if protecoes['exclusao']['ativado'] else emoji.off

        embed.add_field(
            name=f"{emoji.plus} Criações em Massa",
            value=(
                f"{status_criacao} Status: `{'Ativado' if protecoes['criacao']['ativado'] else 'Desativado'}`\n"
                f"{emoji.chart} Limite: `{protecoes['criacao']['limite']}`\n"
                f"{emoji.clock} Intervalo: `{protecoes['criacao']['intervalo']}s`"
            ),
            inline=True
        )
        embed.add_field(
            name=f"{emoji.edit} Edições em Massa",
            value=(
                f"{status_edicao} Status: `{'Ativado' if protecoes['edicao']['ativado'] else 'Desativado'}`\n"
                f"{emoji.chart} Limite: `{protecoes['edicao']['limite']}`\n"
                f"{emoji.clock} Intervalo: `{protecoes['edicao']['intervalo']}s`"
            ),
            inline=True
        )
        embed.add_field(
            name=f"{emoji.delete} Exclusões em Massa",
            value=(
                f"{status_exclusao} Status: `{'Ativado' if protecoes['exclusao']['ativado'] else 'Desativado'}`\n"
                f"{emoji.chart} Limite: `{protecoes['exclusao']['limite']}`\n"
                f"{emoji.clock} Intervalo: `{protecoes['exclusao']['intervalo']}s`"
            ),
            inline=True
        )

        desc_punicao, select_cargos, desc_categorias, select_logs = self._get_advanced_select_descriptions(inter, protecoes)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Tipo de Proteção",
                    options=[
                        disnake.SelectOption(label="Proteção de Criação", value="criacao", emoji=emoji.plus, description=f"Contra a criação de canais em massa"),
                        disnake.SelectOption(label="Proteção de Edições", value="edicao", emoji=emoji.edit, description=f"Contra a edição de canais em massa"),
                        disnake.SelectOption(label="Proteção de Exclusão", value="exclusao", emoji=emoji.delete, description=f"Contra a exclusão de canais em massa"),
                    ],
                    custom_id="ProtCanaisTipoSelect"
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Configurações Avançadas",
                    options=[
                        disnake.SelectOption(label="Configurar Punição", value="punicao", emoji=emoji.ban, description=desc_punicao),
                        disnake.SelectOption(label="Configurar Cargos Imunes", value="cargo_imune", emoji=emoji.role, description=select_cargos),
                        disnake.SelectOption(label="Configurar Categoria Imune", value="categoria_imune", emoji=emoji.dir, description=desc_categorias),
                        disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=select_logs),
                    ],
                    custom_id="ProtCanaisConfigSelect"
                ),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Geral"),
            )
        ]
        return embed, components

    def PainelComponents(self, inter: disnake.MessageInteraction, tipo=None) -> list:
        protecoes = helpers.carregar_config()
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        if tipo in helpers.TIPOS:
            dados = protecoes[tipo]
            nome_map = {"criacao": "Criação", "edicao": "Edição", "exclusao": "Exclusão"}
            nome = nome_map[tipo]
            status_emoji = emoji.on if dados['ativado'] else emoji.off
            return [
                disnake.ui.Container(
                    disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Canais > **{nome}**"),
                    disnake.ui.Separator(),
                    disnake.ui.TextDisplay(f"{status_emoji} **Status:** `{'Ativado' if dados['ativado'] else 'Desativado'}`\n{emoji.chart} **Limite atual:** `{dados['limite']}`\n{emoji.clock} **Intervalo atual:** `{dados['intervalo']}s`"),
                    disnake.ui.Separator(),
                    disnake.ui.ActionRow(
                        disnake.ui.Select(
                            placeholder="Configurar Proteção",
                            options=[
                                disnake.SelectOption(label="Desativar" if dados['ativado'] else "Ativar", value="toggle", emoji=emoji.power),
                                disnake.SelectOption(label="Definir Limite", value="limite", emoji=emoji.chart, description=f"Limite de ações por intervalo"),
                                disnake.SelectOption(label="Definir Intervalo", value="intervalo", emoji=emoji.clock, description=f"Intervalo de tempo para a punição"),
                            ],
                            custom_id=f"ProtCanaisTipoConfig_{tipo}"
                        ),
                    ),
                    **container_kwargs
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Canais"),
                )
            ]
        
        desc_punicao, select_cargos, desc_categorias, select_logs = self._get_advanced_select_descriptions(inter, protecoes)

        status_criacao = emoji.on if protecoes['criacao']['ativado'] else emoji.off
        status_edicao = emoji.on if protecoes['edicao']['ativado'] else emoji.off
        status_exclusao = emoji.on if protecoes['exclusao']['ativado'] else emoji.off

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > **Canais**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**{emoji.plus} Criações em Massa**\n{status_criacao} Status: `{'Ativado' if protecoes['criacao']['ativado'] else 'Desativado'}`\n{emoji.chart} Limite: `{protecoes['criacao']['limite']}` | Intervalo: `{protecoes['criacao']['intervalo']}s`"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**{emoji.edit} Edições em Massa**\n{status_edicao} Status: `{'Ativado' if protecoes['edicao']['ativado'] else 'Desativado'}`\n{emoji.chart} Limite: `{protecoes['edicao']['limite']}` | Intervalo: `{protecoes['edicao']['intervalo']}s`"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"**{emoji.delete} Exclusões em Massa**\n{status_exclusao} Status: `{'Ativado' if protecoes['exclusao']['ativado'] else 'Desativado'}`\n{emoji.chart} Limite: `{protecoes['exclusao']['limite']}` | Intervalo: `{protecoes['exclusao']['intervalo']}s`"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Tipo de Proteção",
                        options=[
                            disnake.SelectOption(label="Proteção de Criação", value="criacao", emoji=emoji.plus, description=f"Contra a criação de canais em massa"),
                            disnake.SelectOption(label="Proteção de Edições", value="edicao", emoji=emoji.edit, description=f"Contra a edição de canais em massa" ),
                            disnake.SelectOption(label="Proteção de Exclusão", value="exclusao", emoji=emoji.delete, description=f"Contra a exclusão de canais em massa"),
                        ],
                        custom_id="ProtCanaisTipoSelect"
                    ),
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Configurações Avançadas",
                        options=[
                            disnake.SelectOption(label="Configurar Punição", value="punicao", emoji=emoji.ban, description=desc_punicao),
                            disnake.SelectOption(label="Configurar Cargos Imunes", value="cargo_imune", emoji=emoji.role, description=select_cargos),
                            disnake.SelectOption(label="Configurar Categoria Imune", value="categoria_imune", emoji=emoji.dir, description=desc_categorias),
                            disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=select_logs),
                        ],
                        custom_id="ProtCanaisConfigSelect"
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Protecao_Geral"),
            )
        ]

    # --- Component Builders ---

    def _get_punishment_options(self, punicao_atual: str) -> list[disnake.SelectOption]:
        return [
            disnake.SelectOption(label="Banimento", value="ban", default=punicao_atual == 'ban', description="Bane o membro que exceder o limite."),
            disnake.SelectOption(label="Expulsão", value="kick", default=punicao_atual == 'kick', description="Expulsa o membro que exceder o limite."),
            disnake.SelectOption(label="Castigo de 30 dias", value="timeout_30d", default=punicao_atual == 'timeout_30d', description="Aplica um castigo de 30 dias ao membro."),
            disnake.SelectOption(label="Remoção de Cargos", value="remover_cargos", default=punicao_atual == 'remover_cargos', description="Remove todos os cargos do membro."),
            disnake.SelectOption(label="Reversão da Ação", value="revert_action", default=punicao_atual == 'revert_action', description="Reverte a ação feita pelo infrator."),
            disnake.SelectOption(label="Nenhuma", value="none", default=punicao_atual == 'none', description="Nenhuma ação será tomada (apenas logs)."),
        ]

    def PunicaoPanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        punicao_atual = config["canais_avancado"].get("punicao", "ban")
        embed = disnake.Embed(
            title=f"Configurar Punição",
            description="Escolha a punição para quem violar a proteção de canais.",
        )
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)
        options = self._get_punishment_options(punicao_atual)
        components = [
            disnake.ui.ActionRow(disnake.ui.Select(options=options, custom_id="ProtCanaisPunicaoSelect", min_values=1, max_values=1)),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Protecao_Canais", style=disnake.ButtonStyle.grey))
        ]
        return embed, components

    def PunicaoPanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        punicao_atual = config["canais_avancado"].get("punicao", "ban")
        options = self._get_punishment_options(punicao_atual)
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Canais > **Punição**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Aplique a punição para o infrator do limite."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(disnake.ui.Select(options=options, custom_id="ProtCanaisPunicaoSelect")),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Protecao_Canais", style=disnake.ButtonStyle.grey))
        ]

    def CargoImunePanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        cargos = config["canais_avancado"].get("cargos_imunes", [])
        embed = disnake.Embed(title=f"Cargos Imunes", description="Selecione os cargos que não serão afetados pela proteção.")
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)
        cargos_str = ", ".join(f"<@&{c}>" for c in cargos) or "Nenhum"
        embed.add_field(name="Cargos Atuais", value=cargos_str)
        components = [
            disnake.ui.ActionRow(disnake.ui.RoleSelect(custom_id="ProtCanaisCargoImuneSelect", max_values=25)),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Protecao_Canais"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtCanaisCargoImuneClear", style=disnake.ButtonStyle.red, disabled=not cargos)
            )
        ]
        return embed, components

    def CargoImunePanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        cargos = config["canais_avancado"].get("cargos_imunes", [])
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        cargos_str = ", ".join(f"<@&{c}>" for c in cargos) or "Nenhum"
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Canais > **Cargos Imunes**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Selecione os cargos que não serão afetados pela proteção."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Cargos Atuais: {cargos_str}"),
                disnake.ui.ActionRow(disnake.ui.RoleSelect(custom_id="ProtCanaisCargoImuneSelect", max_values=25)),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Protecao_Canais"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtCanaisCargoImuneClear", style=disnake.ButtonStyle.red, disabled=not cargos)
            )
        ]

    def CategoriaImunePanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        cats = config["canais_avancado"].get("categorias_imunes", [])
        embed = disnake.Embed(title=f"Categorias Imunes", description="Selecione as categorias que não serão afetadas.")
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)
        cats_str = ", ".join(f"<#{c}>" for c in cats) or "Nenhuma"
        embed.add_field(name="Categorias Atuais", value=cats_str)
        components = [
            disnake.ui.ActionRow(disnake.ui.ChannelSelect(custom_id="ProtCanaisCategoriaImuneSelect", channel_types=[disnake.ChannelType.category], max_values=25)),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Protecao_Canais"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtCanaisCategoriaImuneClear", style=disnake.ButtonStyle.red, disabled=not cats)
            )
        ]
        return embed, components

    def CategoriaImunePanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        cats = config["canais_avancado"].get("categorias_imunes", [])
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        cats_str = ", ".join(f"<#{c}>" for c in cats) or "Nenhuma"
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Canais > **Categorias Imunes**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Selecione as categorias que não serão afetadas."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Categorias Atuais: `{cats_str}`"),
                disnake.ui.ActionRow(disnake.ui.ChannelSelect(custom_id="ProtCanaisCategoriaImuneSelect", channel_types=[disnake.ChannelType.category], max_values=25)),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Protecao_Canais"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtCanaisCategoriaImuneClear", style=disnake.ButtonStyle.red, disabled=not cats)
            )
        ]

    def LogsPanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        canal_id = config["canais_avancado"].get("canal_logs")
        embed = disnake.Embed(title=f"Canal de Logs", description="Selecione o canal para enviar os logs.")
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        if primary_color_hex:
            embed.color = int(primary_color_hex.replace("#", ""), 16)
        canal_str = f"<#{canal_id}>" if canal_id else "Nenhum"
        embed.add_field(name="Canal Atual", value=canal_str)
        components = [
            disnake.ui.ActionRow(disnake.ui.ChannelSelect(custom_id="ProtCanaisLogsSelect", channel_types=[disnake.ChannelType.text])),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Protecao_Canais"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtCanaisLogsClear", style=disnake.ButtonStyle.red, disabled=not canal_id),
                disnake.ui.Button(label="Criar para mim", emoji=emoji.wand, custom_id="ProtCanaisLogsCreate", style=disnake.ButtonStyle.blurple),
            )
        ]
        return embed, components 

    def LogsPanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        canal_id = config["canais_avancado"].get("canal_logs")
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        canal_str = f"<#{canal_id}>" if canal_id else "Nenhum"
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Canais > **Canal de Logs**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Selecione o canal para enviar os logs."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"Canal Atual: {canal_str}"),
                disnake.ui.ActionRow(disnake.ui.ChannelSelect(custom_id="ProtCanaisLogsSelect", channel_types=[disnake.ChannelType.text])),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Protecao_Canais"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, custom_id="ProtCanaisLogsClear", style=disnake.ButtonStyle.red, disabled=not canal_id),
                disnake.ui.Button(label="Criar para mim", emoji=emoji.wand, custom_id="ProtCanaisLogsCreate", style=disnake.ButtonStyle.blurple),
            )
        ]

    # --- Listeners ---

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "ProtCanaisTipoSelect":
            await interactions.handle_tipo_select(self, inter)
        elif custom_id == "ProtCanaisConfigSelect":
            await interactions.handle_advanced_select(self, inter)
        elif custom_id.startswith("ProtCanaisTipoConfig_"):
            tipo = custom_id.split("_")[-1]
            await interactions.handle_per_type_config(self, inter, tipo)
        elif custom_id == "ProtCanaisPunicaoSelect":
            await interactions.handle_punicao_select(self, inter)
        elif custom_id == "ProtCanaisCargoImuneSelect":
            await interactions.handle_cargo_imune_select(self, inter)
        elif custom_id == "ProtCanaisCategoriaImuneSelect":
            await interactions.handle_categoria_imune_select(self, inter)
        elif custom_id == "ProtCanaisLogsSelect":
            await interactions.handle_logs_select(self, inter)

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id

        button_map = {
            "ProtCanaisCargoImuneClear": interactions.handle_cargo_imune_clear,
            "ProtCanaisCategoriaImuneClear": interactions.handle_categoria_imune_clear,
            "ProtCanaisLogsClear": interactions.handle_logs_clear,
            "ProtCanaisLogsCreate": interactions.handle_logs_create,
        }
        
        if custom_id == "Protecao_Canais":
            await self.display_panel(inter)
            return

        handler = button_map.get(custom_id)
        if handler:
            await handler(self, inter)

def setup(bot: commands.Bot):
    bot.add_cog(CanaisCog(bot))
