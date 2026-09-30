import disnake
from disnake.ext import commands
from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from . import helpers

class ConfigurarLockUnlockModal(disnake.ui.Modal):
    def __init__(self, bot: commands.Bot, canal_id: str, canal_nome: str):
        self.bot = bot
        self.canal_id = canal_id
        self.canal_nome = canal_nome
        
        config = helpers.carregar_config()
        canal_config = config.get("canais", {}).get(canal_id, {})
        horario_lock_atual = canal_config.get("horario_lock", "22:00")
        horario_unlock_atual = canal_config.get("horario_unlock", "08:00")

        components = [
            disnake.ui.TextInput(
                label="Horário de Lock (HH:MM)",
                placeholder="Ex: 22:00",
                custom_id="horario_lock",
                style=disnake.TextInputStyle.short,
                required=True,
                min_length=5,
                max_length=5,
                value=horario_lock_atual
            ),
            disnake.ui.TextInput(
                label="Horário de Unlock (HH:MM)",
                placeholder="Ex: 08:00",
                custom_id="horario_unlock",
                style=disnake.TextInputStyle.short,
                required=True,
                min_length=5,
                max_length=5,
                value=horario_unlock_atual
            )
        ]
        super().__init__(
            title=f"Use o horário de Brasília",
            custom_id="LockUnlock_ConfigModal",
            components=components,
        )

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter)
        else:
            await message.wait(inter)
        
        try:
            horario_lock = inter.text_values.get("horario_lock", "22:00").strip()
            horario_unlock = inter.text_values.get("horario_unlock", "08:00").strip()
            
            # Validar horários
            hora_l, min_l = map(int, horario_lock.split(":"))
            if not (0 <= hora_l <= 23 and 0 <= min_l <= 59): raise ValueError
            horario_lock_formatado = f"{hora_l:02d}:{min_l:02d}"

            hora_u, min_u = map(int, horario_unlock.split(":"))
            if not (0 <= hora_u <= 23 and 0 <= min_u <= 59): raise ValueError
            horario_unlock_formatado = f"{hora_u:02d}:{min_u:02d}"

        except Exception:
            # TODO: Adicionar mensagem de erro para o usuário
            await inter.edit_original_message(components=LockUnlockCog.Painel())
            return

        config = helpers.carregar_config()
        config["canais"][self.canal_id] = {
            "horario_lock": horario_lock_formatado,
            "horario_unlock": horario_unlock_formatado,
            "config_timestamp": disnake.utils.utcnow().timestamp(),
            "ultimo_estado": None # 'lock' ou 'unlock'
        }
        helpers.salvar_config(config)
        
        if mode == "embed":
            embed, components = LockUnlockCog.PainelEmbed()
            await inter.edit_original_message(content=None, embed=embed, components=components)
        else:
            await inter.edit_original_message(components=LockUnlockCog.Painel())

class LockUnlockCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def Painel() -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        ativado = bool(config.get("ativado", False))
        canais = config.get("canais", {})
        logs_ativados = bool(config.get("logs_ativados", True))

        canais_info = [
            f"<#{canal_id}> - Lock: {ch_config.get('horario_lock', 'N/A')} | Unlock: {ch_config.get('horario_unlock', 'N/A')}"
            for canal_id, ch_config in canais.items()
        ]
        
        canais_texto = "\n".join(canais_info[:5]) if canais_info else f"{emoji.arrow} `Nenhum canal configurado`"
        if len(canais_info) > 5:
            canais_texto += f"\n{emoji.arrow} ... e mais {len(canais_info) - 5} canais"

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_ativados else emoji.off} **Logs:** `{'Ativado' if logs_ativados else 'Desativado'}`\n"
            f"{emoji.textc} **Canais configurados:** `{len(canais)}`"
        )

        botoes_principais = [
            disnake.ui.Button(
                label="",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.power,
                custom_id="LockUnlock_ToggleAtivo"
            ),
            disnake.ui.Button(
                label="Adicionar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id="LockUnlock_AdicionarCanal", disabled=not ativado
            )
        ]
        if canais:
            botoes_principais.append(
                disnake.ui.Button(
                    label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="LockUnlock_RemoverCanal", disabled=not ativado
                )
            )

        botoes_inferiores = [
            disnake.ui.Button(
                label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"
            ),
            disnake.ui.Button(
                label="Logs",
                style=disnake.ButtonStyle.grey,
                emoji=emoji.power,
                custom_id="LockUnlock_ToggleLogs",
                disabled=not ativado
            )
        ]

        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > **Lock/Unlock de Canais**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Configure o lock/unlock automático de canais em horários fixos."),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.TextDisplay(resumo),
                disnake.ui.Separator(spacing=disnake.SeparatorSpacing.small),
                disnake.ui.ActionRow(*botoes_principais),
                **container_kwargs,
            ),
            disnake.ui.ActionRow(*botoes_inferiores)
        ]

    @staticmethod
    def PainelEmbed() -> tuple[disnake.Embed, list[disnake.ui.ActionRow]]:
        config = helpers.carregar_config()
        ativado = bool(config.get("ativado", False))
        canais = config.get("canais", {})
        logs_ativados = bool(config.get("logs_ativados", True))

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_ativados else emoji.off} **Logs:** `{'Ativado' if logs_ativados else 'Desativado'}`\n"
            f"{emoji.textc} **Canais configurados:** `{len(canais)}`"
        )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Lock/Unlock de Canais",
            description="Configure o lock/unlock automático de canais em horários fixos."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        embed.add_field(name="Configurações", value=resumo, inline=False)

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="LockUnlock_ToggleAtivo"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id="LockUnlock_AdicionarCanal", disabled=not ativado)
        ]
        if canais:
            botoes_principais.append(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="LockUnlock_RemoverCanal", disabled=not ativado)
            )

        botoes_inferiores = [
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            disnake.ui.Button(label="Logs", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="LockUnlock_ToggleLogs", disabled=not ativado)
        ]

        components = [
            disnake.ui.ActionRow(*botoes_principais),
            disnake.ui.ActionRow(*botoes_inferiores)
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def on_button_click(self, inter: disnake.MessageInteraction):
        cid = inter.component.custom_id
        if not cid.startswith("LockUnlock_"):
            return

        if cid == "LockUnlock_DesativarLogsViaLog":
            # Importar e usar a classe perms para verificação
            from functions.perms import perms as perms_check
            if not await perms_check.check(inter.author.id):
                await inter.response.send_message("Você não tem permissão para fazer isso.", ephemeral=True)
                return
            
            config = helpers.carregar_config()
            config["logs_ativados"] = False
            helpers.salvar_config(config)
            
            await inter.response.send_message("As logs de lock/unlock automático foram desativadas.\nAtive novamente em: **Painel > Automações > Lock/Unlock de Canais**", ephemeral=True)
            
            try:
                await inter.message.delete()
            except disnake.HTTPException:
                pass
            return
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if cid == "LockUnlock_ToggleAtivo":
            config = helpers.carregar_config()
            config["ativado"] = not bool(config.get("ativado", False))
            helpers.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

        elif cid == "LockUnlock_ToggleLogs":
            config = helpers.carregar_config()
            config["logs_ativados"] = not bool(config.get("logs_ativados", True))
            helpers.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

        elif cid == "LockUnlock_AdicionarCanal":
            if mode == "embed":
                primary_color_hex = db.get_document("custom_colors").get("primary")
                embed = disnake.Embed(
                    title=f"Adicionar Canal",
                    description="Selecione um canal para configurar o lock/unlock automático."
                )
                if primary_color_hex:
                    embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                components = [
                    disnake.ui.ActionRow(
                        disnake.ui.ChannelSelect(placeholder="Pesquise e selecione um canal...", custom_id="LockUnlock_SelectCanal", min_values=1, max_values=1, channel_types=[disnake.ChannelType.text])
                    ),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="LockUnlock_VoltarPainel"))
                ]
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                primary_color_hex = db.get_document("custom_colors").get("primary")
                container_kwargs = {}
                if primary_color_hex:
                    primary_color = int(primary_color_hex.replace("#", ""), 16)
                    container_kwargs["accent_colour"] = disnake.Colour(primary_color)
                await inter.edit_original_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > Lock/Unlock de Canais > **Adicionar Canal**"),
                            disnake.ui.Separator(),
                            disnake.ui.ActionRow(
                                disnake.ui.ChannelSelect(placeholder="Pesquise e selecione um canal...", custom_id="LockUnlock_SelectCanal", min_values=1, max_values=1, channel_types=[disnake.ChannelType.text])
                            ),
                            **container_kwargs,
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="LockUnlock_VoltarPainel"),
                        )
                    ]
                )

        elif cid == "LockUnlock_RemoverCanal":
            config = helpers.carregar_config()
            canais = config.get("canais", {})
            if not canais:
                if mode == "embed":
                    embed, components = self.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.Painel())
                return

            canais_opcoes = [
                disnake.SelectOption(label=f"#{canal.name}", value=str(canal.id), description=f"ID: {canal.id}")
                for canal_id in canais.keys()
                if (canal := inter.guild.get_channel(int(canal_id)))
            ]
            
            if not canais_opcoes:
                if mode == "embed":
                    embed, components = self.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.Painel())
                return

            if mode == "embed":
                primary_color_hex = db.get_document("custom_colors").get("primary")
                embed = disnake.Embed(
                    title=f"Remover Canal",
                    description="Selecione um ou mais canais para remover da automação."
                )
                if primary_color_hex:
                    embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                components = [
                    disnake.ui.ActionRow(
                        disnake.ui.Select(placeholder="Escolha um canal para remover...", options=canais_opcoes, custom_id="LockUnlock_RemoverSelectCanal", min_values=1, max_values=len(canais_opcoes))
                    ),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="LockUnlock_VoltarPainel"))
                ]
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                primary_color_hex = db.get_document("custom_colors").get("primary")
                container_kwargs = {}
                if primary_color_hex:
                    primary_color = int(primary_color_hex.replace("#", ""), 16)
                    container_kwargs["accent_colour"] = disnake.Colour(primary_color)
                await inter.edit_original_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > Lock/Unlock de Canais > **Remover Canal**"),
                            disnake.ui.Separator(),
                            disnake.ui.ActionRow(
                                disnake.ui.Select(placeholder="Escolha um canal para remover...", options=canais_opcoes, custom_id="LockUnlock_RemoverSelectCanal", min_values=1, max_values=len(canais_opcoes))
                            ),
                            **container_kwargs,
                        ),
                        disnake.ui.ActionRow(
                            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="LockUnlock_VoltarPainel"),
                        )
                    ]
                )

        elif cid == "LockUnlock_VoltarPainel":
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

    @commands.Cog.listener("on_dropdown")
    async def on_dropdown(self, inter: disnake.MessageInteraction):
        cid = inter.data.custom_id
        if not cid.startswith("LockUnlock_"):
            return
        
        if cid == "LockUnlock_SelectCanal":
            canal_id = inter.values[0]
            canal = inter.guild.get_channel(int(canal_id))
            if not canal:
                mode = db.get_document("custom_mode").get("mode")
                if mode == "embed":
                    await embed_message.wait(inter, send=False)
                    embed, components = self.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await message.wait(inter, send=False)
                    await inter.edit_original_message(components=self.Painel())
                return
            await inter.response.send_modal(ConfigurarLockUnlockModal(self.bot, canal_id, canal.name))

        elif cid == "LockUnlock_RemoverSelectCanal":
            mode = db.get_document("custom_mode").get("mode")
            if mode == "embed":
                await embed_message.wait(inter, send=False)
            else:
                await message.wait(inter, send=False)
            
            config = helpers.carregar_config()
            canais = config.get("canais", {})
            for canal_id in inter.values:
                if canal_id in canais:
                    del canais[canal_id]
            helpers.salvar_config(config)
            
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

def setup(bot: commands.Bot):
    bot.add_cog(LockUnlockCog(bot))
