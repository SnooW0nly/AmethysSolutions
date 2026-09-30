import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from functions.message import message, embed_message

from . import helpers
from . import interactions

class PrivatizacaoMencoesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _get_advanced_select_descriptions(self, inter: disnake.Interaction, avancado: dict) -> tuple:
        punicao_atual = avancado.get("punicao", "kick")
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
            disnake.SelectOption(label="Banimento", value="ban", default=punicao_atual == 'ban', description="Bane o membro que fizer uma menção proibida."),
            disnake.SelectOption(label="Expulsão", value="kick", default=punicao_atual == 'kick', description="Expulsa o membro que fizer uma menção proibida."),
            disnake.SelectOption(label="Castigo de 30 dias", value="timeout_30d", default=punicao_atual == 'timeout_30d', description="Aplica um castigo de 30 dias ao membro."),
            disnake.SelectOption(label="Remoção dos Cargos", value="remove_roles", default=punicao_atual == 'remove_roles', description="Remove todos os cargos do membro."),
            disnake.SelectOption(label="Nenhuma", value="none", default=punicao_atual == 'none', description="Nenhuma ação será tomada (apenas logs)."),
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
        mode = db.get_document("custom_mode").get("mode")
        msg_handler = embed_message if mode == "embed" else message
        await msg_handler.wait(inter, send=False)

        if mode == "embed":
            embed, components = self.PunishmentPanelEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            components = self.PunishmentPanelComponents(inter)
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

    def PunishmentPanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get("privatizacao_mencoes_avancado", {})
        punicao_atual = avancado.get("punicao", "kick")
        
        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title=f"Configurar Punição",
            description="Escolha a punição para quem fizer uma menção não permitida.",
            color=primary_color
        )

        options = self._get_punishment_options(punicao_atual)
        components = [
            disnake.ui.ActionRow(disnake.ui.Select(options=options, custom_id="ProtPrivMencoesPunishmentSelect")),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtPrivMencoes_Back"))
        ]
        return embed, components

    def PunishmentPanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        avancado = config.get("privatizacao_mencoes_avancado", {})
        punicao_atual = avancado.get("punicao", "kick")
        options = self._get_punishment_options(punicao_atual)
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Privatizações > Menções > **Punição**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Escolha a punição para o infrator."),
                disnake.ui.ActionRow(disnake.ui.Select(options=options, custom_id="ProtPrivMencoesPunishmentSelect")),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtPrivMencoes_Back"))
        ]

    def ImmuneRolePanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get("privatizacao_mencoes_avancado", {})
        cargos_imunes = avancado.get("cargos_imunes", [])
        
        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title=f"Configurar Cargos Imunes",
            description="Selecione os cargos que poderão fazer menções.",
            color=primary_color
        )

        cargos_str = ", ".join([f'<@&{cid}>' for cid in cargos_imunes]) if cargos_imunes else "Nenhum"
        embed.add_field(name="Cargos Imunes Atuais", value=cargos_str)
        components = [
            disnake.ui.ActionRow(disnake.ui.RoleSelect(custom_id="ProtPrivMencoesImmuneRoleSelect", max_values=25)),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtPrivMencoes_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red, custom_id="ProtPrivMencoesImmuneRoleClear", disabled=not cargos_imunes)
            )
        ]
        return embed, components

    def ImmuneRolePanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        avancado = config.get("privatizacao_mencoes_avancado", {})
        cargos_imunes = avancado.get("cargos_imunes", [])
        cargos_str = ", ".join([f'<@&{cid}>' for cid in cargos_imunes]) if cargos_imunes else "Nenhum"
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Privatizações > Menções > **Cargos Imunes**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Cargos Atuais: {cargos_str}"),
                disnake.ui.ActionRow(disnake.ui.RoleSelect(custom_id="ProtPrivMencoesImmuneRoleSelect", max_values=25)),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtPrivMencoes_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red, custom_id="ProtPrivMencoesImmuneRoleClear", disabled=not cargos_imunes)
            )
        ]

    def LogChannelPanelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        avancado = config.get("privatizacao_mencoes_avancado", {})
        canal_logs_id = avancado.get("canal_logs")
        
        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title=f"Configurar Canal de Logs",
            description="Selecione o canal para os logs da proteção.",
            color=primary_color
        )

        canal_str = f"<#{canal_logs_id}>" if canal_logs_id else "Nenhum"
        embed.add_field(name="Canal de Logs Atual", value=canal_str)
        components = [
            disnake.ui.ActionRow(disnake.ui.ChannelSelect(custom_id="ProtPrivMencoesLogChannelSelect", channel_types=[disnake.ChannelType.text])),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtPrivMencoes_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red, custom_id="ProtPrivMencoesLogChannelClear", disabled=not canal_logs_id),
                disnake.ui.Button(label="Criar para mim", style=disnake.ButtonStyle.blurple, emoji=emoji.wand, custom_id="ProtPrivMencoesLogChannelCreate"),
            )
        ]
        return embed, components

    def LogChannelPanelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        avancado = config.get("privatizacao_mencoes_avancado", {})
        canal_logs_id = avancado.get("canal_logs")
        canal_str = f"<#{canal_logs_id}>" if canal_logs_id else "Nenhum"
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Privatizações > Menções > **Logs**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Canal Atual: {canal_str}"),
                disnake.ui.ActionRow(disnake.ui.ChannelSelect(custom_id="ProtPrivMencoesLogChannelSelect", channel_types=[disnake.ChannelType.text])),
                **container_kwargs
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="ProtPrivMencoes_Back"),
                disnake.ui.Button(label="Remover", emoji=emoji.delete, style=disnake.ButtonStyle.red, custom_id="ProtPrivMencoesLogChannelClear", disabled=not canal_logs_id),
                disnake.ui.Button(label="Criar para mim", style=disnake.ButtonStyle.blurple, emoji=emoji.wand, custom_id="ProtPrivMencoesLogChannelCreate"),
            )
        ]

    def PainelEmbed(self, inter: disnake.MessageInteraction):
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get("privatizacao_mencoes_avancado", {})
        
        colors = db.get_document("custom_colors")
        primary_color = int(colors.get("primary").replace("#", ""), 16) if colors.get("primary") else None

        embed = disnake.Embed(
            title=f"Privatização de Menções",
            color=primary_color
        )

        status_emoji = emoji.on if dados.get('ativado', False) else emoji.off
        embed.description = f"{status_emoji} **Status:** `{'Ativado' if dados.get('ativado') else 'Desativado'}`\n\nImpede que membros não autorizados mencionem usuários ou cargos."
        
        desc_punicao, select_cargos, select_logs = self._get_advanced_select_descriptions(inter, avancado)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Select(
                    placeholder="Configurar Proteção",
                    options=[
                        disnake.SelectOption(label="Desativar" if dados.get('ativado') else "Ativar", value="toggle", emoji=emoji.power),
                        disnake.SelectOption(label="Configurar Punição", value="punicao", emoji=emoji.ban, description=desc_punicao),
                        disnake.SelectOption(label="Configurar Cargos Imunes", value="cargo_imune", emoji=emoji.role, description=select_cargos),
                        disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=select_logs),
                    ],
                    custom_id="ProtPrivMencoesConfigSelect"
                ),
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Privatizacoes_Panel"))
        ]
        return embed, components

    def PainelComponents(self, inter: disnake.MessageInteraction) -> list:
        config = helpers.carregar_config()
        dados = config.get(helpers.CHAVE, {})
        avancado = config.get("privatizacao_mencoes_avancado", {})
        desc_punicao, select_cargos, select_logs = self._get_advanced_select_descriptions(inter, avancado)
        status_emoji = emoji.on if dados.get('ativado', False) else emoji.off
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Proteção > Privatizações > **Menções**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(
                    f"{status_emoji} **Status:** `{'Ativado' if dados.get('ativado') else 'Desativado'}`"
                ),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Select(
                        placeholder="Configurar Proteção",
                        options=[
                            disnake.SelectOption(label="Desativar" if dados.get('ativado') else "Ativar", value="toggle", emoji=emoji.power),
                            disnake.SelectOption(label="Configurar Punição", value="punicao", emoji=emoji.ban, description=desc_punicao),
                            disnake.SelectOption(label="Configurar Cargos Imunes", value="cargo_imune", emoji=emoji.role, description=select_cargos),
                            disnake.SelectOption(label="Configurar Canal de Logs", value="canal_logs", emoji=emoji.textc, description=select_logs),
                        ],
                        custom_id="ProtPrivMencoesConfigSelect"
                    ),
                ),
                **container_kwargs
            ),
            disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Privatizacoes_Panel"))
        ]

    @commands.Cog.listener("on_dropdown")
    async def priv_mencoes_dropdown_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if "ProtPrivMencoes" not in custom_id:
            return
        
        if custom_id == "ProtPrivMencoesPunishmentSelect":
            await interactions.handle_punishment_select(self, inter)
            return
        if custom_id == "ProtPrivMencoesImmuneRoleSelect":
            await interactions.handle_immune_role_select(self, inter)
            return
        if custom_id == "ProtPrivMencoesLogChannelSelect":
            await interactions.handle_log_channel_select(self, inter)
            return

        value = inter.values[0]
        action_map = {
            "toggle": interactions.handle_toggle,
            "punicao": interactions.handle_set_punishment,
            "cargo_imune": interactions.handle_set_immune_role,
            "canal_logs": interactions.handle_set_log_channel,
        }
        handler = action_map.get(value)
        if handler:
            await handler(self, inter)

    @commands.Cog.listener("on_button_click")
    async def priv_mencoes_button_listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if "ProtPrivMencoes" not in custom_id:
            return

        action_map = {
            "ProtPrivMencoes_Back": self.display_panel,
            "ProtPrivMencoesImmuneRoleClear": interactions.handle_immune_role_clear,
            "ProtPrivMencoesLogChannelClear": interactions.handle_log_channel_clear,
            "ProtPrivMencoesLogChannelCreate": interactions.handle_log_channel_create,
        }
        handler = action_map.get(custom_id)
        if handler:
            if custom_id == "ProtPrivMencoes_Back":
                await handler(inter)
            else:
                await handler(self, inter)

def setup(bot: commands.Bot):
    bot.add_cog(PrivatizacaoMencoesCog(bot))
