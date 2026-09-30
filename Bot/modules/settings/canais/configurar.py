import disnake
from disnake.ext import commands

from functions.database import database as db
from functions.emoji import emoji
from functions.message import message, embed_message
from .criar_todos import MensagensCanais
from .listar import CANAIS_OPCOES

class ConfigurarCanal(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def canal_components(inter: disnake.MessageInteraction, canal_key: str) -> list[disnake.ui.Container]:
        definicoes = db.get_document("canais") or {}
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)
            
        try:
            canalID = int(definicoes.get(canal_key))
        except:
            canalID = None

        canal = next((c for c in CANAIS_OPCOES if c[0] == canal_key), None)
        canal_nome = canal[1]

        try:
            canal_obj = inter.guild.get_channel(canalID)
        except:
            canal_obj = None

        canal_id_str = f"`{canal_obj.id}`" if canal_obj else "Não definido"
        canal_name = f"{canal_obj.mention}" if canal_obj else "Não definido"

        components = [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Configurações > Canais > **{canal[1]}**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"Utilize o painel para gerenciar os canais do servidor.\nPara configurar um canal, selecione-o na lista abaixo."),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay(f"**Canal selecionado:** `{canal_nome}`\n**Canal atual:** {canal_name} ({canal_id_str})"),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        channel_types=[disnake.ChannelType.text],
                        placeholder="Selecione um canal para definir",
                        custom_id=f"Configuracoes_EditarNovoCanal:{canal_key}",
                        min_values=1,
                        max_values=1,
                    )
                ),
                disnake.ui.ActionRow(
                    disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Configuracoes_ApagarCanal:{canal_key}", style=disnake.ButtonStyle.red, disabled=canal_obj is None),
                    disnake.ui.Button(label="Criar o canal para mim", emoji=emoji.wand, custom_id=f"Configuracoes_CriarCanal:{canal_key}", style=disnake.ButtonStyle.blurple),
                ),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Configuracoes_EditarCanais")
            )
        ]
        return components

    @staticmethod
    def canal_embed(inter: disnake.MessageInteraction, canal_key: str):
        definicoes = db.get_document("canais") or {}
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")
        try:
            canalID = int(definicoes.get(canal_key))
        except:
            canalID = None

        canal = next((c for c in CANAIS_OPCOES if c[0] == canal_key), None)
        canal_nome = canal[1]

        try:
            canal_obj = inter.guild.get_channel(canalID)
        except:
            canal_obj = None

        canal_id_str = f"`{canal_obj.id}`" if canal_obj else "Não definido"
        canal_name = f"{canal_obj.mention}" if canal_obj else "Não definido"

        embed = disnake.Embed(
            title=f"{canal_nome}",
            description=f"Utilize o painel para gerenciar os canais do servidor.\nPara configurar um canal, selecione-o na lista abaixo.",
            # timestamp=disnake.utils.utcnow()
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color

        embed.add_field(
            name="Canal selecionado:",
            value=f"`{canal_nome}`"
        )
        embed.add_field(
            name="Canal atual:",
            value=f"{canal_name} ({canal_id_str})"
        )
        # embed.set_footer(text=inter.guild.name, icon_url=inter.guild.icon.url if inter.guild.icon else None)

        components = [
            disnake.ui.ActionRow(
                disnake.ui.ChannelSelect(
                    channel_types=[disnake.ChannelType.text],
                    placeholder="Selecione um canal para definir",
                    custom_id=f"Configuracoes_EditarNovoCanal:{canal_key}",
                    min_values=1,
                    max_values=1,
                )
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Apagar", emoji=emoji.delete, custom_id=f"Configuracoes_ApagarCanal:{canal_key}", style=disnake.ButtonStyle.red, disabled=canal_obj is None),
                disnake.ui.Button(label="Criar o canal para mim", emoji=emoji.wand, custom_id=f"Configuracoes_CriarCanal:{canal_key}", style=disnake.ButtonStyle.blurple),
            ),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", emoji=emoji.back, custom_id="Configuracoes_EditarCanais")
            )
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def configurar_canais_button_listener(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")

        if inter.component.custom_id.startswith("Configuracoes_ApagarCanal"):
            canal_key = inter.component.custom_id.split(":")[1]
            canais_db = db.get_document("canais")
            canais_db[canal_key] = None
            db.save_document("canais", {}, canais_db)

            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.canal_embed(inter, canal_key)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.canal_components(inter, canal_key))
        
        elif inter.component.custom_id.startswith("Configuracoes_CriarCanal"):
            canal_key = inter.component.custom_id.split(":")[1]
            canal_nome = next((c for c in CANAIS_OPCOES if c[0] == canal_key), None)
            canal_nome = canal_nome[1]

            categoria = next((c for c in inter.guild.categories if c.name.lower() == "logs"), None)

            try:
                ch = await inter.guild.create_text_channel(
                    canal_nome,
                    category=categoria,
                    reason=f"Auto-criação pelo painel de configurações - {inter.user.name} ({inter.user.id})"
                )
            except Exception:
                pass

            canais_db = db.get_document("canais")
            canais_db[canal_key] = str(ch.id)
            db.save_document("canais", {}, canais_db)

            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.canal_embed(inter, canal_key)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.canal_components(inter, canal_key))

            if mode == "embed":
                embed, components = MensagensCanais.canal_criado_embed(ch, auto=False)
                await inter.followup.send(embed=embed, components=components, ephemeral=True)
            else:
                await ch.send(components=MensagensCanais.canal_criado_components(ch, auto=False), flags=disnake.MessageFlags(is_components_v2=True))

    @commands.Cog.listener("on_dropdown")
    async def configurar_canais_dropdown_listener(self, inter: disnake.MessageInteraction):
        mode = db.get_document("custom_mode").get("mode")

        if inter.component.custom_id.startswith("Configuracoes_EditarCanal"):
            canal_key = inter.values[0]
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.canal_embed(inter, canal_key)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.canal_components(inter, canal_key))
        
        elif inter.component.custom_id.startswith("Configuracoes_EditarNovoCanal"):
            canal_key = inter.component.custom_id.replace("Configuracoes_EditarNovoCanal:", "")
            canal_id = inter.values[0]
            canais_db = db.get_document("canais")
            canais_db[canal_key] = canal_id
            db.save_document("canais", {}, canais_db)
            
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.canal_embed(inter, canal_key)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.canal_components(inter, canal_key))