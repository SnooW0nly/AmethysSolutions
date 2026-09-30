import disnake
from disnake.ext import commands
from datetime import datetime, timedelta
import pytz

from functions.emoji import emoji
from functions.message import message, embed_message
from functions.database import database as db
from . import helpers

class RepostCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @staticmethod
    def Painel() -> list[disnake.ui.Container]:
        config = helpers.carregar_config()
        ativado = config.get("ativado", False)
        intervalo_horas = config.get("intervalo_horas", 24)
        logs_ativados = config.get("logs_ativados", False)
        
        proxima_repostagem_str = config.get("proxima_repostagem")
        if proxima_repostagem_str:
            try:
                proxima_dt = datetime.fromisoformat(proxima_repostagem_str)
                info_prox = f"<t:{int(proxima_dt.timestamp())}:R>"
            except ValueError:
                info_prox = "`Agendamento inválido`"
        else:
            info_prox = "`Aguardando agendamento`"
        
        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_ativados else emoji.off} **Logs:** `{'Ativado' if logs_ativados else 'Desativado'}`\n"
            f"{emoji.clock} **Intervalo:** `{intervalo_horas}h`\n"
            f"{emoji.arrow} **Próxima repostagem:** {info_prox}"
        )

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Repost_ToggleAtivo"),
            disnake.ui.Button(label="Configurar Intervalo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Repost_ConfigurarIntervalo", disabled=not ativado)
        ]

        botoes_inferiores = [
            disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
            disnake.ui.Button(label="Logs", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Repost_ToggleLogs", disabled=not ativado)
        ]

        primary_color_hex = db.get_document("custom_colors").get("primary")
        container_kwargs = {}
        if primary_color_hex:
            primary_color = int(primary_color_hex.replace("#", ""), 16)
            container_kwargs["accent_colour"] = disnake.Colour(primary_color)

        return [
            disnake.ui.Container(
                disnake.ui.TextDisplay(f"# {emoji.a1}{emoji.b2}{emoji.c3}{emoji.d4}{emoji.e5}\n-# Painel > Automações > **Repostagem de Produtos**"),
                disnake.ui.Separator(),
                disnake.ui.TextDisplay("Configure a repostagem automática de todos os produtos em intervalos fixos."),
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
        intervalo_horas = config.get("intervalo_horas", 24)
        logs_ativados = config.get("logs_ativados", False)

        proxima_repostagem_str = config.get("proxima_repostagem")
        if proxima_repostagem_str:
            try:
                proxima_dt = datetime.fromisoformat(proxima_repostagem_str)
                info_prox = f"<t:{int(proxima_dt.timestamp())}:R>"
            except ValueError:
                info_prox = "`Agendamento inválido`"
        else:
            info_prox = "`Aguardando agendamento`"

        resumo = (
            f"{emoji.on if ativado else emoji.off} **Status:** `{'Ativado' if ativado else 'Desativado'}`\n"
            f"{emoji.on if logs_ativados else emoji.off} **Logs:** `{'Ativado' if logs_ativados else 'Desativado'}`\n"
            f"{emoji.clock} **Intervalo:** `{intervalo_horas}h`\n"
            f"{emoji.arrow} **Próxima repostagem:** {info_prox}"
        )

        primary_color_hex = db.get_document("custom_colors").get("primary")
        embed = disnake.Embed(
            title=f"Repostagem de Produtos",
            description="Configure a repostagem automática de todos os produtos em intervalos fixos."
        )
        if primary_color_hex:
            embed.color = disnake.Colour(int(primary_color_hex.replace("#", ""), 16))
        
        embed.add_field(name="Configurações", value=resumo, inline=False)

        botoes_principais = [
            disnake.ui.Button(label="", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Repost_ToggleAtivo"),
            disnake.ui.Button(label="Configurar Intervalo", style=disnake.ButtonStyle.blurple, emoji=emoji.edit, custom_id="Repost_ConfigurarIntervalo", disabled=not ativado)
        ]

        components = [
            disnake.ui.ActionRow(*botoes_principais),
            disnake.ui.ActionRow(
                disnake.ui.Button(label="Voltar", style=disnake.ButtonStyle.grey, emoji=emoji.back, custom_id="VoltarAutomações"),
                disnake.ui.Button(label="Logs", style=disnake.ButtonStyle.grey, emoji=emoji.power, custom_id="Repost_ToggleLogs", disabled=not ativado)
            )
        ]
        return embed, components

    @commands.Cog.listener("on_button_click")
    async def Repost_Button_Listener(self, inter: disnake.MessageInteraction):
        custom_id = inter.component.custom_id
        if not custom_id.startswith("Repost_"):
            return

        if custom_id == "Repost_DesativarLogsViaLog":
            # Importar e usar a classe perms para verificação
            from functions.perms import perms as perms_check
            if not await perms_check.check(inter.author.id):
                await inter.response.send_message("Você não tem permissão para fazer isso.", ephemeral=True)
                return
            
            config = helpers.carregar_config()
            config["logs_ativados"] = False
            helpers.salvar_config(config)
            
            await inter.response.send_message("As logs de repostagem automática foram desativadas.\nAtive novamente em: **Painel > Automações > Repostagem de Produtos**", ephemeral=True)
            
            try:
                await inter.message.delete()
            except disnake.HTTPException:
                pass
            return
        
        mode = db.get_document("custom_mode").get("mode")

        if custom_id == "Repost_ToggleAtivo":
            config = helpers.carregar_config()
            novo_estado = not config.get("ativado", False)
            config["ativado"] = novo_estado
            
            # Se ativou, agendar primeira repostagem
            if novo_estado and not config.get("proxima_repostagem"):
                agora = datetime.now(pytz.timezone('America/Sao_Paulo'))
                intervalo_horas = config.get("intervalo_horas", 24)
                proxima = agora + timedelta(hours=intervalo_horas)
                config["proxima_repostagem"] = proxima.isoformat()
            
            helpers.salvar_config(config)
            
            if task_cog := inter.bot.get_cog("RepostTaskCog"):
                task_cog.restart_task()
            
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.Painel())
        
        elif custom_id == "Repost_VoltarPainel":
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.Painel())

        elif custom_id == "Repost_ToggleLogs":
            config = helpers.carregar_config()
            config["logs_ativados"] = not config.get("logs_ativados", False)
            helpers.salvar_config(config)
            if mode == "embed":
                await embed_message.wait(inter, send=False)
                embed, components = self.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await message.wait(inter, send=False)
                await inter.edit_original_message(components=self.Painel())

        elif custom_id == "Repost_ConfigurarIntervalo":
            await inter.response.send_modal(ConfigurarRepostModal())

class ConfigurarRepostModal(disnake.ui.Modal):
    def __init__(self):
        components = [
            disnake.ui.TextInput(label="Intervalo em horas (mínimo 1)", placeholder="Ex: 24 (para 24 horas), 12 (para 12h)", custom_id="intervalo", style=disnake.TextInputStyle.short, required=True, min_length=1, max_length=3)
        ]
        
        super().__init__(title="Configurar Repostagem", custom_id="Repost_ConfigModal", components=components)

    async def callback(self, inter: disnake.ModalInteraction):
        mode = db.get_document("custom_mode").get("mode")
        
        try:
            intervalo = int(inter.text_values.get("intervalo", "24").strip())
            if intervalo < 1:
                raise ValueError("Intervalo muito baixo")

            # Se chegou aqui, a validação passou - agora podemos fazer wait e atualizar
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)

            config = helpers.carregar_config()
            agora = datetime.now(pytz.timezone('America/Sao_Paulo'))
            proxima_repostagem = agora + timedelta(hours=intervalo)

            config["intervalo_horas"] = intervalo
            config["proxima_repostagem"] = proxima_repostagem.isoformat()
            helpers.salvar_config(config)

            if task_cog := inter.bot.get_cog("RepostTaskCog"):
                task_cog.restart_task()
            
            if mode == "embed":
                embed, components = RepostCog.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=RepostCog.Painel())

        except (ValueError, TypeError):
            # Em caso de erro, fazer wait primeiro e depois atualizar o painel
            if mode == "embed":
                await embed_message.wait(inter)
            else:
                await message.wait(inter)
            
            # Atualizar o painel mesmo em caso de erro
            if mode == "embed":
                embed, components = RepostCog.PainelEmbed()
                await inter.edit_original_message(content=None, embed=embed, components=components)
            else:
                await inter.edit_original_message(components=RepostCog.Painel())
            
            # Enviar mensagem de erro como followup
            await inter.followup.send("O intervalo deve ser um número válido maior que 0.", ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(RepostCog(bot))
