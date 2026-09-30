import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
import pytz

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from . import helpers

class CleanCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def Painel() -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        canais = config.get("canais", {})
        
        canais_info = []
        for canal_id, canal_config in canais.items():
            intervalo_minutos = canal_config.get("intervalo_minutos", 1440)
            if intervalo_minutos >= 60 and intervalo_minutos % 60 == 0:
                intervalo_text = f"A cada {intervalo_minutos // 60}h"
            else:
                intervalo_text = f"A cada {intervalo_minutos}min"
            
            proxima_limpeza_str = canal_config.get("proxima_limpeza")
            if proxima_limpeza_str:
                try:
                    proxima_dt = datetime.fromisoformat(proxima_limpeza_str)
                    info_prox = f"(Próxima: <t:{int(proxima_dt.timestamp())}:R>)"
                except ValueError:
                    info_prox = "(Agendamento inválido)"
            else:
                info_prox = "(Aguardando agendamento)"

            canais_info.append(f"{emoji.arrow} <#{canal_id}> - `{intervalo_text}`")
        
        canais_texto = "\n".join(canais_info[:5]) if canais_info else f"{emoji.arrow} `Nenhum canal configurado`"
        if len(canais_info) > 5:
            canais_texto += f"\n{emoji.arrow} ... e mais {len(canais_info) - 5} canais"

        logs_ativados = config.get("logs_ativados", False)
        
        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_ativados else emoji.off} **Logs:** `{'Ativado' if logs_ativados else 'Desativado'}`\n"
            f"{emoji.textc} **Canais configurados:** `{len(canais)}`"
        )

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Limpeza_ToggleAtivo"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id="Limpeza_AdicionarCanal", disabled=not ativado)
        ]

        if canais:
            botoes_principais.append(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="Limpeza_RemoverCanal", disabled=not ativado)
            )

        botoes_inferiores = [
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            disnake.ui.Button(label="Logs", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Limpeza_ToggleLogs", disabled=not ativado)
        ]

        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > **Limpeza de Canais**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Configure a limpeza automática de canais em intervalos fixos."),
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
        ativado = config.get("ativado", False)
        canais = config.get("canais", {})
        logs_ativados = config.get("logs_ativados", False)

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_ativados else emoji.off} **Logs:** `{'Ativado' if logs_ativados else 'Desativado'}`\n"
            f"{emoji.textc} **Canais configurados:** `{len(canais)}`"
        )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Limpeza de Canais",
            description="Configure a limpeza automática de canais em intervalos fixos."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        embed.add_field(name="Configurações", value=resumo, inline=False)

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Limpeza_ToggleAtivo"),
            disnake.ui.Button(label="Adicionar", style=disnake.ButtonStyle.blurple, emoji=emoji.plus, custom_id="Limpeza_AdicionarCanal", disabled=not ativado)
        ]

        if canais:
            botoes_principais.append(
                disnake.ui.Button(label="Remover", style=disnake.ButtonStyle.red, emoji=emoji.minus, custom_id="Limpeza_RemoverCanal", disabled=not ativado)
            )

        components = [
            disnake.ui.ActionRow(*botoes_principais),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
                disnake.ui.Button(label="Logs", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Limpeza_ToggleLogs", disabled=not ativado)
            )
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def Limpeza_Button_Listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("Limpeza_"):
            return

        if custom_id == "Limpeza_DesativarLogsViaLog":
            # Importar e usar a classe perms para verificação
            from functions.perms import perms as perms_check
            if not await perms_check.check(inter.author.id):
                await inter.response.send_message("Você não tem permissão para fazer isso.", ephemeral=True)
                return
            
            config = helpers.carregar_config()
            config["logs_ativados"] = False
            helpers.salvar_config(config)
            
            await inter.response.send_message("As logs de limpeza automática foram desativadas.\nAtive novamente em: **Painel > Automações > Limpeza de Canais**", ephemeral=True)
            
            try:
                # Apaga a mensagem de log original
                await inter.message.delete()
            except disnake.HTTPException:
                pass
            return
        
        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)

        if custom_id == "Limpeza_ToggleAtivo":
            config = helpers.carregar_config()
            config["ativado"] = not config.get("ativado", False)
            helpers.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())
        
        elif custom_id == "Limpeza_VoltarPainel":
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

        elif custom_id == "Limpeza_ToggleLogs":
            config = helpers.carregar_config()
            config["logs_ativados"] = not config.get("logs_ativados", False)
            helpers.salvar_config(config)
            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

        elif custom_id == "Limpeza_AdicionarCanal":
            primary_color_hex = db.get_document("custom_colors").get("primary")
            container_kwargs = {}
            if primary_color_hex:
                primary_color = int(primary_color_hex.replace("#", ""), 16)
                container_kwargs["accent_colour"] = disnake.Colour(primary_color)
            if mode == "embed":
                embed = disnake.Embed(
                    title=f"Adicionar Canal",
                    description="Selecione o canal que deseja configurar para limpeza automática."
                )
                primary_color_hex = db.get_document("custom_colors").get("primary")
                if primary_color_hex:
                    embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
                
                components = [
                    disnake.ui.ActionRow(
                        disnake.ui.ChannelSelect(placeholder="Selecione um canal...", custom_id="Limpeza_SelectCanal", min_values=1, max_values=1, channel_types=[disnake.ChannelType.text])
                    ),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Limpeza_VoltarPainel"))
                ]
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(
                    components=[
                        disnake.ui.Container(
                            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > Limpeza > **Adicionar**"),
                            disnake.ui.Separator(),
                            disnake.ui.ActionRow(
                                disnake.ui.ChannelSelect(placeholder="Selecione um canal...", custom_id="Limpeza_SelectCanal", min_values=1, max_values=1, channel_types=[disnake.ChannelType.text])
                            ),
                            **container_kwargs
                        ),
                        disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Limpeza_VoltarPainel"))
                    ]
                )

        elif custom_id == "Limpeza_RemoverCanal":
            config = helpers.carregar_config()
            canais = config.get("canais", {})
            if not canais:
                if mode == "embed":
                    embed, components = self.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.Painel())
                return

            opcoes = []
            for cid, cconfig in canais.items():
                if channel := inter.guild.get_channel(int(cid)):
                    intervalo_min = cconfig.get("intervalo_minutos", 1440)
                    if intervalo_min >= 60 and intervalo_min % 60 == 0:
                        desc = f"A cada {intervalo_min // 60}h"
                    else:
                        desc = f"A cada {intervalo_min}min"
                    opcoes.append(disnake.SelectOption(label=f"#{channel.name}", value=cid, description=desc))
            
            if not opcoes:
                if mode == "embed":
                    embed, components = self.PainelEmbed()
                    await inter.edit_original_message(content=None, embed=embed, components=components)
                else:
                    await inter.edit_original_message(components=self.Painel())
                return

            if mode == "embed":
                embed = disnake.Embed(
                    title=f"Remover Canal",
                    description="Selecione um canal para remover da limpeza automática."
                )
                primary_color_hex = db.get_document("custom_colors").get("primary")
                if primary_color_hex:
                    embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))

                components = [
                    disnake.ui.ActionRow(disnake.ui.Select(placeholder="Escolha um canal para remover...", options=opcoes, custom_id="Limpeza_RemoverSelectCanal", min_values=1, max_values=1)),
                    disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Limpeza_VoltarPainel"))
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
                            disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > Limpeza > **Remover**"),
                            disnake.ui.Separator(),
                            disnake.ui.ActionRow(disnake.ui.Select(placeholder="Escolha um canal para remover...", options=opcoes, custom_id="Limpeza_RemoverSelectCanal", min_values=1, max_values=1)),
                            **container_kwargs
                        ),
                        disnake.ui.ActionRow(disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="Limpeza_VoltarPainel"))
                    ]
                )

    @commands.Cog.listener("on_dropdown")
    async def Limpeza_Select_Listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("Limpeza_"):
            return

        if custom_id == "Limpeza_SelectCanal":
            canal_id = inter.values[0]
            await inter.response.send_modal(ConfigurarLimpezaModal(canal_id))
            return

        mode = db.get_document("custom_mode").get("mode")
        if mode == "embed":
            await embed_message.wait(inter, send=False)
        else:
            await message.wait(inter, send=False)
        
        if custom_id == "Limpeza_RemoverSelectCanal":
            canal_id = inter.values[0]
            config = helpers.carregar_config()
            if canal_id in config.get("canais", {}):
                del config["canais"][canal_id]
                helpers.salvar_config(config)

            if mode == "embed":
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=self.Painel())

class ConfigurarLimpezaModal(disnake.ui.Modal):
    def __init__(self, canal_id: str):
        self.canal_id = canal_id
        
        components = [
            disnake.ui.TextInput(label="Intervalo em minutos (mínimo 1)", placeholder="Ex: 60 (para 1 hora), 1440 (para 24h)", custom_id="intervalo", style=disnake.TextInputStyle.short, required=True, min_length=1, max_length=5)
        ]
        
        super().__init__(title="Configurar Limpeza de Canal", custom_id="Limpeza_ConfigModal", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        
        try:
            intervalo = int(inter.text_values.get("intervalo", "1440").strip())
            if intervalo < 1:
                raise ValueError("Intervalo muito baixo")

            # Se chegou aqui, a validação passou - agora podemos fazer wait e atualizar
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)

            config = helpers.carregar_config()
            agora = datetime.now(pytz.timezone('America/Sao_Paulo'))
            proxima_limpeza = agora + timedelta(minutes=intervalo)

            config["canais"][self.canal_id] = {
                "intervalo_minutos": intervalo,
                "proxima_limpeza": proxima_limpeza.isoformat()
            }
            helpers.salvar_config(config)

            if task_cog := inter.bot.get_cog("CleanTaskCog"):
                task_cog.restart_task()
            
            if mode == "embed":
                embed, components = CleanCog.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=CleanCog.Painel())

        except (ValueError, TypeError):
            # Em caso de erro, fazer wait primeiro e depois atualizar o painel
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)
            
            # Atualizar o painel mesmo em caso de erro
            if mode == "embed":
                embed, components = CleanCog.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=CleanCog.Painel())
            
            # Enviar mensagem de erro como followup
            await inter.followup.send("O intervalo deve ser um número válido maior que 0.", ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(CleanCog(bot))
