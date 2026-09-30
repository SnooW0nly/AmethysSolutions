import disnake
import asyncio
from disnake.ext import commands
from functions.emoji import emoji
from functions.database import database as db
from functions.perms import perms
from functions.message import message, embed_message
from functions.utils import utils

class ConectarCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._reconnect_attempted = False
        self._reconnecting = False

    def _get_connection_status(self, guild_id: int = None) -> dict:
        connection_data = db.get_document("bot_connection") or {}
        channel_id = connection_data.get("channel_id")
        
        channel = None
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
        
        is_connected = False
        if channel and self.bot.voice_clients:
            for vc in self.bot.voice_clients:
                if vc.channel and vc.channel.id == int(channel_id):
                    if guild_id is None or vc.guild.id == guild_id:
                        is_connected = True
                        break
        
        return {
            "channel_id": channel_id,
            "channel": channel,
            "is_connected": is_connected
        }

    def ConectarComponents(self, inter: disnake.MessageInteraction) -> list[disnake.ui.Container]:
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        connection = self._get_connection_status(inter.guild.id if inter.guild else None)
        channel = connection["channel"]
        is_connected = connection["is_connected"]

        channel_display = channel.mention if channel else "`Nenhum canal configurado`"

        connect_button_label = "Desconectar" if is_connected else "Conectar"
        connect_button_style = disnake.ButtonStyle.red if is_connected else disnake.ButtonStyle.green
        connect_button_emoji = emoji.voice

        container = disnake.ui.Container(
            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# **Gerenciar Conexão do Bot**"),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.TextDisplay(
                f"{emoji.voice} **Canal Atual:** {channel_display}"
            ),
            disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=connect_button_label,
                    style=connect_button_style,
                    emoji=connect_button_emoji,
                    custom_id="Conectar_Toggle"
                ),
                disnake.ui.Button(
                    label="Editar Canal",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="Conectar_EditChannel"
                ),
                disnake.ui.Button(
                    label="Configurar Canal",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.settings2,
                    custom_id="Conectar_ConfigurarCanal",
                    disabled=not connection["channel"],
                ),
            ),
            **container_kwargs
        )

        return [container]

    def ConectarEmbed(self, inter: disnake.MessageInteraction):
        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        connection = self._get_connection_status(inter.guild.id if inter.guild else None)
        channel = connection["channel"]
        is_connected = connection["is_connected"]

        channel_display = channel.mention if channel else "`Nenhum canal configurado`"

        embed = disnake.Embed(
            title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Gerenciar Conexão do Bot",
            description=f"{emoji.voice} **Canal Atual:** {channel_display}",
        )
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            embed.color = primary_color

        connect_button_label = "Desconectar" if is_connected else "Conectar"
        connect_button_style = disnake.ButtonStyle.red if is_connected else disnake.ButtonStyle.green
        connect_button_emoji = emoji.voice

        components = [
            disnake.ui.ActionRow(
                disnake.ui.Button(
                    label=connect_button_label,
                    style=connect_button_style,
                    emoji=connect_button_emoji,
                    custom_id="Conectar_Toggle"
                ),
                disnake.ui.Button(
                    label="Editar Canal",
                    style=disnake.ButtonStyle.blurple,
                    emoji=emoji.edit,
                    custom_id="Conectar_EditChannel"
                ),
                disnake.ui.Button(
                    label="Configurar Canal",
                    style=disnake.ButtonStyle.grey,
                    emoji=emoji.settings2,
                    custom_id="Conectar_ConfigurarCanal",
                    disabled=not channel,
                ),
            )
        ]
        return embed, components

    @commands.slash_command(
        name="conectar",
        description="Gerencia a conexão do bot em canais de voz.",
        guild_ids=[utils.obter_server_principal()],
    )
    async def conectar(self, inter: disnake.ApplicationCommandInteraction):
        await inter.response.defer(ephemeral=True)
        
        if not await perms.check(inter.user.id):
            await inter.followup.send("Você não tem permissão para usar este comando", ephemeral=True)
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            embed, components = self.ConectarEmbed(inter)
            await inter.edit_original_response(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_response(
                components=self.ConectarComponents(inter),
            )

    @commands.Cog.listener("on_button_click")
    async def Conectar_Button_Listener(self, inter: disnake.MessageInteraction):
        if not inter.component.custom_id.startswith("Conectar"):
            return

        custom_id = inter.component.custom_id

        if custom_id == "Conectar_Toggle":
            await self._handle_toggle_connection(inter)
        elif custom_id == "Conectar_EditChannel":
            await self._handle_edit_channel(inter)
        elif custom_id == "Conectar_ConfigurarCanal":
            await self._handle_configurar_canal(inter)

    async def _connect_to_channel(self, channel: disnake.VoiceChannel):
        for vc in self.bot.voice_clients:
            if vc.guild.id == channel.guild.id:
                await vc.disconnect(force=True)
                await asyncio.sleep(0.5)

        voice_client = await channel.connect(reconnect=False)
        await channel.guild.change_voice_state(channel=channel, self_deaf=True)
        return voice_client

    async def _handle_toggle_connection(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)
        
        connection = self._get_connection_status(inter.guild.id if inter.guild else None)
        channel_id = connection["channel_id"]
        is_connected = connection["is_connected"]

        if not channel_id:
            await inter.followup.send("Configure um canal primeiro usando o botão 'Editar Canal'", ephemeral=True)
            return

        channel = self.bot.get_channel(int(channel_id))
        if not channel:
            await inter.followup.send("Canal não encontrado. Configure um novo canal.", ephemeral=True)
            return

        if not isinstance(channel, disnake.VoiceChannel):
            await inter.followup.send("O canal configurado não é um canal de voz.", ephemeral=True)
            return

        try:
            if is_connected:
                for vc in self.bot.voice_clients:
                    if vc.channel and vc.channel.id == channel.id:
                        await vc.disconnect(force=True)
                        break
                
                connection_data = db.get_document("bot_connection") or {}
                connection_data["was_connected"] = False
                db.save_document("bot_connection", connection_data)
            else:
                await self._connect_to_channel(channel)
                
                connection_data = db.get_document("bot_connection") or {}
                connection_data["was_connected"] = True
                db.save_document("bot_connection", connection_data)
        except Exception as e:
            error_msg = str(e)
            if "PyNaCl" in error_msg:
                await inter.followup.send("Erro ao conectar: É necessário instalar a biblioteca PyNaCl. Execute: `pip install PyNaCl`", ephemeral=True)
            else:
                await inter.followup.send(f"Erro ao {'desconectar' if is_connected else 'conectar'}: {error_msg}", ephemeral=True)
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            embed, components = self.ConectarEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=self.ConectarComponents(inter))

    async def _handle_edit_channel(self, inter: disnake.MessageInteraction):
        await inter.response.defer(ephemeral=True)
        
        voice_channels = [ch for ch in inter.guild.channels if isinstance(ch, disnake.VoiceChannel)]
        
        if not voice_channels:
            await inter.followup.send("Não há canais de voz neste servidor.", ephemeral=True)
            return
        
        mode = db.get_document("custom_mode").get("mode")

        colors = db.get_document("custom_colors")
        primary_color_hex = colors.get("primary")

        select_options = [
            disnake.SelectOption(
                label=ch.name,
                value=str(ch.id),
                description=f"ID: {ch.id}"
            )
            for ch in voice_channels[:25]
        ]

        if mode == "components":
            container_kwargs = {}
            if primary_color_hex:
                container_kwargs["accent_colour"] = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

            container = disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# **Selecionar Canal de Voz**"),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(f"{emoji.information} Selecione o canal de voz onde o bot deve se conectar:"),
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        placeholder="Selecione um canal de voz...",
                        custom_id="Conectar_SelectChannel",
                        channel_types=[disnake.ChannelType.voice],
                        min_values=1,
                        max_values=1,
                    )
                ),
                **container_kwargs
            )
            await inter.edit_original_message(components=[container])
        else:
            embed_kwargs = {}
            if primary_color_hex:
                embed_kwargs["color"] = int(primary_color_hex.replace("#", ""), 16)

            embed = disnake.Embed(
                title=f"{emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5} Selecionar Canal de Voz",
                description=f"{emoji.information} Selecione o canal de voz onde o bot deve se conectar:",
                **embed_kwargs
            )

            components = [
                disnake.ui.ActionRow(
                    disnake.ui.ChannelSelect(
                        placeholder="Selecione um canal de voz...",
                        custom_id="Conectar_SelectChannel",
                        channel_types=[disnake.ChannelType.voice],
                        min_values=1,
                        max_values=1,
                    )
                )
            ]
            await inter.edit_original_message(content=None, embed=embed, components=components)

    async def _handle_configurar_canal(self, inter: disnake.MessageInteraction):
        connection = self._get_connection_status(inter.guild.id if inter.guild else None)
        channel = connection["channel"]

        if not channel or not isinstance(channel, disnake.VoiceChannel):
            await inter.response.send_message(
                f"{emoji.wrong} Nenhum canal de voz configurado!", ephemeral=True
            )
            return

        current_name = channel.name
        current_status = getattr(channel, "status", None) or ""

        current_emoji = ""
        current_clean_name = current_name
        if current_name:
            first_char = current_name[0]
            if ord(first_char) > 0xFF:
                end = 1
                if len(current_name) > 1 and ord(current_name[1]) == 0xFE0F:
                    end = 2
                current_emoji = current_name[:end]
                current_clean_name = current_name[end:].lstrip()

        await inter.response.send_modal(
            ConfigurarCanalModal(
                channel_id=channel.id,
                current_emoji=current_emoji,
                current_name=current_clean_name,
                current_status=current_status,
            )
        )

    @commands.Cog.listener("on_modal_submit")
    async def Conectar_Modal_Listener(self, inter: disnake.ModalInteraction):
        if not inter.custom_id.startswith("Conectar_ConfigurarCanalModal:"):
            return

        channel_id = int(inter.custom_id.split(":")[1])
        channel = inter.guild.get_channel(channel_id)

        if not channel or not isinstance(channel, disnake.VoiceChannel):
            await inter.response.send_message(
                f"{emoji.wrong} Canal não encontrado!", ephemeral=True
            )
            return

        new_emoji = (inter.text_values.get("canal_emoji") or "").strip()
        new_name  = (inter.text_values.get("canal_nome") or "").strip()
        new_desc  = (inter.text_values.get("canal_descricao") or "").strip()

        if not new_name:
            await inter.response.send_message(
                f"{emoji.wrong} O nome do canal não pode estar vazio!", ephemeral=True
            )
            return

        final_name = f"{new_emoji} {new_name}".strip() if new_emoji else new_name
        final_name = final_name[:100]

        try:
            await channel.edit(
                name=final_name,
                reason=f"Configurado via /conectar por {inter.author}",
            )
            if new_desc:
                route = disnake.http.Route("PUT", "/channels/{channel_id}/voice-status", channel_id=channel.id)
                await inter.bot.http.request(route, json={"status": new_desc[:500]})
            else:
                route = disnake.http.Route("PUT", "/channels/{channel_id}/voice-status", channel_id=channel.id)
                await inter.bot.http.request(route, json={"status": ""})
        except disnake.Forbidden:
            await inter.response.send_message(
                f"{emoji.wrong} Sem permissão para editar o canal!", ephemeral=True
            )
            return
        except Exception as e:
            await inter.response.send_message(
                f"{emoji.wrong} Erro ao editar canal: `{e}`", ephemeral=True
            )
            return

        await inter.response.defer(ephemeral=True)

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            embed, components = self.ConectarEmbed(inter)
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=self.ConectarComponents(inter))

        await inter.followup.send(
            f"{emoji.correct} Canal **{final_name}** configurado com sucesso!",
            ephemeral=True,
        )

    @commands.Cog.listener("on_dropdown")
    async def Conectar_Dropdown_Listener(self, inter: disnake.MessageInteraction):
        if inter.component.custom_id == "Conectar_SelectChannel":
            await inter.response.defer(ephemeral=True)
            
            channel_id = int(inter.values[0])
            channel = inter.guild.get_channel(channel_id)

            if not channel or not isinstance(channel, disnake.VoiceChannel):
                await inter.followup.send("Canal inválido.", ephemeral=True)
                return

            connection_data = db.get_document("bot_connection") or {}
            connection_data["channel_id"] = str(channel_id)
            db.save_document("bot_connection", connection_data)

            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                embed, components = self.ConectarEmbed(inter)
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.ConectarComponents(inter))

    @commands.Cog.listener("on_ready")
    async def auto_reconnect(self):
        if self._reconnect_attempted:
            return
        
        self._reconnect_attempted = True

        await self.bot.wait_until_ready()
        await asyncio.sleep(3)
        
        connection_data = db.get_document("bot_connection") or {}
        was_connected = connection_data.get("was_connected", False)
        channel_id = connection_data.get("channel_id")
        
        if not was_connected or not channel_id:
            return
        
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel or not isinstance(channel, disnake.VoiceChannel):
                connection_data["was_connected"] = False
                db.save_document("bot_connection", connection_data)
                return
            
            for vc in self.bot.voice_clients:
                if vc.channel and vc.channel.id == channel.id:
                    return
            
            await self._connect_to_channel(channel)
            print(f"[Conectar] Bot reconectado automaticamente ao canal {channel.name} ({channel.id})")
        except Exception as e:
            connection_data["was_connected"] = False
            db.save_document("bot_connection", connection_data)
            print(f"[Conectar] Erro ao reconectar automaticamente: {e}")

    @commands.Cog.listener("on_voice_state_update")
    async def keep_connected(self, member: disnake.Member, before: disnake.VoiceState, after: disnake.VoiceState):
        if member.id != self.bot.user.id:
            return

        if before.channel is not None and after.channel is None:
            connection_data = db.get_document("bot_connection") or {}
            was_connected = connection_data.get("was_connected", False)
            channel_id = connection_data.get("channel_id")

            if not was_connected or not channel_id:
                return

            if self._reconnecting:
                return
            self._reconnecting = True

            try:
                await asyncio.sleep(2)

                channel = self.bot.get_channel(int(channel_id))
                if not channel or not isinstance(channel, disnake.VoiceChannel):
                    return

                for vc in self.bot.voice_clients:
                    if vc.channel and vc.channel.id == channel.id:
                        return

                await self._connect_to_channel(channel)
                print(f"[Conectar] Bot reconectado ao canal {channel.name} após desconexão inesperada.")
            except Exception as e:
                print(f"[Conectar] Falha ao reconectar após desconexão: {e}")
            finally:
                self._reconnecting = False


class ConfigurarCanalModal(disnake.ui.Modal):
    def __init__(
        self,
        channel_id: int,
        current_emoji: str = "",
        current_name: str = "",
        current_status: str = "",
    ):
        components = [
            disnake.ui.TextInput(
                label="Emoji do canal",
                placeholder="Ex: 🎮  (deixe vazio para remover)",
                custom_id="canal_emoji",
                style=disnake.TextInputStyle.short,
                required=False,
                max_length=8,
                value=current_emoji,
            ),
            disnake.ui.TextInput(
                label="Nome do canal",
                placeholder="Ex: Gaming",
                custom_id="canal_nome",
                style=disnake.TextInputStyle.short,
                required=True,
                max_length=90,
                value=current_name,
            ),
            disnake.ui.TextInput(
                label="Descrição (status do canal)",
                placeholder="Ex: Canal de música 24/7",
                custom_id="canal_descricao",
                style=disnake.TextInputStyle.paragraph,
                required=False,
                max_length=500,
                value=current_status,
            ),
        ]
        super().__init__(
            title="Configurar Canal de Voz",
            components=components,
            custom_id=f"Conectar_ConfigurarCanalModal:{channel_id}",
        )

def setup(bot: commands.Bot):
    bot.add_cog(ConectarCommand(bot))
