import disnake
from disnake.ext import commands

from ._common import obter_canal_id, enviar_log, verificar_guild
from functions.emoji import emoji


def obter_nome_completo_comando(inter: disnake.Interaction) -> str:
    """
    Extrai o nome completo do comando incluindo subcomandos.
    Exemplo: /ticket fechar -> "ticket fechar"
    """
    if not hasattr(inter, 'data') or not inter.data:
        return ""
    
    nome_base = inter.data.name if hasattr(inter.data, 'name') else ""
    
    # Verificar se há opções (subcomandos)
    if hasattr(inter.data, 'options') and inter.data.options:
        partes = [nome_base]
        
        # Função recursiva para extrair subcomandos
        def extrair_subcomandos(options):
            for option in options:
                # Verificar se é um subcomando ou grupo de subcomandos
                # Tipo 1 = sub_command, Tipo 2 = sub_command_group
                if isinstance(option, dict):
                    option_type = option.get('type')
                    option_name = option.get('name', '')
                    option_options = option.get('options', [])
                else:
                    option_type = getattr(option, 'type', None)
                    option_name = getattr(option, 'name', '')
                    option_options = getattr(option, 'options', [])
                
                # Verificar se é subcomando (tipo 1) ou grupo de subcomandos (tipo 2)
                if option_type in (1, 2):
                    if option_name:
                        partes.append(option_name)
                    # Se houver mais opções dentro do subcomando, continuar recursivamente
                    if option_options:
                        extrair_subcomandos(option_options)
                    break  # Geralmente só há um subcomando por nível
        
        extrair_subcomandos(inter.data.options)
        return " ".join(partes)
    
    return nome_base


class OnCommand(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_interaction")
    async def on_slash_command(self, inter: disnake.Interaction):
        if inter.type != disnake.InteractionType.application_command or inter.data.type != disnake.ApplicationCommandType.chat_input:
            return

        if inter.guild is None or not verificar_guild(inter.guild.id):
            return
            
        canal_id = obter_canal_id("canal_de_logs_de_comandos")
        if not canal_id:
            return
            
        try:
            usuario = inter.user
            nome_completo = obter_nome_completo_comando(inter)
            linhas = [
                f"{emoji.commands} **Comando:** `/{nome_completo}`",
                f"{emoji.member} **Usuário:** {usuario.mention} (`{usuario.id}`)",
                f"{emoji.textc} **Canal:** {inter.channel.mention if inter.channel else '(desconhecido)'}",
            ]
            await enviar_log(inter.guild, canal_id, "Logs de Comandos (Slash)", linhas)
        except Exception:
            return

    @commands.Cog.listener("on_command")
    async def on_prefix_command(self, ctx: commands.Context):
        if ctx.guild is None or not verificar_guild(ctx.guild.id):
            return

        canal_id = obter_canal_id("canal_de_logs_de_comandos")
        if not canal_id:
            return

        try:
            usuario = ctx.author
            nome = ctx.command.name
            linhas = [
                f"{emoji.commands} **Comando:** `{ctx.prefix}{nome}`",
                f"{emoji.member} **Usuário:** {usuario.mention} (`{usuario.id}`)",
                f"{emoji.textc} **Canal:** {ctx.channel.mention if ctx.channel else '(desconhecido)'}",
            ]
            await enviar_log(ctx.guild, canal_id, "Logs de Comandos (Prefixo)", linhas)
        except Exception:
            return


def setup(bot: commands.Bot):
    bot.add_cog(OnCommand(bot))
