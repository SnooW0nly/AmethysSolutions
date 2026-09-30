import disnake
from disnake.ext import commands
import json
from .helpers import ReacoesDB
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from functions.utils import utils

class ReacoesUI:
    def __init__(self, bot, db: ReacoesDB):
        self.bot = bot
        self.db = db

    def Painel(self) -> list[disnake.ui.Container]:
        status = self.db.get_status()
        reactions = self.db.get_reactions()

        status_str = "Ativado" if status else "Desativado"
        status_emoji = emoji.on if status else emoji.off
        status_button_style = disnake.ButtonStyle.red if status else disnake.ButtonStyle.green

        action_buttons = [
            disnake.ui.Button(
                label="" if not status else "",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.power,
                custom_id="ToggleReacoesStatus"
            ),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id="ConfigurarReacao", disabled=not status)
        ]

        if reactions:
            action_buttons.append(disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="RemoverReacao", disabled=not status))

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"""
# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}
-# Painel > Automações > **Reações**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"""
{status_emoji} **Status:** `{status_str}`
{emoji.message} **Reações Automáticas:** `{len(reactions)}`
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(*action_buttons),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]
        return components

    def PainelEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        status = self.db.get_status()
        reactions = self.db.get_reactions()

        status_str = "Ativado" if status else "Desativado"
        status_emoji = emoji.on if status else emoji.off
        
        description = f"""
{status_emoji} **Status:** `{status_str}`
{emoji.message} **Reações Automáticas:** `{len(reactions)}`
        """

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Reações Automáticas",
            description="Gerencie as reações automáticas do servidor.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        embed.add_field(name="Configurações", value=description.strip(), inline=False)
        
        action_buttons = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="ToggleReacoesStatus"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id="ConfigurarReacao", disabled=not status)
        ]

        if reactions:
            action_buttons.append(disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="RemoverReacao", disabled=not status))
            
        components = [
            disnake.ui.ActionRow(*action_buttons),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações")
            )
        ]
        return embed, components

    def PainelConfigurar(self) -> list[disnake.ui.Container]:
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
-# Painel > Automações > Reações > **Adicionar Reação**
                """),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        custom_id="CanalReacaoSelect",
                        placeholder="Selecione um canal",
                        channel_types=[disnake.ChannelType.text]
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarPainelReacoes")
            )
        ]

    def PainelConfigurarEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Adicionar Reação > Por Canal",
            description="Selecione o canal onde as mensagens receberão a reação automática.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    custom_id="CanalReacaoSelect",
                    placeholder="Selecione um canal",
                    channel_types=[disnake.ChannelType.text]
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarPainelReacoes")
            )
        ]
        return embed, components

    def PainelTipoConfiguracao(self) -> list[disnake.ui.Container]:
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
-# Painel > Automações > Reações > Adicionar Reação > **Tipo**
                """),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Por Canal", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id="ConfigurarReacaoCanal"),
                    disnake.ui.Button(label="Por Palavra", style=disnake.ButtonStyle.blurple, emoji=emoji.message, custom_id="ConfigurarReacaoPalavra")
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarPainelReacoes")
            )
        ]

    def PainelTipoConfiguracaoEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Adicionar Reação > Tipo",
            description="Escolha o tipo de gatilho para a reação automática.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Por Canal", style=disnake.ButtonStyle.blurple, emoji=emoji.textc, custom_id="ConfigurarReacaoCanal"),
                disnake.ui.Button(label="Por Palavra", style=disnake.ButtonStyle.blurple, emoji=emoji.message, custom_id="ConfigurarReacaoPalavra")
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarPainelReacoes")
            )
        ]
        return embed, components

    def PainelRemover(self) -> list[disnake.ui.Container]:
        reactions = self.db.get_reactions()
        if not reactions:
            return self.Painel()

        options = []
        for idx, r in enumerate(reactions):
            reaction_type = r.get("type")
            value = r.get("value")
            reaction_emoji = r.get("emoji")
            label = ""
            option_value = ""

            if reaction_type == "channel":
                if self.bot:
                    channel = self.bot.get_channel(int(value))
                    label = f"Canal: {channel.name}" if channel else f"Canal não encontrado ({value})"
                else:
                    label = f"Canal: {value}"
            elif reaction_type == "keyword":
                label = f"Palavra: {value}"
            else:
                continue
            
            # Use index instead of full JSON to avoid truncation issues
            option_value = str(idx)

            options.append(disnake.SelectOption(
                label=label, 
                value=option_value,
                emoji=reaction_emoji
            ))

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
-# Painel > Automações > Reações > **Remover**
                """),
                disnake.ui.Separator(),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="RemoverReacaoSelect",
                        placeholder="Selecione uma reação para remover",
                        options=options
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarPainelReacoes")
            )
        ]

    def PainelRemoverEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        reactions = self.db.get_reactions()
        if not reactions:
            return self.PainelEmbed()

        options = []
        for idx, r in enumerate(reactions):
            reaction_type = r.get("type")
            value = r.get("value")
            reaction_emoji = r.get("emoji")
            label = ""
            option_value = ""

            if reaction_type == "channel":
                if self.bot:
                    channel = self.bot.get_channel(int(value))
                    label = f"Canal: {channel.name}" if channel else f"Canal não encontrado ({value})"
                else:
                    label = f"Canal: {value}"
            elif reaction_type == "keyword":
                label = f"Palavra: {value}"
            else:
                continue
            
            # Use index instead of full JSON to avoid truncation issues
            option_value = str(idx)

            options.append(disnake.SelectOption(
                label=label, 
                value=option_value,
                emoji=reaction_emoji
            ))
        
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Remover Reação",
            description="Selecione a reação automática que deseja remover da lista.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        components = [
             disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="RemoverReacaoSelect",
                    placeholder="Selecione uma reação para remover",
                    options=options
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarPainelReacoes")
            )
        ]
        return embed, components

class ReacoesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = ReacoesDB()
        self.ui = ReacoesUI(bot, self.db)

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        db_instance = ReacoesDB()
        ui_instance = ReacoesUI(None, db_instance)
        return ui_instance.PainelEmbed()

    def cog_check(self, inter: disnake.ApplicationCommandInteraction):
        # Implement permission check logic here if needed
        return True

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        # Modal buttons must be handled before deferring.
        if custom_id == "ConfigurarReacaoPalavra":
            await inter.response.send_modal(
                title="Configurar Reação por Palavra",
                custom_id="PalavraReacaoModal",
                components=[
                    disnake.ui.TextInput(
                        label="Palavra ou Frase",
                        placeholder="Insira a palavra ou frase chave",
                        custom_id="palavra_input",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=100
                    ),
                    disnake.ui.TextInput(
                        label="Emoji",
                        placeholder="Insira o emoji ou ID do emoji",
                        custom_id="emoji_input",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=100
                    )
                ]
            )
            return

        # Check for other relevant custom_ids for this listener.
        relevant_ids = ["ToggleReacoesStatus", "ConfigurarReacao", "ConfigurarReacaoCanal", "RemoverReacao", "VoltarPainelReacoes"]
        if custom_id not in relevant_ids:
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        if custom_id == "ToggleReacoesStatus":
            current_status = self.db.get_status()
            self.db.set_status(not current_status)
            if mode == "embed":
                embed, components = self.ui.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.Painel())

        elif custom_id == "ConfigurarReacao":
            if mode == "embed":
                embed, components = self.ui.PainelTipoConfiguracaoEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.PainelTipoConfiguracao())

        elif custom_id == "ConfigurarReacaoCanal":
            if mode == "embed":
                embed, components = self.ui.PainelConfigurarEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.PainelConfigurar())

        elif custom_id == "RemoverReacao":
            if mode == "embed":
                embed, components = self.ui.PainelRemoverEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.PainelRemover())
            
        elif custom_id == "VoltarPainelReacoes":
            if mode == "embed":
                embed, components = self.ui.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.Painel())

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.data.custom_id

        if custom_id == "CanalReacaoSelect":
            channel_id = int(inter.values[0])
            await inter.response.send_modal(
                title="Configurar Reação",
                custom_id=f"EmojiReacaoModal_channel_{channel_id}",
                components=[
                    disnake.ui.TextInput(
                        label="Emoji",
                        placeholder="Insira o emoji ou ID do emoji",
                        custom_id="emoji_input",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=100
                    )
                ]
            )
        
        elif custom_id == "RemoverReacaoSelect":
            try:
                # Get the index from the selected value
                selected_idx = int(inter.values[0])
                reactions = self.db.get_reactions()
                
                if not (0 <= selected_idx < len(reactions)):
                    if not inter.response.is_done():
                        await inter.response.send_message("Reação não encontrada.", ephemeral=True)
                    else:
                        await inter.followup.send("Reação não encontrada.", ephemeral=True)
                    return
                
                reaction = reactions[selected_idx]
                self.db.remove_reaction(reaction["type"], reaction["value"], reaction["emoji"])
                
                mode = db.get_document("custom_mode").get("mode")
                if mode == "embed":
                    await embed_message.wait(inter)
                    embed, comps = self.ui.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=comps)
                else:
                    await message.wait(inter)
                    await inter.edit_original_message(components=self.ui.Painel())
            except (ValueError, IndexError, KeyError) as e:
                mode = db.get_document("custom_mode").get("mode")
                if not inter.response.is_done():
                    if mode == "embed":
                        await embed_message.wait(inter)
                    else:
                        await message.wait(inter)
                    await inter.followup.send("Erro ao remover reação. Tente novamente.", ephemeral=True)
                else:
                    await inter.followup.send("Erro ao remover reação. Tente novamente.", ephemeral=True)


    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id

        if custom_id.startswith("PalavraReacaoModal") or custom_id.startswith("EmojiReacaoModal_"):
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)

        if custom_id == "PalavraReacaoModal":
            keyword = inter.text_values["palavra_input"].strip()
            emoji_str = inter.text_values["emoji_input"].strip()

            if not keyword:
                await inter.response.send_message("A palavra-chave não pode estar vazia.", ephemeral=True)
                return

            is_valid_emoji = self.is_valid_emoji(emoji_str)
            
            if "error" in is_valid_emoji:
                final_emoji = is_valid_emoji["original"]
            else:
                final_emoji = is_valid_emoji["emoji"]


            if not "error" in is_valid_emoji:
                self.db.add_reaction("keyword", keyword, final_emoji)
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel())
            else:
                # Em caso de erro, atualizar o painel também
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel())
                await inter.followup.send("Emoji inválido. Por favor, use um emoji padrão ou o ID de um emoji do servidor.", ephemeral=True)


        elif custom_id.startswith("EmojiReacaoModal_"):
            parts = custom_id.split("_", 2)
            reaction_type = parts[1]
            value = parts[2]
            emoji_str = inter.text_values["emoji_input"].strip()
            
            is_valid_emoji = self.is_valid_emoji(emoji_str)
            if "error" in is_valid_emoji:
                final_emoji = is_valid_emoji["original"]
            else:
                final_emoji = is_valid_emoji["emoji"]

            if not "error" in is_valid_emoji:
                if reaction_type == "channel":
                    self.db.add_reaction("channel", int(value), final_emoji)
                else: # keyword
                    self.db.add_reaction("keyword", value, final_emoji)
                
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel())
            else:
                # Em caso de erro, atualizar o painel também
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel())
                await inter.followup.send("Emoji inválido. Por favor, use um emoji padrão ou o ID de um emoji do servidor.", ephemeral=True)

    def is_valid_emoji(self, emoji_str: str):
        validation = utils.validate_emoji_for_components(emoji_str)
        if validation["valid"]:
            emoji_result = validation["emoji"]
            if isinstance(emoji_result, disnake.PartialEmoji):
                return {"emoji": str(emoji_result)}
            else:
                return {"emoji": emoji_result}
        return {"error": validation.get("error", "invalid emoji"), "original": emoji_str}

def setup(bot: commands.Bot):
    bot.add_cog(ReacoesCog(bot))
