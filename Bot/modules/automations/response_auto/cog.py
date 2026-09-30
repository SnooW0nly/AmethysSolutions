import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.message import message, embed_message
from .helpers import RespAutomaticasDB, truncar_para_mensagem
from functions.database import database as db

class RespAutomaticasUI:
    def __init__(self, db: RespAutomaticasDB):
        self.db = db

    def Painel(self) -> list[disnake.ui.Container]:
        status = self.db.get_status()
        responses = self.db.get_responses()

        status_str = "Ativado" if status else "Desativado"
        status_emoji = emoji.on if status else emoji.off
        status_button_style = disnake.ButtonStyle.red if status else disnake.ButtonStyle.green

        action_buttons = [
            disnake.ui.Button(
                label="",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.power,
                custom_id="ToggleRespAutomaticasStatus"
            ),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id="AdicionarRespAutomatica", disabled=not status)
        ]

        if responses:
            action_buttons.append(disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="RemoverRespAutomatica", disabled=not status))

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
-# Painel > Automações > **Respostas Automáticas**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"""
{status_emoji} **Status:** `{status_str}`
{emoji.message} **Respostas Automáticas:** `{len(responses)}`
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(*action_buttons),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            )
        ]

    def PainelEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        status = self.db.get_status()
        responses = self.db.get_responses()

        status_str = "Ativado" if status else "Desativado"
        status_emoji = emoji.on if status else emoji.off
        
        description = (
            f"{status_emoji} **Status:** `{status_str}`\n"
            f"{emoji.message} **Respostas Automáticas:** `{len(responses)}`"
        )

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Respostas Automáticas",
            description="Gerencie as respostas automáticas do servidor.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        embed.add_field(name="Configurações", value=description, inline=False)
        
        action_buttons = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="ToggleRespAutomaticasStatus"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id="AdicionarRespAutomatica", disabled=not status)
        ]

        if responses:
            action_buttons.append(disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="RemoverRespAutomatica", disabled=not status))
            
        components = [
            disnake.ui.ActionRow(*action_buttons),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações")
            )
        ]
        return embed, components

    def PainelRemover(self) -> list[disnake.ui.Container]:
        responses = self.db.get_responses()
        if not responses:
            return self.Painel()

        options = [
            disnake.SelectOption(
                label=f"Gatilho: {r['keyword']}",
                value=r['keyword'],
                description=f"Resposta: {r['response'][:50]}..." if len(r['response']) > 50 else f"Resposta: {r['response']}"
            ) for r in responses
        ]

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
-# Painel > Automações > Respostas > **Remover**
                """),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(
                    disnake.ui.StringSelect(
                        custom_id="RemoverRespAutomaticaSelect",
                        placeholder="Selecione uma resposta para remover",
                        options=options
                    )
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarPainelRespAutomaticas")
            )
        ]

    def PainelRemoverEmbed(self) -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        responses = self.db.get_responses()
        if not responses:
            return self.PainelEmbed()

        options = [
            disnake.SelectOption(
                label=f"Gatilho: {r['keyword']}",
                value=r['keyword'],
                description=f"Resposta: {r['response'][:50]}..." if len(r['response']) > 50 else f"Resposta: {r['response']}"
            ) for r in responses
        ]

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        embed = disnake.Embed(
            title=f"Remover Resposta Automática",
            description="Selecione uma resposta automática para remover.",
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

        components = [
            disnake.ui.ActionRow(
                disnake.ui.StringSelect(
                    custom_id="RemoverRespAutomaticaSelect",
                    placeholder="Selecione uma resposta para remover",
                    options=options
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarPainelRespAutomaticas")
            )
        ]
        return embed, components

class RespAutomaticasCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = RespAutomaticasDB()
        self.ui = RespAutomaticasUI(self.db)

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        db_instance = RespAutomaticasDB()
        ui_instance = RespAutomaticasUI(db_instance)
        return ui_instance.PainelEmbed()

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        
        if custom_id == "AdicionarRespAutomatica":
            await inter.response.send_modal(
                title="Adicionar Resposta Automática",
                custom_id="RespAutomaticaModal",
                components=[
                    disnake.ui.TextInput(
                        label="Palavra ou Frase (Gatilho)",
                        placeholder="Insira a palavra ou frase chave",
                        custom_id="keyword_input",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=100
                    ),
                    disnake.ui.TextInput(
                        label="Resposta",
                        placeholder="Insira a resposta do bot",
                        custom_id="response_input",
                        style=disnake.TextInputStyle.paragraph,
                        required=True,
                        max_length=2000
                    ),
                    disnake.ui.TextInput(
                        label="Resposta via DM? (sim/não)",
                        placeholder="A resposta será enviada na DM do autor.",
                        custom_id="ephemeral_input",
                        style=disnake.TextInputStyle.short,
                        required=True,
                        max_length=3
                    )
                ]
            )
            return

        relevant_ids = ["ToggleRespAutomaticasStatus", "RemoverRespAutomatica", "VoltarPainelRespAutomaticas"]
        if custom_id not in relevant_ids:
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)

        if custom_id == "ToggleRespAutomaticasStatus":
            current_status = self.db.get_status()
            self.db.set_status(not current_status)
            if mode == "embed":
                embed, components = self.ui.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.Painel())

        elif custom_id == "RemoverRespAutomatica":
            if mode == "embed":
                embed, components = self.ui.PainelRemoverEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.PainelRemover())
            
        elif custom_id == "VoltarPainelRespAutomaticas":
            if mode == "embed":
                embed, components = self.ui.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.Painel())

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        custom_id = inter.data.custom_id

        if custom_id == "RemoverRespAutomaticaSelect":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)
            
            keyword = inter.values[0]
            self.db.remove_response(keyword)

            if mode == "embed":
                embed, components = self.ui.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.Painel())

    @commands.Cog.listener("on_modal_submit")
    async def on_modal_submit(self, inter: disnake.ModalInteraction):
        custom_id = inter.custom_id

        if custom_id == "RespAutomaticaModal":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)

            keyword = inter.text_values["keyword_input"].strip()
            response_raw = inter.text_values["response_input"].strip()
            ephemeral_str = inter.text_values["ephemeral_input"].strip().lower()

            if not keyword or not response_raw:
                # Em caso de erro, atualizar o painel também
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel())
                await inter.followup.send("O gatilho e a resposta não podem estar vazios.", ephemeral=True)
                return

            if ephemeral_str not in ["sim", "não", "nao"]:
                # Em caso de erro, atualizar o painel também
                if mode == "embed":
                    embed, components = self.ui.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.ui.Painel())
                await inter.followup.send("Resposta inválida para 'efêmera'. Use 'sim' ou 'não'.", ephemeral=True)
                return
            
            # Truncar resposta para garantir que não exceda limites do Discord
            response = truncar_para_mensagem(response_raw)
            
            if response != response_raw:
                await inter.followup.send(f"⚠️ A resposta foi truncada para {len(response)} caracteres para respeitar os limites do Discord.", ephemeral=True)
            
            ephemeral = ephemeral_str == "sim"
            
            self.db.add_response(keyword, response, ephemeral)

            if mode == "embed":
                embed, components = self.ui.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ui.Painel())

def setup(bot: commands.Bot):
    bot.add_cog(RespAutomaticasCog(bot))
