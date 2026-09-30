import json
import disnake
from disnake.ext import commands
from functools import wraps
from typing import Optional, Union

def get_main_server_id() -> Optional[int]:
    """Obtém o ID do servidor principal do config.json"""
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
            server_id = config.get("bot", {}).get("server")
            if server_id:
                return int(server_id)
    except Exception as e:
        print(f"Erro ao ler config.json: {e}")
    return None

def is_main_server(guild_id: Union[int, str]) -> bool:
    """Verifica se o guild_id é do servidor principal"""
    main_server_id = get_main_server_id()
    if main_server_id is None:
        return False
    return int(guild_id) == main_server_id

def check_server_slash_command():
    """
    Decorador para comandos slash que verifica se o comando está sendo executado no servidor principal.
    Comandos decorados com @exclude_from_check não serão verificados.
    """
    def decorator(func):
        # Se o comando tem o atributo exclude_from_check, não aplica a verificação
        if hasattr(func, '_exclude_from_check') and func._exclude_from_check:
            return func
            
        @wraps(func)
        async def wrapper(self, inter: disnake.ApplicationCommandInteraction, *args, **kwargs):
            # Verifica se é o servidor principal
            if not is_main_server(inter.guild_id):
                await inter.response.send_message(
                    "Acesso Negado: Este comando só pode ser usado no servidor principal.",
                    ephemeral=True
                )
                return
            
            # Se passou na verificação, executa o comando normalmente
            return await func(self, inter, *args, **kwargs)
        
        return wrapper
    return decorator

def check_server_prefix_command():
    """
    Decorador para comandos de prefixo que verifica se o comando está sendo executado no servidor principal.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, ctx: commands.Context, *args, **kwargs):
            # Verifica se é o servidor principal
            if not is_main_server(ctx.guild.id):
                await ctx.send(
                    "Acesso Negado: Este comando só pode ser usado no servidor principal.",
                    delete_after=10
                )
                return
            
            # Se passou na verificação, executa o comando normalmente
            return await func(self, ctx, *args, **kwargs)
        
        return wrapper
    return decorator

def exclude_from_check(func):
    """
    Marca um comando para ser excluído da verificação de servidor.
    Use isso para comandos como /backup que devem funcionar em qualquer servidor.
    """
    func._exclude_from_check = True
    return func

async def check_server_event(guild_id: Union[int, str]) -> bool:
    """
    Verifica se um evento deve ser processado baseado no servidor.
    Retorna True se o evento deve ser processado, False caso contrário.
    """
    return is_main_server(guild_id)

def check_interaction_server(inter: Union[disnake.Interaction, disnake.ApplicationCommandInteraction]) -> bool:
    """
    Verifica se uma interação (botão, select menu, modal) está no servidor principal.
    """
    if not inter.guild:
        return False
    return is_main_server(inter.guild.id)

async def send_server_error(inter: Union[disnake.Interaction, disnake.ApplicationCommandInteraction], ephemeral: bool = True):
    """
    Envia uma mensagem de erro padrão quando o comando é usado fora do servidor principal.
    """
    msg = "Acesso Negado: Esta ação só pode ser realizada no servidor principal."
    
    if isinstance(inter, disnake.ApplicationCommandInteraction):
        if not inter.response.is_done():
            await inter.response.send_message(msg, ephemeral=ephemeral)
        else:
            await inter.followup.send(msg, ephemeral=ephemeral)
    else:
        if not inter.response.is_done():
            await inter.response.send_message(msg, ephemeral=ephemeral)
        else:
            await inter.followup.send(msg, ephemeral=ephemeral)
