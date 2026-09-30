import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.message import message, embed_message
from .helpers import TopicoModal, TopicsDB
from functions.database import database as db

class TopicsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def Painel(self, guild: disnake.Guild) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)
        config = TopicsDB.carregar_config()
        ativado = config.get("ativado", False)
        topicos_count = len(config.get("topicos", []))
        immune_role_id = config.get("immune_role_id")
        immune_role = guild.get_role(immune_role_id) if immune_role_id else None

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.receipt} **Tópicos configurados:** `{topicos_count}`\n"
            f"{emoji.role} **Cargo Imune:** {immune_role.mention if immune_role else '`Nenhum`'}"
        )

        botoes_config = [
            disnake.ui.Button(
                label="",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.power,
                custom_id="Topicos_ToggleAtivo"
            ),
            disnake.ui.Button(
                label="Cargo Imune",
                style=disnake.ButtonStyle.blurple,
                emoji=emoji.role,
                custom_id="Topicos_SetImmuneRole",
                disabled=not ativado
            )
        ]
        
        botoes_gerenciar = [
            disnake.ui.Button(
                label="Adicionar",
                style=disnake.ButtonStyle.blurple,
                emoji=emoji.plus,
                custom_id="Topicos_AbrirAdicionar",
                disabled=not ativado
            ),
        ]
        if topicos_count > 0:
            botoes_gerenciar.append(
                disnake.ui.Button(
                    label="Remover",
                    style=disnake.ButtonStyle.red,
                    emoji=emoji.minus,
                    custom_id="Topicos_AbrirRemover",
                    disabled=not ativado
                )
            )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > **Tópicos**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(*botoes_config),
                disnake.ui.ActionRow(*botoes_gerenciar),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]

    @staticmethod
    def PainelEmbed(bot: commands.Bot, guild: disnake.Guild) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = TopicsDB.carregar_config()
        ativado = config.get("ativado", False)
        topicos_count = len(config.get("topicos", []))
        immune_role_id = config.get("immune_role_id")
        immune_role = guild.get_role(immune_role_id) if immune_role_id else None

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.receipt} **Tópicos configurados:** `{topicos_count}`\n"
            f"{emoji.role} **Cargo Imune:** {immune_role.mention if immune_role else '`Nenhum`'}"
        )

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Tópicos Automáticos",
            description="Crie tópicos automáticos em canais quando mensagens forem enviadas.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        embed.add_field(name="Configurações", value=resumo, inline=False)
        
        botoes_config = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Topicos_ToggleAtivo"),
            disnake.ui.Button(label="Cargo Imune", style=disnake.ButtonStyle.blurple, emoji=emoji.role, custom_id="Topicos_SetImmuneRole", disabled=not ativado)
        ]
        
        botoes_gerenciar = [
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id="Topicos_AbrirAdicionar", disabled=not ativado)
        ]
        if topicos_count > 0:
            botoes_gerenciar.append(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="Topicos_AbrirRemover", disabled=not ativado)
            )

        components = [
            disnake.ui.ActionRow(*botoes_config),
            disnake.ui.ActionRow(*botoes_gerenciar),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações")
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
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Tópicos > **Configurar Cargo Imune**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Selecione abaixo o cargo que não irá criar tópicos."),
                disnake.ui.ActionRow(
                    disnake.ui.RoleSelect(
                        custom_id="Topicos_ImmuneRoleSelect",
                        placeholder="Selecione o cargo imune",
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Topicos_Voltar"),
            )
        ]

    def PainelCargoImuneEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Tópicos > Configurar Cargo Imune",
            description="Selecione abaixo o cargo que não irá criar tópicos.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        components = [
            disnake.ui.ActionRow(
                disnake.ui.RoleSelect(
                    custom_id="Topicos_ImmuneRoleSelect",
                    placeholder="Selecione o cargo imune",
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Topicos_Voltar"),
            )
        ]
        return embed, components
    
    def PainelAdicionar(self) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)
        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > Tópicos > **Adicionar**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="Topicos_SelectCanal",
                        placeholder="Selecione um canal de texto",
                        channel_types=[disnake.ChannelType.text],
                        min_values=1,
                        max_values=1,
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Topicos_Voltar"),
            )
        ]

    def PainelAdicionarEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Tópicos > Adicionar",
            description="Selecione o canal onde os tópicos automáticos serão criados.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="Topicos_SelectCanal",
                    placeholder="Selecione um canal de texto",
                    channel_types=[disnake.ChannelType.text],
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Topicos_Voltar"),
            )
        ]
        return embed, components
    
    def PainelRemover(self, guild: disnake.Guild) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)
        config = TopicsDB.carregar_config()
        topicos = config.get("topicos", [])
        
        if not topicos:
            return self.Painel(guild)

        options = []
        for topico in topicos:
            channel = self.bot.get_channel(topico.get("channel_id"))
            channel_name = channel.name if channel else "Canal não encontrado"
            options.append(
                disnake.SelectOption(
                    label=f"{topico.get('name')}",
                    value=topico.get("id"),
                    description=f"Canal: #{channel_name}"
                )
            )

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > Tópicos > **Remover**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="Topicos_SelectRemover",
                        placeholder="Selecione um tópico",
                        options=options,
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Topicos_Voltar"),
            )
        ]

    def PainelRemoverEmbed(self, guild: disnake.Guild) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = TopicsDB.carregar_config()
        topicos = config.get("topicos", [])
        
        if not topicos:
            return self.PainelEmbed(self.bot, guild)

        options = []
        for topico in topicos:
            channel = self.bot.get_channel(topico.get("channel_id"))
            channel_name = channel.name if channel else "Canal não encontrado"
            options.append(
                disnake.SelectOption(
                    label=f"{topico.get('name')}",
                    value=topico.get("id"),
                    description=f"Canal: #{channel_name}"
                )
            )

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Tópicos > Remover",
            description="Selecione um tópico automático para remover.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="Topicos_SelectRemover",
                    placeholder="Selecione um tópico",
                    options=options,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Topicos_Voltar"),
            )
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("Topicos_"):
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "Topicos_ToggleAtivo":
            config = TopicsDB.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            TopicsDB.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed(self.bot, inter.guild)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel(inter.guild))
        elif cid == "Topicos_AbrirAdicionar":
            if mode == "embed":
                embed, components = self.PainelAdicionarEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelAdicionar())
        elif cid == "Topicos_AbrirRemover":
            if mode == "embed":
                embed, components = self.PainelRemoverEmbed(inter.guild)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelRemover(inter.guild))
        elif cid == "Topicos_Voltar":
            if mode == "embed":
                embed, components = self.PainelEmbed(self.bot, inter.guild)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel(inter.guild))
        elif cid == "Topicos_SetImmuneRole":
            if mode == "embed":
                embed, components = self.PainelCargoImuneEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelCargoImune())

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id
        if cid == "Topicos_SelectCanal":
            channel_id = int(inter.values[0])
            await inter.response.send_modal(TopicoModal(channel_id=channel_id))
            return
        
        if cid == "Topicos_SelectRemover":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)

            topico_id = inter.values[0]
            config = TopicsDB.carregar_config()
            
            topico_para_remover = next((t for t in config["topicos"] if t["id"] == topico_id), None)
            
            if topico_para_remover:
                config["topicos"] = [t for t in config["topicos"] if t.get("id") != topico_id]
                TopicsDB.salvar_config(config)

            if mode == "embed":
                embed, components = self.PainelRemoverEmbed(inter.guild)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.PainelRemover(inter.guild))

        elif cid == "Topicos_ImmuneRoleSelect":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)

            role_id = int(inter.values[0])
            config = TopicsDB.carregar_config()
            config["immune_role_id"] = role_id
            TopicsDB.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed(self.bot, inter.guild)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel(inter.guild))

def setup(bot: commands.Bot):
    bot.add_cog(TopicsCog(bot))
